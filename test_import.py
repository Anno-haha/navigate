#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("测试simple_visual.py的导入...")

try:
    print("1. 测试基础导入...")
    import os
    import sys
    import json
    import time
    import threading
    from datetime import datetime
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    import socketserver
    print("   基础模块导入成功")
    
    print("2. 测试自定义模块导入...")
    from coord_converter import CoordinateConverter
    print("   coord_converter导入成功")
    
    from safe_file_reader import SafeADSBDataReader
    print("   safe_file_reader导入成功")
    
    print("3. 测试模块初始化...")
    coordinate_converter = CoordinateConverter()
    print("   CoordinateConverter初始化成功")
    
    data_reader = SafeADSBDataReader()
    print("   SafeADSBDataReader初始化成功")
    
    print("4. 测试数据读取...")
    # 测试读取数据文件
    if os.path.exists('adsb_decoded.log'):
        with open('adsb_decoded.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   成功读取{len(lines)}行数据")
    else:
        print("   adsb_decoded.log文件不存在")
    
    print("\n所有测试通过！simple_visual.py的导入应该没有问题。")
    
except Exception as e:
    print(f"导入错误: {e}")
    import traceback
    traceback.print_exc()
