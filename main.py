import serial
import serial.tools.list_ports
import time
import math
import os
from collections import defaultdict
import sys
import ctypes  # 添加缺失的ctypes导入

# 获取当前脚本位置
current_dir = os.path.dirname(os.path.abspath(__file__))


def list_available_ports():
    """列出所有可用串口"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def setup_serial(target_port=None):
    """设置串口连接，处理Windows和Linux平台差异"""
    available_ports = list_available_ports()
    print("可用的串口:")
    for port in available_ports:
        print(f" - {port}")

    # 如果指定了目标端口，尝试连接
    if target_port:
        # 处理Windows上COM10及以上端口的特殊格式
        if os.name == 'nt' and target_port.isdigit() and int(target_port) >= 10:
            port_name = f'\\\\.\\COM{target_port}'
        else:
            port_name = target_port

        print(f"尝试连接目标串口: {port_name}")
        try:
            return serial.Serial(
                port=port_name,
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
        except Exception as e:
            print(f"连接目标串口失败: {e}")

    # 尝试自动连接第一个可用端口
    if available_ports:
        print("尝试自动连接第一个可用串口")
        try:
            return serial.Serial(
                port=available_ports[0],
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
        except Exception as e:
            print(f"连接 {available_ports[0]} 失败: {e}")

    return None


# 全局变量存储奇/偶格式消息
message_cache = defaultdict(dict)  # icao: {"even": (lat_cpr, lon_cpr, timestamp), "odd": (...)}
MAX_CACHE_AGE = 10  # 消息缓存最大有效期（秒）


def calc_NL(lat):
    """计算经度区域数量NL"""
    abs_lat = abs(lat)
    if abs_lat >= 87.0:
        return 1
    elif abs_lat >= 86.5:
        return 2
    # 简化的NL计算（完整实现需按标准分段）
    NZ = 15
    a = 1 - math.cos(math.pi / (2 * NZ))
    cos_lat = math.cos(math.radians(abs_lat))
    if cos_lat < 1e-9:  # 避免除零
        return 1
    d = 1 - a / (cos_lat ** 2)
    d = max(min(d, 1), -1)  # 确保d在[-1,1]范围内
    return int(2 * math.pi / math.acos(d))


def decode_altitude(alt_bits):
    """解码高度信息"""
    if len(alt_bits) != 12:
        return 0

    Q = int(alt_bits[7])  # Q位（高度字段的第8位）
    alt_bits_noq = alt_bits[:7] + alt_bits[8:]  # 移除Q位
    N = int(alt_bits_noq, 2)

    if Q == 1:
        # Q=1 表示25英尺间隔
        altitude = N * 25 - 1000
    else:
        # Q=0 表示100英尺间隔（无格雷码转换）
        altitude = N * 100 - 1000
    return altitude


def cpr_global_decode(even_msg, odd_msg):
    """CPR全球位置解码"""
    lat_even, lon_even, _ = even_msg
    lat_odd, lon_odd, _ = odd_msg

    # 归一化CPR值
    lat_even /= 131072.0
    lon_even /= 131072.0
    lat_odd /= 131072.0
    lon_odd /= 131072.0

    # 计算纬度索引j
    j = math.floor(59 * lat_even - 60 * lat_odd + 0.5)

    # 计算偶/奇纬度
    dlat_even = 360.0 / 60
    rlat_even = dlat_even * (j % 60 + lat_even)
    if rlat_even >= 270: rlat_even -= 360

    dlat_odd = 360.0 / 59
    rlat_odd = dlat_odd * (j % 59 + lat_odd)
    if rlat_odd >= 270: rlat_odd -= 360

    # 计算NL
    NL_even = calc_NL(rlat_even)
    NL_odd = calc_NL(rlat_odd)
    if NL_even != NL_odd:
        return None, None  # NL不匹配

    # 确定最后接收的消息
    last_is_even = even_msg[2] >= odd_msg[2]
    rlat = rlat_even if last_is_even else rlat_odd
    NL = NL_even

    # 计算经度索引m
    if last_is_even:
        m = math.floor(lon_even * (NL - 1) - lon_odd * NL + 0.5)
        n_i = max(NL, 1)
        lon = (360.0 / n_i) * (m % n_i + lon_even)
    else:
        m = math.floor(lon_even * (NL - 1) - lon_odd * NL + 0.5)
        n_i = max(NL - 1, 1)
        lon = (360.0 / n_i) * (m % n_i + lon_odd)

    # 经度范围调整
    if lon > 180: lon -= 360
    if lon < -180: lon += 360

    return rlat, lon


def decode_adsb_message(hex_str):
    """解码ADS-B消息"""
    # 确保输入正确
    if not hex_str or len(hex_str) != 28:  # 28字节十六进制
        return None

    try:
        # 转换为二进制字符串
        bin_str = bin(int(hex_str, 16))[2:].zfill(112)

        # 解析DF字段 (5位)
        DF = int(bin_str[:5], 2)
        if DF != 17:  # 仅处理ADS-B消息 (DF=17)
            return None

        # 解析ICAO地址 (24位)
        icao = hex(int(bin_str[8:32], 2))[2:].upper().zfill(6)

        # 解析ME字段 (56位)
        me_bin = bin_str[32:88]

        # 解析消息类型 (5位)
        tc = int(me_bin[:5], 2)
        if not (9 <= tc <= 18):  # 仅处理空中位置消息 (9-18)
            return None

        # 解析F位 (奇偶格式)
        F = int(me_bin[21])
        format_type = "even" if F == 0 else "odd"

        # 解析高度 (12位)
        alt_bits = me_bin[8:20]
        altitude = decode_altitude(alt_bits)

        # 解析CPR纬度和经度 (各17位)
        lat_cpr = int(me_bin[22:39], 2)
        lon_cpr = int(me_bin[39:56], 2)

        return icao, format_type, lat_cpr, lon_cpr, altitude
    except Exception as e:
        print(f"解码错误: {e}")
        return None


def process_adsb_message(hex_str):
    """处理ADS-B消息并尝试解码位置"""
    result = decode_adsb_message(hex_str)
    if not result:
        return None

    icao, format_type, lat_cpr, lon_cpr, altitude = result
    current_time = time.time()

    # 清除过期缓存
    for icao_key in list(message_cache.keys()):
        for msg_type in ["even", "odd"]:
            if msg_type in message_cache[icao_key]:
                msg_time = message_cache[icao_key][msg_type][2]
                if current_time - msg_time > MAX_CACHE_AGE:
                    del message_cache[icao_key][msg_type]
                    # 如果空则移除整个ICAO条目
                    if not message_cache[icao_key]:
                        del message_cache[icao_key]

    # 存储当前消息
    message_cache[icao][format_type] = (lat_cpr, lon_cpr, current_time, altitude)

    # 检查是否有一对消息
    if "even" in message_cache[icao] and "odd" in message_cache[icao]:
        even_msg = message_cache[icao]["even"]
        odd_msg = message_cache[icao]["odd"]

        # 尝试全球解码
        lat, lon = cpr_global_decode(even_msg[:3], odd_msg[:3])
        if lat is not None and lon is not None:
            # 使用最新消息的高度
            altitude = even_msg[3] if even_msg[2] >= odd_msg[2] else odd_msg[3]
            return icao, lat, lon, altitude

    return None


# 主程序
def main():
    # 尝试连接串口
    ser = setup_serial("10")  # 尝试连接COM10
    if ser is None:
        print("无法连接到任何串口，程序退出")
        sys.exit(1)

    print(f"成功连接到串口: {ser.port}")
    print("开始接收ADS-B数据...")

    try:
        # 创建日志文件
        raw_log = open(os.path.join(current_dir, 'adsb_raw.log'), 'a')
        decoded_log = open(os.path.join(current_dir, 'adsb_decoded.log'), 'a')

        while True:
            try:
                # 尝试读取一行
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if not line:
                    continue

                # 记录原始数据
                raw_log.write(line + '\n')
                raw_log.flush()  # 确保即时写入

                # 只处理以*开头的有效行
                if not line.startswith('*'):
                    continue

                # 提取有效的28字节十六进制数据
                hex_str = line[1:29]  # 提取28字节十六进制
                if len(hex_str) != 28:
                    continue

                # 处理ADS-B消息
                result = process_adsb_message(hex_str)

                if result:
                    icao, lat, lon, alt = result
                    output = f"ICAO: {icao} | 纬度: {lat:.6f}° | 经度: {lon:.6f}° | 高度: {alt}英尺"
                    print(output)

                    # 记录解码后的数据
                    decoded_log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{icao},{lat:.6f},{lon:.6f},{alt}\n")
                    decoded_log.flush()

            except UnicodeDecodeError:
                # 处理编码错误
                continue
            except Exception as e:
                print(f"处理错误: {e}")
                continue

    except KeyboardInterrupt:
        print("\n程序终止")
    finally:
        # 关闭串口和文件
        ser.close()
        raw_log.close()
        decoded_log.close()
        print("串口已关闭")
        print("日志文件已保存")


if __name__ == "__main__":
    # 打印提示信息
    print("ADS-B数据解码程序")
    print("=================")
    print("程序将尝试检测和连接可用串口")
    print("波特率设置为115200，数据格式：*开头+28位十六进制数")

    # 检查管理员权限
    if os.name == 'nt':
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        print(f"管理员权限: {'是' if is_admin else '否'}")
        if not is_admin:
            print("警告：未以管理员身份运行，可能导致串口访问问题")
            print("如需访问COM10及以上的端口，请以管理员身份运行本程序")

    print("按Ctrl+C终止程序")
    print()

    main()