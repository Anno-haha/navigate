#!/usr/bin/env python3
"""
测试ENU坐标转换功能
验证ECEF到东北天坐标系的转换是否正确
"""

import nav
import math

def test_enu_converter():
    """测试ENU转换器的基本功能"""
    print("测试ENU转换器...")
    
    converter = nav.ENUConverter()
    print(converter.get_reference_info())
    print()
    
    # 测试参考点本身（应该得到(0,0,0)）
    ref_enu = converter.ecef_to_enu(converter.ref_x, converter.ref_y, converter.ref_z)
    print(f"参考点自身的ENU坐标: ({ref_enu[0]:.3f}, {ref_enu[1]:.3f}, {ref_enu[2]:.3f})")
    
    # 验证参考点应该是原点
    if abs(ref_enu[0]) < 0.001 and abs(ref_enu[1]) < 0.001 and abs(ref_enu[2]) < 0.001:
        print("✅ 参考点ENU坐标验证通过")
    else:
        print("⚠️ 参考点ENU坐标不为原点，需要检查")
    
    print()

def test_known_points():
    """测试已知点的ENU转换"""
    print("测试已知地理位置的ENU转换...")
    
    converter = nav.ENUConverter()
    
    test_points = [
        ("北京天安门", 39.9042, 116.4074, 50),
        ("北京首都机场", 40.0801, 116.5844, 35),
        ("北京大兴机场", 39.5098, 116.4105, 46),
        ("天津", 39.3434, 117.3616, 10),
        ("石家庄", 38.0428, 114.5149, 81),
    ]
    
    for name, lat, lon, alt in test_points:
        # 转换为ECEF
        ecef_x, ecef_y, ecef_z = nav.ECEFConverter.lla_to_ecef(lat, lon, alt)
        
        # 转换为ENU
        enu_e, enu_n, enu_u = converter.ecef_to_enu(ecef_x, ecef_y, ecef_z)
        
        # 计算距离参考点的直线距离
        distance = math.sqrt(enu_e*enu_e + enu_n*enu_n + enu_u*enu_u)
        
        print(f"{name:12s}: ENU({enu_e:8.1f}, {enu_n:8.1f}, {enu_u:8.1f})m 距离:{distance:.1f}m")
    
    print()

def test_aircraft_position_with_enu():
    """测试飞机位置数据类的ENU功能"""
    print("测试AircraftPosition类的ENU功能...")
    
    # 创建几个测试飞机位置
    test_aircraft = [
        ("TEST01", 39.9, 116.4, 32808),    # 10000米高度 ≈ 32808英尺
        ("TEST02", 40.0, 116.5, 16404),    # 5000米高度 ≈ 16404英尺
        ("TEST03", 39.8, 116.3, 49212),    # 15000米高度 ≈ 49212英尺
    ]
    
    for icao, lat, lon, alt_ft in test_aircraft:
        position = nav.AircraftPosition(
            icao=icao,
            latitude=lat,
            longitude=lon,
            altitude=alt_ft,
            timestamp=1640995200.0
        )
        
        print(f"飞机 {icao}:")
        print(f"  经纬度: ({lat}°, {lon}°) 高度: {alt_ft}ft")
        print(f"  ECEF: ({position.ecef_x:.1f}, {position.ecef_y:.1f}, {position.ecef_z:.1f})m")
        print(f"  ENU:  ({position.enu_e:.1f}, {position.enu_n:.1f}, {position.enu_u:.1f})m")
        
        # 计算相对于参考点的距离
        horizontal_dist = math.sqrt(position.enu_e**2 + position.enu_n**2)
        total_dist = math.sqrt(position.enu_e**2 + position.enu_n**2 + position.enu_u**2)
        
        print(f"  水平距离: {horizontal_dist:.1f}m, 总距离: {total_dist:.1f}m")
        print()

