"""
ADS-B 导航数据处理系统
基于main.py的思路重新设计，采用面向对象架构
主要功能：串口通信、ADS-B消息解码、位置计算、数据记录
"""

import serial
import serial.tools.list_ports
import time
import math
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Tuple, List
import logging


class ECEFConverter:
    """经纬度到地心地固坐标系(ECEF)转换器"""

    # WGS84椭球参数
    WGS84_A = 6378137.0  # 地球赤道半径（长半轴），单位：米
    WGS84_E2 = 6.69437999014e-3  # 第一偏心率平方

    @classmethod
    def degrees_to_radians(cls, degrees: float) -> float:
        """度转弧度"""
        return degrees * math.pi / 180.0

    @classmethod
    def calculate_prime_vertical_radius(cls, lat_rad: float) -> float:
        """计算卯酉圈曲率半径 N"""
        sin_lat = math.sin(lat_rad)
        return cls.WGS84_A / math.sqrt(1 - cls.WGS84_E2 * sin_lat * sin_lat)

    @classmethod
    def lla_to_ecef(cls, latitude: float, longitude: float, altitude: float) -> Tuple[float, float, float]:
        """
        将经纬度高度转换为ECEF坐标

        Args:
            latitude: 纬度（度），北纬为正，南纬为负
            longitude: 经度（度），东经为正，西经为负
            altitude: 高度（米），相对于椭球面

        Returns:
            (X, Y, Z): ECEF坐标，单位：米
        """
        # 1. 将经纬度转换为弧度
        lat_rad = cls.degrees_to_radians(latitude)
        lon_rad = cls.degrees_to_radians(longitude)

        # 2. 计算卯酉圈曲率半径 N
        N = cls.calculate_prime_vertical_radius(lat_rad)

        # 3. 计算三角函数值
        cos_lat = math.cos(lat_rad)
        sin_lat = math.sin(lat_rad)
        cos_lon = math.cos(lon_rad)
        sin_lon = math.sin(lon_rad)

        # 4. 计算ECEF坐标
        X = (N + altitude) * cos_lat * cos_lon
        Y = (N + altitude) * cos_lat * sin_lon
        Z = (N * (1 - cls.WGS84_E2) + altitude) * sin_lat

        return X, Y, Z


class ENUConverter:
    """ECEF到东北天坐标系(ENU)转换器"""

    # 参考点：北京上空10000m
    REF_LATITUDE = 39.9    # 北纬39.9度
    REF_LONGITUDE = 116.4  # 东经116.4度
    REF_ALTITUDE = 10000.0 # 高度10000米

    def __init__(self):
        """初始化参考点的ECEF坐标和旋转参数"""
        # 计算参考点的ECEF坐标
        self.ref_x, self.ref_y, self.ref_z = ECEFConverter.lla_to_ecef(
            self.REF_LATITUDE, self.REF_LONGITUDE, self.REF_ALTITUDE
        )

        # 将参考点经纬度转换为弧度
        self.ref_lat_rad = ECEFConverter.degrees_to_radians(self.REF_LATITUDE)
        self.ref_lon_rad = ECEFConverter.degrees_to_radians(self.REF_LONGITUDE)

        # 预计算三角函数值
        self.sin_lat = math.sin(self.ref_lat_rad)
        self.cos_lat = math.cos(self.ref_lat_rad)
        self.sin_lon = math.sin(self.ref_lon_rad)
        self.cos_lon = math.cos(self.ref_lon_rad)

    def ecef_to_enu(self, ecef_x: float, ecef_y: float, ecef_z: float) -> Tuple[float, float, float]:
        """
        将ECEF坐标转换为ENU坐标

        Args:
            ecef_x, ecef_y, ecef_z: 目标点的ECEF坐标 (米)

        Returns:
            (E, N, U): 东北天坐标 (米)
                E: 东向距离 (正值表示在参考点东方)
                N: 北向距离 (正值表示在参考点北方)
                U: 天向距离 (正值表示在参考点上方)
        """
        # 1. 计算ECEF坐标差
        delta_x = ecef_x - self.ref_x
        delta_y = ecef_y - self.ref_y
        delta_z = ecef_z - self.ref_z

        # 2. 应用旋转矩阵转换到ENU坐标系
        # 东向 (East)
        E = -self.sin_lon * delta_x + self.cos_lon * delta_y

        # 北向 (North)
        N = (-self.sin_lat * self.cos_lon * delta_x
             - self.sin_lat * self.sin_lon * delta_y
             + self.cos_lat * delta_z)

        # 天向 (Up)
        U = (self.cos_lat * self.cos_lon * delta_x
             + self.cos_lat * self.sin_lon * delta_y
             + self.sin_lat * delta_z)

        return E, N, U

    def get_reference_info(self) -> str:
        """获取参考点信息"""
        return (f"参考点: 北京上空 ({self.REF_LATITUDE}°N, {self.REF_LONGITUDE}°E, {self.REF_ALTITUDE}m)\n"
                f"参考点ECEF: ({self.ref_x:.1f}, {self.ref_y:.1f}, {self.ref_z:.1f}) m")


