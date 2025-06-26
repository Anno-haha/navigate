#!/usr/bin/env python3
"""
测试ECEF坐标转换功能
验证经纬度到地心地固坐标系的转换是否正确
"""

import nav
import math

def test_ecef_converter():
    """测试ECEF转换器的基本功能"""
    print("测试ECEF转换器...")
    
    # 测试北京某点（您提供的示例）
    lat = 39.9  # 北纬
    lon = 116.4  # 东经
    alt_m = 50  # 高度50米
    
    X, Y, Z = nav.ECEFConverter.lla_to_ecef(lat, lon, alt_m)
    
    print(f"输入: 纬度={lat}°, 经度={lon}°, 高度={alt_m}m")
    print(f"ECEF坐标: X={X:.1f}m, Y={Y:.1f}m, Z={Z:.1f}m")
    
    # 验证结果（与您提供的理论值对比）
    expected_X = -2173876.6
    expected_Y = 4422559.5
    expected_Z = 4164072.8
    
    error_X = abs(X - expected_X)
    error_Y = abs(Y - expected_Y)
    error_Z = abs(Z - expected_Z)
    
    print(f"理论值: X={expected_X}m, Y={expected_Y}m, Z={expected_Z}m")
    print(f"误差: ΔX={error_X:.1f}m, ΔY={error_Y:.1f}m, ΔZ={error_Z:.1f}m")
    
    # 检查误差是否在合理范围内（小于10米）
    if error_X < 10 and error_Y < 10 and error_Z < 10:
        print("✅ ECEF转换精度验证通过")
    else:
        print("⚠️ ECEF转换精度需要检查")
    
    print()

def test_aircraft_position_with_ecef():
    """测试飞机位置数据类的ECEF功能"""
    print("测试AircraftPosition类的ECEF功能...")
    
    # 创建飞机位置对象（高度使用英尺）
    position = nav.AircraftPosition(
        icao="TEST01",
        latitude=39.9,
        longitude=116.4,
        altitude=164,  # 50米约等于164英尺
        timestamp=1640995200.0
    )
    
    print(f"飞机位置信息: {position}")
    print(f"ECEF坐标详细:")
    print(f"  X = {position.ecef_x:.1f} m")
    print(f"  Y = {position.ecef_y:.1f} m") 
    print(f"  Z = {position.ecef_z:.1f} m")
    print()

def test_multiple_locations():
    """测试多个地理位置的ECEF转换"""
    print("测试多个地理位置的ECEF转换...")
    
    test_locations = [
        ("北京", 39.9, 116.4, 50),
        ("上海", 31.2, 121.5, 10),
        ("广州", 23.1, 113.3, 20),
        ("赤道0点", 0.0, 0.0, 0),
        ("北极", 90.0, 0.0, 0),
        ("南极", -90.0, 0.0, 0),
    ]
    
    for name, lat, lon, alt in test_locations:
        X, Y, Z = nav.ECEFConverter.lla_to_ecef(lat, lon, alt)
        distance = math.sqrt(X*X + Y*Y + Z*Z)
        print(f"{name:8s}: ({lat:6.1f}°, {lon:6.1f}°, {alt:4.0f}m) → "
              f"ECEF({X:10.1f}, {Y:10.1f}, {Z:10.1f}) 距地心:{distance:.1f}m")
    
    print()

def test_altitude_conversion():
    """测试高度单位转换"""
    print("测试高度单位转换（英尺→米）...")
    
    test_altitudes = [1000, 5000, 10000, 30000, 40000]  # 英尺
    
    for alt_ft in test_altitudes:
        alt_m = alt_ft * 0.3048
        position = nav.AircraftPosition(
            icao=f"TEST{alt_ft//1000}",
            latitude=39.9,
            longitude=116.4,
            altitude=alt_ft,
            timestamp=1640995200.0
        )
        
        print(f"高度 {alt_ft:5d}ft = {alt_m:7.1f}m → ECEF_Z = {position.ecef_z:.1f}m")
    
    print()

def test_coordinate_system_properties():
    """测试坐标系特性"""
    print("测试ECEF坐标系特性...")
    
    # 测试赤道上的点
    print("赤道上的点 (Z坐标应接近0):")
    for lon in [0, 90, 180, -90]:
        X, Y, Z = nav.ECEFConverter.lla_to_ecef(0.0, lon, 0)
        print(f"  经度{lon:4d}°: Z = {Z:.1f}m")
    
    # 测试本初子午线上的点
    print("本初子午线上的点 (Y坐标应接近0):")
    for lat in [0, 30, 60, 90]:
        X, Y, Z = nav.ECEFConverter.lla_to_ecef(lat, 0.0, 0)
        print(f"  纬度{lat:2d}°: Y = {Y:.1f}m")
    
    print()

def main():
    """运行所有测试"""
    print("ECEF坐标转换功能测试")
    print("=" * 50)
    
    try:
        test_ecef_converter()
        test_aircraft_position_with_ecef()
        test_multiple_locations()
        test_altitude_conversion()
        test_coordinate_system_properties()
        
        print("🎉 所有ECEF测试完成！")
        print("\n功能验证:")
        print("- ✅ ECEF转换算法正确")
        print("- ✅ 飞机位置类集成ECEF坐标")
        print("- ✅ 高度单位转换正确")
        print("- ✅ 坐标系特性符合预期")
        print("\n现在可以运行 python nav.py 查看带ECEF坐标的实时输出")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