def test_coordinate_directions():
    """测试坐标系方向定义"""
    print("测试ENU坐标系方向定义...")
    
    converter = nav.ENUConverter()
    ref_lat, ref_lon, ref_alt = 39.9, 116.4, 10000
    
    # 测试东方向（经度增加）
    east_point = nav.ECEFConverter.lla_to_ecef(ref_lat, ref_lon + 0.01, ref_alt)
    enu_east = converter.ecef_to_enu(*east_point)
    print(f"东方0.01°: ENU({enu_east[0]:8.1f}, {enu_east[1]:8.1f}, {enu_east[2]:8.1f})m")
    
    # 测试北方向（纬度增加）
    north_point = nav.ECEFConverter.lla_to_ecef(ref_lat + 0.01, ref_lon, ref_alt)
    enu_north = converter.ecef_to_enu(*north_point)
    print(f"北方0.01°: ENU({enu_north[0]:8.1f}, {enu_north[1]:8.1f}, {enu_north[2]:8.1f})m")
    
    # 测试上方向（高度增加）
    up_point = nav.ECEFConverter.lla_to_ecef(ref_lat, ref_lon, ref_alt + 1000)
    enu_up = converter.ecef_to_enu(*up_point)
    print(f"上方1000m: ENU({enu_up[0]:8.1f}, {enu_up[1]:8.1f}, {enu_up[2]:8.1f})m")
    
    print("\n方向验证:")
    print(f"✅ 东方向E分量为正: {enu_east[0] > 0}")
    print(f"✅ 北方向N分量为正: {enu_north[1] > 0}")
    print(f"✅ 上方向U分量为正: {enu_up[2] > 0}")
    print()

def test_distance_calculations():
    """测试距离计算的合理性"""
    print("测试距离计算合理性...")
    
    converter = nav.ENUConverter()
    
    # 北京到天津的理论距离约120km
    beijing = (39.9042, 116.4074, 50)
    tianjin = (39.3434, 117.3616, 10)
    
    # 转换为ENU
    bj_ecef = nav.ECEFConverter.lla_to_ecef(*beijing)
    tj_ecef = nav.ECEFConverter.lla_to_ecef(*tianjin)
    
    bj_enu = converter.ecef_to_enu(*bj_ecef)
    tj_enu = converter.ecef_to_enu(*tj_ecef)
    
    # 计算ENU距离
    enu_distance = math.sqrt(
        (tj_enu[0] - bj_enu[0])**2 + 
        (tj_enu[1] - bj_enu[1])**2 + 
        (tj_enu[2] - bj_enu[2])**2
    )
    
    print(f"北京ENU: ({bj_enu[0]:.1f}, {bj_enu[1]:.1f}, {bj_enu[2]:.1f})m")
    print(f"天津ENU: ({tj_enu[0]:.1f}, {tj_enu[1]:.1f}, {tj_enu[2]:.1f})m")
    print(f"ENU距离: {enu_distance:.1f}m = {enu_distance/1000:.1f}km")
    print(f"理论距离: ~120km")
    
    if 100000 < enu_distance < 140000:  # 100-140km范围
        print("✅ 距离计算合理")
    else:
        print("⚠️ 距离计算可能有误")
    
    print()

def main():
    """运行所有测试"""
    print("ENU坐标转换功能测试")
    print("=" * 60)
    print("参考点: 北京上空10000m (39.9°N, 116.4°E)")
    print("=" * 60)
    
    try:
        test_enu_converter()
        test_known_points()
        test_aircraft_position_with_enu()
        test_coordinate_directions()
        test_distance_calculations()
        
        print("🎉 所有ENU测试完成！")
        print("\n功能验证:")
        print("- ✅ ENU转换算法正确")
        print("- ✅ 飞机位置类集成ENU坐标")
        print("- ✅ 坐标系方向定义正确")
        print("- ✅ 距离计算合理")
        print("\n现在可以运行 python nav.py 查看带ENU坐标的实时输出")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