@dataclass
class AircraftPosition:
    """飞机位置信息数据类"""
    icao: str
    latitude: float
    longitude: float
    altitude: int
    timestamp: float
    ecef_x: float = 0.0
    ecef_y: float = 0.0
    ecef_z: float = 0.0
    enu_e: float = 0.0  # 东向距离
    enu_n: float = 0.0  # 北向距离
    enu_u: float = 0.0  # 天向距离

    def __post_init__(self):
        """初始化后自动计算ECEF和ENU坐标"""
        # 将高度从英尺转换为米（1英尺 = 0.3048米）
        altitude_meters = self.altitude * 0.3048

        # 计算ECEF坐标
        self.ecef_x, self.ecef_y, self.ecef_z = ECEFConverter.lla_to_ecef(
            self.latitude, self.longitude, altitude_meters
        )

        # 计算ENU坐标（相对于北京上空10000m）
        enu_converter = ENUConverter()
        self.enu_e, self.enu_n, self.enu_u = enu_converter.ecef_to_enu(
            self.ecef_x, self.ecef_y, self.ecef_z
        )

    def __str__(self):
        return (f"ICAO:{self.icao} "
                f"位置:({self.latitude:.6f}°, {self.longitude:.6f}°) "
                f"高度:{self.altitude}ft "
                f"ECEF:({self.ecef_x:.1f}, {self.ecef_y:.1f}, {self.ecef_z:.1f})m "
                f"ENU:({self.enu_e:.1f}, {self.enu_n:.1f}, {self.enu_u:.1f})m")


class SerialManager:
    """串口管理器 - 负责串口连接和数据读取"""

    def __init__(self, baudrate: int = 115200, timeout: int = 1):
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def get_available_ports(self) -> List[str]:
        """获取可用串口列表"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, target_port: Optional[str] = None) -> bool:
        """连接串口"""
        available_ports = self.get_available_ports()
        print(f"发现可用串口: {available_ports}")

        # 尝试连接指定端口
        if target_port:
            port_name = self._format_port_name(target_port)
            if self._try_connect(port_name):
                return True

        # 自动连接第一个可用端口
        for port in available_ports:
            if self._try_connect(port):
                return True

        return False

    def _format_port_name(self, port: str) -> str:
        """格式化端口名称，处理Windows高端口号"""
        if os.name == 'nt' and port.isdigit() and int(port) >= 10:
            return f'\\\\.\\COM{port}'
        return port

    def _try_connect(self, port_name: str) -> bool:
        """尝试连接指定端口"""
        try:
            self.connection = serial.Serial(
                port=port_name,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self.timeout
            )
            print(f"成功连接串口: {port_name}")
            return True
        except Exception:
            # 静默处理连接失败，不输出错误信息
            return False

    def read_line(self) -> Optional[str]:
        """读取一行数据"""
        if not self.connection:
            return None
        try:
            return self.connection.readline().decode('ascii', errors='ignore').strip()
        except Exception:
            return None

    def close(self):
        """关闭串口连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


