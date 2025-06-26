#!/usr/bin/env python3
"""
演示ENU坐标输出功能
模拟真实的ADS-B数据输出，展示完整的坐标信息
"""

import nav
import time
import random

def simulate_aircraft_data():
    """模拟飞机数据"""
    # 模拟几架在北京周边的飞机
    aircraft_data = [
        {
            "icao": "CA1234",
            "base_lat": 39.9,
            "base_lon": 116.4,
            "base_alt": 35000,
            "speed": 0.001,  # 度/秒
            "direction": 45   # 东北方向
        },
        {
            "icao": "MU5678", 
            "base_lat": 40.1,
            "base_lon": 116.6,
            "base_alt": 28000,
            "speed": 0.0008,
            "direction": 225  # 西南方向
        },
        {
            "icao": "CZ9012",
            "base_lat": 39.7,
            "base_lon": 116.2,
            "base_alt": 42000,
            "speed": 0.0012,
            "direction": 90   # 正东方向
        }
    ]
    return aircraft_data

def update_aircraft_position(aircraft, time_step):
    """更新飞机位置"""
    import math
    
    # 根据方向和速度更新位置
    direction_rad = math.radians(aircraft["direction"])
    
    # 计算位置变化
    dlat = aircraft["speed"] * time_step * math.cos(direction_rad)
    dlon = aircraft["speed"] * time_step * math.sin(direction_rad)
    
    aircraft["base_lat"] += dlat
    aircraft["base_lon"] += dlon
    
    # 高度随机变化
    aircraft["base_alt"] += random.randint(-100, 100)
    aircraft["base_alt"] = max(20000, min(45000, aircraft["base_alt"]))

def demo_enu_output():
    """演示ENU坐标输出"""
    print("ADS-B导航数据处理系统 - ENU坐标演示")
    print("=" * 60)
    
    # 显示参考点信息
    converter = nav.ENUConverter()
    print(converter.get_reference_info())
    print()
    print("实时飞机位置数据 (包含经纬度、ECEF、ENU坐标):")
    print("-" * 60)
    
    # 初始化飞机数据
    aircraft_list = simulate_aircraft_data()
    
    try:
        for i in range(20):  # 模拟20次更新
            print(f"\n时间: {time.strftime('%H:%M:%S')}")
            print("-" * 40)
            
            for aircraft in aircraft_list:
                # 更新飞机位置
                if i > 0:  # 第一次不更新，显示初始位置
                    update_aircraft_position(aircraft, 1.0)
                
                # 创建飞机位置对象
                position = nav.AircraftPosition(
                    icao=aircraft["icao"],
                    latitude=aircraft["base_lat"],
                    longitude=aircraft["base_lon"],
                    altitude=aircraft["base_alt"],
                    timestamp=time.time()
                )
                
                # 显示完整信息
                print(f"✈️ {position}")
                
                # 显示详细的ENU信息
                horizontal_dist = (position.enu_e**2 + position.enu_n**2)**0.5
                print(f"   ENU详细: 东{position.enu_e:.0f}m 北{position.enu_n:.0f}m 上{position.enu_u:.0f}m (水平距离{horizontal_dist:.0f}m)")
            
            time.sleep(2)  # 等待2秒
            
    except KeyboardInterrupt:
        print("\n演示结束")

def analyze_enu_coordinates():
    """分析ENU坐标的含义"""
    print("\nENU坐标系说明:")
    print("=" * 40)
    print("参考点: 北京上空10000m (39.9°N, 116.4°E)")
    print("坐标系定义:")
    print("  E (East):  东向距离，正值表示在参考点东方")
    print("  N (North): 北向距离，正值表示在参考点北方")
    print("  U (Up):    天向距离，正值表示在参考点上方")
    print()
    
    # 展示一些典型位置的ENU坐标
    print("典型位置的ENU坐标:")
    print("-" * 30)
    
    converter = nav.ENUConverter()
    
    locations = [
        ("天安门广场", 39.9042, 116.4074, 50),
        ("首都机场T3", 40.0801, 116.5844, 35),
        ("大兴机场", 39.5098, 116.4105, 46),
        ("天津滨海机场", 39.1244, 117.3464, 3),
    ]
    
    for name, lat, lon, alt in locations:
        ecef_x, ecef_y, ecef_z = nav.ECEFConverter.lla_to_ecef(lat, lon, alt)
        enu_e, enu_n, enu_u = converter.ecef_to_enu(ecef_x, ecef_y, ecef_z)
        
        distance = (enu_e**2 + enu_n**2)**0.5
        direction = "东北" if enu_e > 0 and enu_n > 0 else \
                   "东南" if enu_e > 0 and enu_n < 0 else \
                   "西北" if enu_e < 0 and enu_n > 0 else "西南"
        
        print(f"{name:12s}: E{enu_e:8.0f}m N{enu_n:8.0f}m U{enu_u:8.0f}m")
        print(f"{'':14s}  距离{distance:6.0f}m 方向{direction}")

def show_log_format():
    """展示日志文件格式"""
    print("\n日志文件格式:")
    print("=" * 30)
    print("adsb_decoded.log 新格式包含11个字段:")
    print("时间戳,ICAO,纬度,经度,高度(英尺),ECEF_X,ECEF_Y,ECEF_Z,ENU_E,ENU_N,ENU_U")
    print()
    print("示例记录:")
    print("2025-06-26 19:30:00,CA1234,39.900000,116.400000,35000,-2182051.1,4395713.4,4075888.1,0.0,0.0,4572.0")
    print()
    print("字段说明:")
    print("  ECEF_X/Y/Z: 地心地固坐标 (米)")
    print("  ENU_E/N/U:  东北天坐标 (米，相对于北京上空10000m)")

def main():
    """主演示函数"""
    print("ENU坐标系功能演示")
    print("=" * 50)
    
    try:
        # 分析ENU坐标含义
        analyze_enu_coordinates()
        
        # 展示日志格式
        show_log_format()
        
        # 询问是否运行动态演示
        print("\n是否运行动态飞机位置演示? (y/n): ", end="")
        choice = input().lower().strip()
        
        if choice in ['y', 'yes', '是']:
            demo_enu_output()
        else:
            print("演示结束")
            
    except Exception as e:
        print(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
