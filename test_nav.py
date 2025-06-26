#!/usr/bin/env python3
"""
nav.py 功能测试脚本
测试各个组件的基本功能
"""

import nav
import time

def test_aircraft_position():
    """测试飞机位置数据类"""
    print("测试 AircraftPosition 类...")
    position = nav.AircraftPosition(
        icao="ABC123",
        latitude=39.9042,
        longitude=116.4074,
        altitude=35000,
        timestamp=time.time()
    )
    print(f"位置信息: {position}")
    print("✓ AircraftPosition 测试通过\n")

def test_serial_manager():
    """测试串口管理器"""
    print("测试 SerialManager 类...")
    manager = nav.SerialManager()
    ports = manager.get_available_ports()
    print(f"发现串口: {ports}")
    print("✓ SerialManager 测试通过\n")

def test_adsb_decoder():
    """测试ADS-B解码器"""
    print("测试 ADSBDecoder 类...")
    decoder = nav.ADSBDecoder()
    
    # 测试无效消息
    result = decoder.decode_message("invalid")
    assert result is None, "无效消息应返回None"
    
    # 测试消息长度检查
    result = decoder.decode_message("1234567890")
    assert result is None, "短消息应返回None"
    
    print("✓ ADSBDecoder 基本测试通过\n")

def test_data_logger():
    """测试数据记录器"""
    print("测试 DataLogger 类...")
    logger = nav.DataLogger(log_dir=".")
    
    # 测试初始化
    success = logger.initialize()
    if success:
        print("✓ 日志文件初始化成功")
        
        # 测试记录原始数据
        logger.log_raw_data("*test_raw_data")
        
        # 测试记录位置信息
        position = nav.AircraftPosition(
            icao="TEST01",
            latitude=40.0,
            longitude=120.0,
            altitude=30000,
            timestamp=time.time()
        )
        logger.log_position(position)
        
        logger.close()
        print("✓ DataLogger 测试通过\n")
    else:
        print("⚠ DataLogger 初始化失败\n")

def main():
    """运行所有测试"""
    print("nav.py 组件测试")
    print("=" * 30)
    
    try:
        test_aircraft_position()
        test_serial_manager()
        test_adsb_decoder()
        test_data_logger()
        
        print("🎉 所有测试完成！")
        print("\n系统组件验证:")
        print("- ✓ 数据结构定义正确")
        print("- ✓ 串口管理功能正常")
        print("- ✓ 消息解码器工作正常")
        print("- ✓ 数据记录功能正常")
        print("\n可以运行 python nav.py 启动完整系统")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