class ADSBDecoder:
    """ADS-B消息解码器 - 负责解析和解码ADS-B消息"""

    def __init__(self, cache_timeout: int = 10):
        self.cache_timeout = cache_timeout
        self.message_cache = defaultdict(dict)  # icao -> {"even": data, "odd": data}

    def decode_message(self, hex_data: str) -> Optional[Tuple[str, str, int, int, int]]:
        """解码ADS-B十六进制消息"""
        if not hex_data or len(hex_data) != 28:
            return None

        try:
            # 转换为二进制
            binary_data = bin(int(hex_data, 16))[2:].zfill(112)

            # 检查消息格式 (DF=17)
            df_field = int(binary_data[:5], 2)
            if df_field != 17:
                return None

            # 提取ICAO地址
            icao = hex(int(binary_data[8:32], 2))[2:].upper().zfill(6)

            # 解析ME字段
            me_field = binary_data[32:88]
            type_code = int(me_field[:5], 2)

            # 只处理位置消息 (TC 9-18)
            if not (9 <= type_code <= 18):
                return None

            # 提取位置相关数据
            format_flag = int(me_field[21])  # 奇偶标志
            format_type = "even" if format_flag == 0 else "odd"

            altitude = self._decode_altitude(me_field[8:20])
            lat_cpr = int(me_field[22:39], 2)
            lon_cpr = int(me_field[39:56], 2)

            return icao, format_type, lat_cpr, lon_cpr, altitude

        except Exception as e:
            logging.warning(f"消息解码失败: {e}")
            return None

    def _decode_altitude(self, altitude_bits: str) -> int:
        """解码高度信息"""
        if len(altitude_bits) != 12:
            return 0

        q_bit = int(altitude_bits[7])
        alt_value = int(altitude_bits[:7] + altitude_bits[8:], 2)

        if q_bit == 1:
            return alt_value * 25 - 1000  # 25英尺精度
        else:
            return alt_value * 100 - 1000  # 100英尺精度

    def process_position_message(self, hex_data: str) -> Optional[AircraftPosition]:
        """处理位置消息，尝试解码完整位置"""
        decoded = self.decode_message(hex_data)
        if not decoded:
            return None

        icao, msg_type, lat_cpr, lon_cpr, altitude = decoded
        current_time = time.time()

        # 清理过期缓存
        self._cleanup_cache(current_time)

        # 存储消息
        self.message_cache[icao][msg_type] = (lat_cpr, lon_cpr, current_time, altitude)

        # 尝试位置解码
        if "even" in self.message_cache[icao] and "odd" in self.message_cache[icao]:
            return self._decode_position(icao)

        return None

    def _cleanup_cache(self, current_time: float):
        """清理过期的消息缓存"""
        expired_icaos = []
        for icao, messages in self.message_cache.items():
            expired_types = []
            for msg_type, data in messages.items():
                if current_time - data[2] > self.cache_timeout:
                    expired_types.append(msg_type)

            for msg_type in expired_types:
                del messages[msg_type]

            if not messages:
                expired_icaos.append(icao)

        for icao in expired_icaos:
            del self.message_cache[icao]

    def _decode_position(self, icao: str) -> Optional[AircraftPosition]:
        """使用CPR算法解码位置"""
        even_data = self.message_cache[icao]["even"]
        odd_data = self.message_cache[icao]["odd"]

        lat, lon = self._cpr_global_decode(even_data, odd_data)
        if lat is None or lon is None:
            return None

        # 使用最新消息的高度
        altitude = even_data[3] if even_data[2] >= odd_data[2] else odd_data[3]

        return AircraftPosition(
            icao=icao,
            latitude=lat,
            longitude=lon,
            altitude=altitude,
            timestamp=max(even_data[2], odd_data[2])
        )

    def _cpr_global_decode(self, even_data: Tuple, odd_data: Tuple) -> Tuple[Optional[float], Optional[float]]:
        """CPR全球位置解码算法"""
        lat_even, lon_even, _ = even_data[:3]
        lat_odd, lon_odd, _ = odd_data[:3]

        # 归一化CPR值到[0,1)
        lat_even_norm = lat_even / 131072.0
        lon_even_norm = lon_even / 131072.0
        lat_odd_norm = lat_odd / 131072.0
        lon_odd_norm = lon_odd / 131072.0

        # 计算纬度索引
        j = math.floor(59 * lat_even_norm - 60 * lat_odd_norm + 0.5)

        # 计算纬度
        dlat_even = 360.0 / 60
        dlat_odd = 360.0 / 59

        lat_even_calc = dlat_even * (j % 60 + lat_even_norm)
        lat_odd_calc = dlat_odd * (j % 59 + lat_odd_norm)

        # 纬度范围调整
        if lat_even_calc >= 270:
            lat_even_calc -= 360
        if lat_odd_calc >= 270:
            lat_odd_calc -= 360

        # 计算经度区域数量
        nl_even = self._calculate_nl(lat_even_calc)
        nl_odd = self._calculate_nl(lat_odd_calc)

        if nl_even != nl_odd:
            return None, None

        # 确定使用哪个纬度（基于最新消息）
        use_even = even_data[2] >= odd_data[2]
        latitude = lat_even_calc if use_even else lat_odd_calc
        nl = nl_even

        # 计算经度
        if use_even:
            m = math.floor(lon_even_norm * (nl - 1) - lon_odd_norm * nl + 0.5)
            ni = max(nl, 1)
            longitude = (360.0 / ni) * (m % ni + lon_even_norm)
        else:
            m = math.floor(lon_even_norm * (nl - 1) - lon_odd_norm * nl + 0.5)
            ni = max(nl - 1, 1)
            longitude = (360.0 / ni) * (m % ni + lon_odd_norm)

        # 经度范围调整
        if longitude > 180:
            longitude -= 360
        elif longitude < -180:
            longitude += 360

        return latitude, longitude

    def _calculate_nl(self, latitude: float) -> int:
        """计算给定纬度的经度区域数量NL"""
        abs_lat = abs(latitude)

        if abs_lat >= 87.0:
            return 1
        elif abs_lat >= 86.5:
            return 2

        # 简化的NL计算
        nz = 15
        a = 1 - math.cos(math.pi / (2 * nz))
        cos_lat = math.cos(math.radians(abs_lat))

        if cos_lat < 1e-9:
            return 1

        d = 1 - a / (cos_lat ** 2)
        d = max(min(d, 1), -1)  # 限制在有效范围内

        return int(2 * math.pi / math.acos(d))


