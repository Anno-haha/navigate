#!/usr/bin/env python3
"""
分析ECEF坐标数据
验证转换结果的合理性和一致性
"""

import math
import csv
from typing import List, Tuple

def read_decoded_log(filename: str = "adsb_decoded.log") -> List[Tuple]:
    """读取解码日志文件"""
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) >= 11:  # 包含ECEF和ENU坐标的最新格式
                    timestamp = parts[0]
                    icao = parts[1]
                    lat = float(parts[2])
                    lon = float(parts[3])
                    alt = int(parts[4])
                    ecef_x = float(parts[5])
                    ecef_y = float(parts[6])
                    ecef_z = float(parts[7])
                    enu_e = float(parts[8])
                    enu_n = float(parts[9])
                    enu_u = float(parts[10])
                    data.append((timestamp, icao, lat, lon, alt, ecef_x, ecef_y, ecef_z, enu_e, enu_n, enu_u))
                elif len(parts) >= 8:  # 包含ECEF坐标的格式
                    timestamp = parts[0]
                    icao = parts[1]
                    lat = float(parts[2])
                    lon = float(parts[3])
                    alt = int(parts[4])
                    ecef_x = float(parts[5])
                    ecef_y = float(parts[6])
                    ecef_z = float(parts[7])
                    data.append((timestamp, icao, lat, lon, alt, ecef_x, ecef_y, ecef_z, None, None, None))
                elif len(parts) >= 5:  # 旧格式，只有经纬度高度
                    timestamp = parts[0]
                    icao = parts[1]
                    lat = float(parts[2])
                    lon = float(parts[3])
                    alt = int(parts[4])
                    data.append((timestamp, icao, lat, lon, alt, None, None, None, None, None, None))
    except FileNotFoundError:
        print(f"文件 {filename} 不存在")
    except Exception as e:
        print(f"读取文件时出错: {e}")
    
    return data

def calculate_distance_from_earth_center(x: float, y: float, z: float) -> float:
    """计算到地心的距离"""
    return math.sqrt(x*x + y*y + z*z)

def analyze_ecef_data(data: List[Tuple]):
    """分析ECEF数据"""
    print("ECEF坐标数据分析")
    print("=" * 50)
    
    # 分离有ECEF数据和无ECEF数据的记录
    ecef_data = [row for row in data if row[5] is not None]
    old_data = [row for row in data if row[5] is None]
    
    print(f"总记录数: {len(data)}")
    print(f"包含ECEF坐标的记录: {len(ecef_data)}")
    print(f"仅包含经纬度的记录: {len(old_data)}")
    print()
    
    if not ecef_data:
        print("没有ECEF坐标数据可分析")
        return
    
    # 分析ECEF坐标范围
    x_values = [row[5] for row in ecef_data]
    y_values = [row[6] for row in ecef_data]
    z_values = [row[7] for row in ecef_data]
    
    print("ECEF坐标范围分析:")
    print(f"X坐标: {min(x_values):.1f} ~ {max(x_values):.1f} m")
    print(f"Y坐标: {min(y_values):.1f} ~ {max(y_values):.1f} m")
    print(f"Z坐标: {min(z_values):.1f} ~ {max(z_values):.1f} m")
    print()
    
    # 分析到地心距离
    distances = []
    for row in ecef_data:
        dist = calculate_distance_from_earth_center(row[5], row[6], row[7])
        distances.append(dist)
    
    print("到地心距离分析:")
    print(f"最小距离: {min(distances):.1f} m")
    print(f"最大距离: {max(distances):.1f} m")
    print(f"平均距离: {sum(distances)/len(distances):.1f} m")
    print(f"地球半径参考: ~6,371,000 m")
    print()
    
    # 分析不同飞机的数据
    icao_groups = {}
    for row in ecef_data:
        icao = row[1]
        if icao not in icao_groups:
            icao_groups[icao] = []
        icao_groups[icao].append(row)
    
    print(f"检测到的飞机数量: {len(icao_groups)}")
    print("各飞机数据统计:")
    
    for icao, records in icao_groups.items():
        if len(records) >= 2:
            # 计算飞行轨迹长度
            total_distance = 0
            for i in range(1, len(records)):
                prev = records[i-1]
                curr = records[i]
                
                # 计算3D距离
                dx = curr[5] - prev[5]
                dy = curr[6] - prev[6]
                dz = curr[7] - prev[7]
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                total_distance += distance
            
            avg_alt = sum(r[4] for r in records) / len(records)
            print(f"  {icao}: {len(records)}条记录, 平均高度{avg_alt:.0f}ft, 轨迹长度{total_distance:.1f}m")
    
    print()

def validate_ecef_conversion():
    """验证ECEF转换的正确性"""
    print("ECEF转换验证")
    print("=" * 30)
    
    # 使用nav.py中的转换器进行验证
    try:
        import nav
        
        # 测试几个已知点
        test_points = [
            ("北京", 39.9, 116.4, 50),
            ("上海", 31.2, 121.5, 10),
            ("赤道", 0.0, 0.0, 0),
        ]
        
        for name, lat, lon, alt_m in test_points:
            x, y, z = nav.ECEFConverter.lla_to_ecef(lat, lon, alt_m)
            distance = calculate_distance_from_earth_center(x, y, z)
            
            print(f"{name}: ({lat}°, {lon}°, {alt_m}m)")
            print(f"  ECEF: ({x:.1f}, {y:.1f}, {z:.1f}) m")
            print(f"  距地心: {distance:.1f} m")
            print()
            
    except ImportError:
        print("无法导入nav模块进行验证")

def main():
    """主函数"""
    print("ADS-B ECEF坐标数据分析工具")
    print("=" * 60)
    
    # 读取数据
    data = read_decoded_log()
    
    if not data:
        print("没有找到数据文件或数据为空")
        return
    
    # 分析数据
    analyze_ecef_data(data)
    
    # 验证转换
    validate_ecef_conversion()
    
    print("分析完成！")
    print("\n说明:")
    print("- ECEF坐标系以地心为原点")
    print("- X轴指向本初子午线与赤道交点")
    print("- Y轴指向东经90°与赤道交点")
    print("- Z轴指向北极")
    print("- 距地心距离应在6,356,752m(极半径)到6,378,137m(赤道半径)之间")

if __name__ == "__main__":
    main()
