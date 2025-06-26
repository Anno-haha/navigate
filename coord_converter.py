#!/usr/bin/env python3
"""
坐标转换器模块
提供经纬度到ECEF和ENU坐标系的转换功能
"""

import math


class CoordinateConverter:
    """坐标转换器类"""
    
    # WGS84椭球参数
    WGS84_A = 6378137.0  # 地球赤道半径（长半轴），单位：米
    WGS84_E2 = 6.69437999014e-3  # 第一偏心率平方
    
    # 参考点：北京上空10000m
    REF_LATITUDE = 39.9    # 北纬39.9度
    REF_LONGITUDE = 116.4  # 东经116.4度
    REF_ALTITUDE = 10000.0 # 高度10000米
    
    def __init__(self):
        """初始化转换器"""
        # 计算参考点的ECEF坐标
        self.ref_x, self.ref_y, self.ref_z = self.lla_to_ecef(
            self.REF_LATITUDE, self.REF_LONGITUDE, self.REF_ALTITUDE
        )
        
        # 将参考点经纬度转换为弧度
        self.ref_lat_rad = self.degrees_to_radians(self.REF_LATITUDE)
        self.ref_lon_rad = self.degrees_to_radians(self.REF_LONGITUDE)
        
        # 预计算三角函数值
        self.sin_lat = math.sin(self.ref_lat_rad)
        self.cos_lat = math.cos(self.ref_lat_rad)
        self.sin_lon = math.sin(self.ref_lon_rad)
        self.cos_lon = math.cos(self.ref_lon_rad)
    
    @classmethod
    def degrees_to_radians(cls, degrees):
        """度转弧度"""
        return degrees * math.pi / 180.0
    
    @classmethod
    def calculate_prime_vertical_radius(cls, lat_rad):
        """计算卯酉圈曲率半径 N"""
        sin_lat = math.sin(lat_rad)
        return cls.WGS84_A / math.sqrt(1 - cls.WGS84_E2 * sin_lat * sin_lat)
    
    @classmethod
    def lla_to_ecef(cls, latitude, longitude, altitude):
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
    
    def ecef_to_enu(self, ecef_x, ecef_y, ecef_z):
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
    
    def lla_to_enu(self, latitude, longitude, altitude):
        """
        直接将经纬度转换为ENU坐标
        
        Args:
            latitude: 纬度（度）
            longitude: 经度（度）
            altitude: 高度（米）
            
        Returns:
            (E, N, U): 东北天坐标 (米)
        """
        # 先转换为ECEF
        ecef_x, ecef_y, ecef_z = self.lla_to_ecef(latitude, longitude, altitude)
        
        # 再转换为ENU
        return self.ecef_to_enu(ecef_x, ecef_y, ecef_z)
    
    def get_reference_info(self):
        """获取参考点信息"""
        return {
            'latitude': self.REF_LATITUDE,
            'longitude': self.REF_LONGITUDE,
            'altitude': self.REF_ALTITUDE,
            'ecef_x': self.ref_x,
            'ecef_y': self.ref_y,
            'ecef_z': self.ref_z,
        }
    
    def calculate_distance(self, enu_e, enu_n, enu_u):
        """计算ENU坐标到参考点的距离"""
        return math.sqrt(enu_e**2 + enu_n**2 + enu_u**2)
    
    def calculate_horizontal_distance(self, enu_e, enu_n):
        """计算水平距离"""
        return math.sqrt(enu_e**2 + enu_n**2)
    
    def calculate_bearing(self, enu_e, enu_n):
        """计算方位角（从北向顺时针，度）"""
        bearing_rad = math.atan2(enu_e, enu_n)
        bearing_deg = math.degrees(bearing_rad)
        return (bearing_deg + 360) % 360  # 确保在0-360度范围内


def test_coordinate_converter():
    """测试坐标转换器"""
    print("测试坐标转换器...")
    
    converter = CoordinateConverter()
    
    # 测试点：北京天安门
    lat, lon, alt = 39.9042, 116.4074, 50
    
    print(f"测试点: ({lat}°, {lon}°, {alt}m)")
    
    # 转换为ECEF
    ecef_x, ecef_y, ecef_z = converter.lla_to_ecef(lat, lon, alt)
    print(f"ECEF坐标: ({ecef_x:.1f}, {ecef_y:.1f}, {ecef_z:.1f}) m")
    
    # 转换为ENU
    enu_e, enu_n, enu_u = converter.lla_to_enu(lat, lon, alt)
    print(f"ENU坐标: ({enu_e:.1f}, {enu_n:.1f}, {enu_u:.1f}) m")
    
    # 计算距离和方位
    distance = converter.calculate_distance(enu_e, enu_n, enu_u)
    h_distance = converter.calculate_horizontal_distance(enu_e, enu_n)
    bearing = converter.calculate_bearing(enu_e, enu_n)
    
    print(f"总距离: {distance:.1f} m")
    print(f"水平距离: {h_distance:.1f} m")
    print(f"方位角: {bearing:.1f}°")
    
    # 参考点信息
    ref_info = converter.get_reference_info()
    print(f"参考点: ({ref_info['latitude']}°, {ref_info['longitude']}°, {ref_info['altitude']}m)")


if __name__ == '__main__':
    test_coordinate_converter()