class DataLogger:
    """数据记录器 - 负责记录原始数据和解码结果"""

    def __init__(self, log_dir: str = "."):
        self.log_dir = log_dir
        self.raw_log_file = None
        self.decoded_log_file = None

    def initialize(self):
        """初始化日志文件"""
        try:
            raw_log_path = os.path.join(self.log_dir, 'adsb_raw.log')
            decoded_log_path = os.path.join(self.log_dir, 'adsb_decoded.log')

            self.raw_log_file = open(raw_log_path, 'a', encoding='utf-8')
            self.decoded_log_file = open(decoded_log_path, 'a', encoding='utf-8')

            return True
        except Exception as e:
            print(f"日志文件初始化失败: {e}")
            return False

    def log_raw_data(self, data: str):
        """记录原始数据"""
        if self.raw_log_file:
            self.raw_log_file.write(f"{data}\n")
            self.raw_log_file.flush()

    def log_position(self, position: AircraftPosition):
        """记录解码后的位置信息（包含ECEF和ENU坐标）"""
        if self.decoded_log_file:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(position.timestamp))
            line = (f"{timestamp},{position.icao},"
                   f"{position.latitude:.6f},{position.longitude:.6f},{position.altitude},"
                   f"{position.ecef_x:.1f},{position.ecef_y:.1f},{position.ecef_z:.1f},"
                   f"{position.enu_e:.1f},{position.enu_n:.1f},{position.enu_u:.1f}\n")
            self.decoded_log_file.write(line)
            self.decoded_log_file.flush()

    def close(self):
        """关闭日志文件"""
        if self.raw_log_file:
            self.raw_log_file.close()
        if self.decoded_log_file:
            self.decoded_log_file.close()


class NavigationSystem:
    """导航系统主类 - 整合所有组件"""

    def __init__(self, target_port: str = "10"):
        self.target_port = target_port
        self.serial_manager = SerialManager()
        self.decoder = ADSBDecoder()
        self.logger = DataLogger()
        self.running = False

    def initialize(self) -> bool:
        """初始化系统"""
        print("ADS-B导航系统初始化...")

        # 初始化日志
        if not self.logger.initialize():
            return False

        # 连接串口
        if not self.serial_manager.connect(self.target_port):
            print("串口连接失败")
            return False

        print("系统初始化完成")
        return True

    def start(self):
        """启动导航系统"""
        if not self.initialize():
            return

        self.running = True
        print("开始接收ADS-B数据...")
        print("按 Ctrl+C 停止程序")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n接收到停止信号")
        finally:
            self._cleanup()

    def _main_loop(self):
        """主处理循环"""
        decoded_count = 0

        while self.running:
            # 读取串口数据
            raw_data = self.serial_manager.read_line()
            if not raw_data:
                continue

            # 记录原始数据
            self.logger.log_raw_data(raw_data)

            # 过滤有效数据（以*开头的28字节十六进制）
            if not raw_data.startswith('*') or len(raw_data) < 29:
                continue

            hex_data = raw_data[1:29]  # 提取十六进制部分

            # 解码位置信息
            position = self.decoder.process_position_message(hex_data)
            if position:
                decoded_count += 1
                print(f"✈️ {position}")
                self.logger.log_position(position)

    def _cleanup(self):
        """清理资源"""
        print("正在关闭系统...")
        self.running = False
        self.serial_manager.close()
        self.logger.close()
        print("系统已关闭")


def main():
    """主程序入口"""
    import sys
    import ctypes

    print("ADS-B导航数据处理系统")
    print("=" * 30)
    print("基于面向对象架构重新设计")
    print("功能：串口通信、消息解码、位置计算、数据记录")

    # Windows权限检查
    if os.name == 'nt':
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            print(f"管理员权限: {'是' if is_admin else '否'}")
            if not is_admin:
                print("提示：如需访问高端口号(COM10+)，建议以管理员身份运行")
        except:
            print("无法检查管理员权限")

    print("\n正在启动系统...")

    # 创建并启动导航系统
    nav_system = NavigationSystem(target_port="10")
    nav_system.start()


if __name__ == "__main__":
    main()