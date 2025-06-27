#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("开始测试...")

try:
    print("1. 导入模块...")
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
    
    # 导入自定义模块
    from coord_converter import CoordinateConverter
    from safe_file_reader import SafeADSBDataReader
    print("   自定义模块导入成功")
    
    print("2. 初始化...")
    aircraft_data = {}
    coordinate_converter = CoordinateConverter()
    data_reader = SafeADSBDataReader()
    print("   初始化成功")
    
    print("3. 测试数据读取...")
    if os.path.exists('adsb_decoded.log'):
        with open('adsb_decoded.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   读取到{len(lines)}行数据")
            
            # 解析最后几行
            current_time = datetime.now()
            count = 0
            for line in lines[-10:]:
                try:
                    parts = line.strip().split(',')
                    if len(parts) >= 5:
                        timestamp_str = parts[0]
                        icao = parts[1]
                        lat = float(parts[2])
                        lon = float(parts[3])
                        alt = int(parts[4])
                        
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        time_diff = (current_time - timestamp).total_seconds()
                        
                        aircraft_data[icao] = {
                            'timestamp': timestamp_str,
                            'lat': lat,
                            'lon': lon,
                            'alt': alt,
                            'time_diff': time_diff
                        }
                        count += 1
                except:
                    pass
            
            print(f"   成功解析{count}架飞机数据")
    else:
        print("   adsb_decoded.log文件不存在")
    
    print("4. 测试HTTP服务器...")
    
    class SimpleHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/api/test':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    'status': 'success',
                    'message': 'API测试成功',
                    'aircraft_count': len(aircraft_data),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html = '''
                <!DOCTYPE html>
                <html>
                <head><title>ADS-B测试</title></head>
                <body>
                    <h1>ADS-B系统测试</h1>
                    <p>服务器运行正常</p>
                    <p><a href="/api/test">测试API</a></p>
                </body>
                </html>
                '''
                self.wfile.write(html.encode('utf-8'))
    
    # 启动服务器
    port = 8001
    print(f"   启动HTTP服务器，端口: {port}")
    
    with socketserver.TCPServer(("127.0.0.1", port), SimpleHandler) as httpd:
        print(f"✅ 测试服务器启动成功！")
        print(f"   访问地址: http://127.0.0.1:{port}/")
        print(f"   API测试: http://127.0.0.1:{port}/api/test")
        print(f"   按 Ctrl+C 停止服务器")
        
        httpd.serve_forever()
        
except KeyboardInterrupt:
    print("\n服务器已停止")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
