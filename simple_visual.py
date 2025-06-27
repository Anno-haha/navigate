#!/usr/bin/env python3
"""
ADS-B 简化可视化系统
不依赖Django，使用内置HTTP服务器
基于nav.py的ADS-B数据，提供实时可视化
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver

# 导入自定义模块
from coord_converter import CoordinateConverter
from safe_file_reader import SafeADSBDataReader

# 全局变量
aircraft_data = {}
coordinate_converter = CoordinateConverter()
data_reader = SafeADSBDataReader()

class ADSBHTTPHandler(SimpleHTTPRequestHandler):
    """自定义HTTP处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)
        
        # API路由
        if path.startswith('/api/'):
            self.handle_api_request(path, query)
        elif path == '/':
            self.serve_index()
        elif path == '/radar/':
            self.serve_radar()
        else:
            # 静态文件
            super().do_GET()
    
    def handle_api_request(self, path, query):
        """处理API请求"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/api/aircraft/':
            # 获取飞机数据
            altitude_min = int(query.get('altitude_min', [0])[0])
            altitude_max = int(query.get('altitude_max', [50000])[0])
            
            filtered_data = {}
            for icao, data in aircraft_data.items():
                if altitude_min <= data['altitude'] <= altitude_max:
                    filtered_data[icao] = data
            
            response = {
                'status': 'success',
                'count': len(filtered_data),
                'aircraft': filtered_data,
                'timestamp': datetime.now().isoformat(),
            }
            
        elif path.startswith('/api/aircraft/') and len(path.split('/')) == 4:
            # 获取特定飞机详情
            icao = path.split('/')[3]
            if icao in aircraft_data:
                response = {
                    'status': 'success',
                    'aircraft': aircraft_data[icao],
                    'trajectory': [],  # 简化版本暂不支持轨迹
                }
            else:
                response = {'status': 'error', 'message': 'Aircraft not found'}

        elif path == '/api/debug/78127C':
            # 调试78127C飞机的数据
            aircraft_78127C = aircraft_data.get('78127C')
            if aircraft_78127C:
                # 计算所有飞机的nav_time_unix排序
                all_aircraft = list(aircraft_data.values())
                sorted_by_nav_time = sorted(all_aircraft,
                    key=lambda x: x.get('nav_time_unix', 0), reverse=True)

                # 找到78127C在排序中的位置
                aircraft_78127C_index = -1
                for i, aircraft in enumerate(sorted_by_nav_time):
                    if aircraft.get('icao') == '78127C':
                        aircraft_78127C_index = i
                        break

                response = {
                    'status': 'success',
                    'aircraft_78127C': aircraft_78127C,
                    'debug_info': {
                        'has_nav_time_unix': 'nav_time_unix' in aircraft_78127C,
                        'nav_time_unix_value': aircraft_78127C.get('nav_time_unix'),
                        'nav_timestamp_value': aircraft_78127C.get('nav_timestamp'),
                        'timestamp_value': aircraft_78127C.get('timestamp'),
                        'last_seen_value': aircraft_78127C.get('last_seen'),
                        'position_in_nav_time_sort': aircraft_78127C_index + 1,
                        'total_aircraft': len(all_aircraft),
                    },
                    'top_5_by_nav_time': [
                        {
                            'icao': aircraft.get('icao'),
                            'nav_time_unix': aircraft.get('nav_time_unix'),
                            'nav_timestamp': aircraft.get('nav_timestamp'),
                        }
                        for aircraft in sorted_by_nav_time[:5]
                    ]
                }
            else:
                response = {
                    'status': 'not_found',
                    'message': '78127C飞机数据未找到',
                    'available_aircraft': list(aircraft_data.keys())
                }

        elif path == '/api/statistics/':
            # 统计信息 - 包含数据新鲜度分析
            if aircraft_data:
                altitudes = [data['altitude'] for data in aircraft_data.values()]
                altitude_ranges = {
                    '低空 (0-10000ft)': len([a for a in altitudes if a < 10000]),
                    '中空 (10000-33000ft)': len([a for a in altitudes if 10000 <= a < 33000]),
                    '高空 (33000ft+)': len([a for a in altitudes if a >= 33000]),
                }

                # 数据新鲜度统计
                current_time = datetime.now()
                freshness_stats = {
                    '实时 (<30秒)': 0,
                    '最近 (30秒-5分钟)': 0,
                    '较旧 (5-60分钟)': 0,
                    '过期 (>60分钟)': 0
                }

                for data in aircraft_data.values():
                    # 使用nav.py的时间戳计算数据年龄
                    if 'nav_time_unix' in data and data['nav_time_unix']:
                        nav_time = datetime.fromtimestamp(data['nav_time_unix'])
                        age_seconds = (current_time - nav_time).total_seconds()
                    else:
                        last_seen = datetime.fromisoformat(data.get('last_seen', data['timestamp']))
                        age_seconds = (current_time - last_seen).total_seconds()

                    if age_seconds < 30:
                        freshness_stats['实时 (<30秒)'] += 1
                    elif age_seconds < 300:
                        freshness_stats['最近 (30秒-5分钟)'] += 1
                    elif age_seconds < 3600:
                        freshness_stats['较旧 (5-60分钟)'] += 1
                    else:
                        freshness_stats['过期 (>60分钟)'] += 1

                response = {
                    'status': 'success',
                    'statistics': {
                        'total_aircraft': len(aircraft_data),
                        'altitude_distribution': altitude_ranges,
                        'average_altitude': sum(altitudes) / len(altitudes),
                        'freshness_distribution': freshness_stats,
                    }
                }
            else:
                response = {
                    'status': 'success',
                    'statistics': {
                        'total_aircraft': 0,
                        'altitude_distribution': {},
                        'freshness_distribution': {},
                    }
                }
        else:
            response = {'status': 'error', 'message': 'API endpoint not found'}
        
        self.wfile.write(json.dumps(response).encode())
    
    def serve_index(self):
        """提供主页"""
        html = self.get_simple_html('3D地球视图', 'index')
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_radar(self):
        """提供雷达页面"""
        html = self.get_simple_html('2D雷达视图', 'radar')
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def get_simple_html(self, title, page_type):
        """生成简化的HTML页面"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - ADS-B可视化</title>
    <!-- Three.js 库 -->
    <script src="https://cdn.jsdelivr.net/npm/three@0.144.0/build/three.min.js"></script>
    <script>
        // 手动加载OrbitControls
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/three@0.144.0/examples/js/controls/OrbitControls.js';
        script.onload = function() {{
            console.log('OrbitControls加载完成');
        }};
        script.onerror = function() {{
            console.warn('OrbitControls加载失败');
        }};
        document.head.appendChild(script);
    </script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a2332 25%, #2d4a6b 50%, #3d5a80 75%, #4a6fa5 100%);
            color: #ffffff;
            min-height: 100vh;
            position: relative;
        }}

        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                radial-gradient(circle at 20% 80%, rgba(120, 119, 255, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120, 219, 255, 0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .nav {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .nav-btn {{
            color: #ffffff;
            text-decoration: none;
            margin: 0 12px;
            padding: 14px 28px;
            background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
            border-radius: 12px;
            border: 1px solid rgba(120, 219, 255, 0.3);
            cursor: pointer;
            font-family: inherit;
            font-size: inherit;
            font-weight: 500;
            letter-spacing: 0.5px;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(10px);
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}
        .nav-btn:hover {{
            background: linear-gradient(145deg, rgba(120, 219, 255, 0.15), rgba(255, 119, 198, 0.1));
            border-color: rgba(120, 219, 255, 0.6);
            transform: translateY(-3px);
            box-shadow:
                0 8px 30px rgba(120, 219, 255, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }}
        .nav-btn.active {{
            background: linear-gradient(145deg, #00d4ff, #0099cc);
            border-color: #00d4ff;
            box-shadow:
                0 6px 25px rgba(0, 212, 255, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            color: #ffffff;
        }}
        .content {{
            background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid rgba(120, 219, 255, 0.2);
            backdrop-filter: blur(15px);
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}
        .aircraft-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .aircraft-card {{
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
            border-radius: 12px;
            padding: 18px;
            border: 1px solid rgba(120, 219, 255, 0.25);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(12px);
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.08),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }}

        .aircraft-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(120, 219, 255, 0.4);
            box-shadow:
                0 8px 30px rgba(0, 0, 0, 0.12),
                0 0 20px rgba(120, 219, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.12);
        }}

        /* 数据新鲜度样式 - 高饱和度 */
        .aircraft-card.fresh-data {{
            border-left: 4px solid #00ff88;
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.08),
                0 0 15px rgba(0,255,136,0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }}

        .aircraft-card.recent-data {{
            border-left: 4px solid #ffdd00;
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.08),
                0 0 15px rgba(255,221,0,0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }}

        .aircraft-card.old-data {{
            border-left: 4px solid #ff6600;
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.08),
                0 0 15px rgba(255,102,0,0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }}

        .aircraft-card.very-old-data {{
            border-left: 4px solid #ff3366;
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.08),
                0 0 15px rgba(255,51,102,0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
            opacity: 0.8;
        }}

        .freshness-indicator {{
            font-size: 0.75em;
            padding: 4px 8px;
            border-radius: 10px;
            font-weight: 600;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .freshness-indicator.fresh-data {{
            background: linear-gradient(145deg, rgba(0,255,136,0.25), rgba(0,255,136,0.15));
            color: #00ff88;
            text-shadow: 0 0 8px rgba(0,255,136,0.5);
        }}

        .freshness-indicator.recent-data {{
            background: linear-gradient(145deg, rgba(255,221,0,0.25), rgba(255,221,0,0.15));
            color: #ffdd00;
            text-shadow: 0 0 8px rgba(255,221,0,0.5);
        }}

        .freshness-indicator.old-data {{
            background: linear-gradient(145deg, rgba(255,102,0,0.25), rgba(255,102,0,0.15));
            color: #ff6600;
            text-shadow: 0 0 8px rgba(255,102,0,0.5);
        }}

        .freshness-indicator.very-old-data {{
            background: linear-gradient(145deg, rgba(255,51,102,0.25), rgba(255,51,102,0.15));
            color: #ff3366;
            text-shadow: 0 0 8px rgba(255,51,102,0.5);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .status {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #28a745;
            margin-right: 8px;
        }}
        .refresh-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 5px;
        }}
        .refresh-btn:hover {{
            background: #0056b3;
        }}
        .view-container {{
            min-height: 400px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}

        .view-3d {{
            display: block;
        }}

        .view-radar {{
            display: none;
        }}

        /* 3D地球视图样式 - 高级感设计 */
        #earth-container {{
            position: relative;
            width: 100%;
            height: 500px;
            background: radial-gradient(circle, #001122 0%, #000814 50%, #000000 100%);
            border-radius: 16px;
            border: 2px solid #00d4ff;
            overflow: hidden;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.3),
                0 0 40px rgba(0, 212, 255, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }}

        #earth-canvas {{
            width: 100%;
            height: 100%;
            display: block;
        }}

        .earth-controls {{
            position: absolute;
            top: 15px;
            left: 15px;
            background: linear-gradient(145deg, rgba(0, 20, 40, 0.9), rgba(0, 10, 20, 0.95));
            border: 1px solid #00d4ff;
            border-radius: 12px;
            padding: 16px;
            z-index: 100;
            color: #00d4ff;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            backdrop-filter: blur(15px);
            box-shadow:
                0 8px 25px rgba(0, 0, 0, 0.3),
                0 0 20px rgba(0, 212, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}

        .earth-info {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: linear-gradient(145deg, rgba(0, 20, 40, 0.9), rgba(0, 10, 20, 0.95));
            border: 1px solid #00d4ff;
            border-radius: 12px;
            padding: 12px;
            z-index: 100;
            color: #00d4ff;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            backdrop-filter: blur(15px);
            box-shadow:
                0 8px 25px rgba(0, 0, 0, 0.3),
                0 0 20px rgba(0, 212, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}

        .earth-controls select, .earth-controls input {{
            background: linear-gradient(145deg, rgba(0, 30, 60, 0.8), rgba(0, 15, 30, 0.9));
            color: #00d4ff;
            border: 1px solid #00d4ff;
            border-radius: 6px;
            padding: 6px 8px;
            font-family: inherit;
            font-size: 11px;
            backdrop-filter: blur(8px);
            transition: all 0.3s ease;
        }}

        .earth-controls select:hover, .earth-controls input:hover {{
            border-color: #00ffaa;
            color: #00ffaa;
            box-shadow: 0 0 10px rgba(0, 255, 170, 0.3);
        }}

        .earth-controls select:focus, .earth-controls input:focus {{
            outline: none;
            border-color: #00ffaa;
            color: #00ffaa;
            box-shadow: 0 0 15px rgba(0, 255, 170, 0.4);
        }}

        /* 雷达视图样式 - 高级感设计 */
        #radar-container {{
            position: relative;
            width: 100%;
            height: 500px;
            background: radial-gradient(circle, #001a2e 0%, #000814 50%, #000000 100%);
            border-radius: 16px;
            border: 2px solid #00d4ff;
            overflow: hidden;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.3),
                0 0 40px rgba(0, 212, 255, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }}

        #radar-canvas {{
            width: 100%;
            height: 100%;
            cursor: crosshair;
        }}

        .radar-controls {{
            position: absolute;
            top: 15px;
            left: 15px;
            background: linear-gradient(145deg, rgba(0, 20, 40, 0.9), rgba(0, 10, 20, 0.95));
            border: 1px solid #00d4ff;
            border-radius: 12px;
            padding: 16px;
            z-index: 100;
            color: #00d4ff;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            backdrop-filter: blur(15px);
            box-shadow:
                0 8px 25px rgba(0, 0, 0, 0.3),
                0 0 20px rgba(0, 212, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}

        .radar-info {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 10px;
            z-index: 100;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            min-width: 150px;
        }}

        .radar-controls select, .radar-controls input {{
            background: linear-gradient(145deg, rgba(0, 30, 60, 0.8), rgba(0, 15, 30, 0.9));
            color: #00d4ff;
            border: 1px solid #00d4ff;
            border-radius: 6px;
            padding: 6px 8px;
            font-family: inherit;
            font-size: 11px;
            backdrop-filter: blur(8px);
            transition: all 0.3s ease;
        }}

        .radar-controls select:hover, .radar-controls input:hover {{
            border-color: #00ffaa;
            color: #00ffaa;
            box-shadow: 0 0 10px rgba(0, 255, 170, 0.3);
        }}

        .radar-controls select:focus, .radar-controls input:focus {{
            outline: none;
            border-color: #00ffaa;
            color: #00ffaa;
            box-shadow: 0 0 15px rgba(0, 255, 170, 0.4);
        }}

        .status-indicator {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }}

        .status-online {{ background: #00ff00; }}
        .status-offline {{ background: #ff0000; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✈️ ADS-B 可视化系统</h1>
            <p>实时飞机位置监控 - 参考点：北京上空 (39.9°N, 116.4°E, 10000m)</p>
        </div>
        
        <div class="nav">
            <button class="nav-btn active" onclick="showView('3d')" id="btn-3d">🌍 3D地球视图</button>
            <button class="nav-btn" onclick="showView('radar')" id="btn-radar">📡 2D雷达视图</button>
            <a href="/api/aircraft/" target="_blank" class="nav-btn">🔗 API接口</a>
        </div>
        
        <div class="content">
            <h2>{title}</h2>
            <div>
                <span class="status" id="status"></span>
                <span id="aircraft-count">0</span> 架飞机在线
                <span style="margin-left: 20px;">最后更新: <span id="last-update">--:--:--</span></span>
                <button class="refresh-btn" onclick="refreshData()">🔄 刷新数据</button>
                <button class="refresh-btn" onclick="toggleAutoRefresh()" id="auto-refresh-btn">⏸️ 停止自动刷新</button>
            </div>
        </div>
        
        <div class="content">
            <!-- 3D地球视图 -->
            <div id="view-3d" class="view-container view-3d">
                <h3>🌍 3D地球可视化</h3>
                <div id="earth-container">
                    <canvas id="earth-canvas"></canvas>

                    <!-- 3D控制面板 -->
                    <div class="earth-controls">
                        <div style="margin-bottom: 8px;">
                            <label>视角模式</label><br>
                            <select id="camera-mode" onchange="changeCameraMode()">
                                <option value="free">自由视角</option>
                                <option value="follow">跟随飞机</option>
                                <option value="overview">全局视图</option>
                            </select>
                        </div>

                        <div style="margin-bottom: 8px;">
                            <label>
                                <input type="checkbox" id="show-orbits" onchange="toggleOrbits()" checked>
                                显示轨迹
                            </label>
                        </div>

                        <div style="margin-bottom: 8px;">
                            <label>
                                <input type="checkbox" id="show-labels-3d" onchange="toggleLabels3D()" checked>
                                显示标签
                            </label>
                        </div>

                        <div style="margin-bottom: 8px;">
                            <label>
                                <input type="checkbox" id="auto-rotate" onchange="toggleAutoRotate()">
                                自动旋转
                            </label>
                        </div>
                    </div>

                    <!-- 3D信息面板 -->
                    <div class="earth-info">
                        <div style="margin-bottom: 5px;">
                            <span id="earth-status" class="status-indicator status-online"></span>
                            <span style="margin-left: 5px;">3D渲染</span>
                        </div>
                        <div style="font-size: 11px;">
                            <div id="earth-aircraft-count">0 架飞机</div>
                            <div id="earth-fps">FPS: 60</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 2D雷达视图 -->
            <div id="view-radar" class="view-container view-radar">
                <h3>📡 实时2D雷达监控</h3>
                <div id="radar-container">
                    <canvas id="radar-canvas"></canvas>

                    <!-- 雷达控制面板 -->
                    <div class="radar-controls">
                        <div style="margin-bottom: 8px;">
                            <label>雷达范围</label><br>
                            <select id="radar-range" onchange="changeRadarRange()">
                                <option value="20">20 km</option>
                                <option value="50">50 km</option>
                                <option value="100" selected>100 km</option>
                                <option value="200">200 km</option>
                            </select>
                            <div id="range-info" style="font-size: 9px; margin-top: 3px; color: #ffff00;">
                                中等范围：显示最近5分钟飞机标签
                            </div>
                        </div>

                        <div style="margin-bottom: 5px;">
                            <label>
                                <input type="checkbox" id="show-sweep" checked onchange="toggleSweep()">
                                雷达扫描
                            </label>
                        </div>

                        <div style="margin-bottom: 5px;">
                            <label>
                                <input type="checkbox" id="show-trails" checked onchange="toggleTrails()">
                                飞机轨迹
                            </label>
                        </div>

                        <div>
                            <label>
                                <input type="checkbox" id="show-labels" checked onchange="toggleLabels()">
                                飞机标签
                            </label>
                        </div>
                    </div>

                    <!-- 雷达信息面板 -->
                    <div class="radar-info">
                        <div>
                            <span class="status-indicator" id="radar-status"></span>
                            <span>雷达状态</span>
                        </div>
                        <div id="radar-aircraft-count">0 架飞机</div>
                        <div style="margin-top: 8px; font-size: 10px;">
                            <div>范围: <span id="current-range">100</span> km</div>
                            <div>更新: <span id="radar-update-rate">--</span> Hz</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="content">
            <h3>📊 统计信息</h3>
            <div class="stats" id="statistics">
                <!-- 动态加载统计信息 -->
            </div>
        </div>
        
        <div class="content">
            <h3>✈️ 飞机列表</h3>
            <div class="aircraft-list" id="aircraft-list">
                <div class="aircraft-card">
                    <p>正在加载飞机数据...</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let autoRefresh = true;
        let aircraftData = {{}};

        // 雷达相关变量
        let radarCanvas, radarCtx;
        let radarCenter = {{x: 0, y: 0}};
        let radarRange = 100; // km
        let sweepAngle = 0;
        let showSweep = true;
        let showTrails = false;
        let showLabels = true;
        let radarAnimationId;
        let radarAircraftData = {{}};

        // 3D地球相关变量
        let earthScene, earthCamera, earthRenderer, earthControls;
        let earthSphere, earthGroup;
        let aircraftMeshes = {{}};
        let aircraftTrails = {{}};
        let earthAnimationId;
        let cameraMode = 'free';
        let showOrbits = true;
        let showLabels3D = true;
        let autoRotate = false;
        let earthAircraftData = {{}};
        
        // 获取飞机数据
        async function fetchAircraftData() {{
            try {{
                const response = await fetch('/api/aircraft/');
                const data = await response.json();
                
                if (data.status === 'success') {{
                    aircraftData = data.aircraft;
                    updateDisplay(data);
                    document.getElementById('status').style.background = '#28a745';
                }} else {{
                    document.getElementById('status').style.background = '#dc3545';
                }}
            }} catch (error) {{
                console.error('获取数据失败:', error);
                document.getElementById('status').style.background = '#dc3545';
            }}
        }}
        
        // 更新显示
        function updateDisplay(data) {{
            document.getElementById('aircraft-count').textContent = data.count;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            updateAircraftList(data.aircraft);
            updateStatistics();
        }}
        
        // 更新飞机列表 - 按最新消息时间排序
        function updateAircraftList(aircraft) {{
            const listContainer = document.getElementById('aircraft-list');

            if (Object.keys(aircraft).length === 0) {{
                listContainer.innerHTML = '<div class="aircraft-card"><p>暂无飞机数据</p></div>';
                return;
            }}

            // 按nav.py输出的时间戳排序（最新的在前）
            const sortedAircraft = Object.values(aircraft).sort((a, b) => {{
                // 优先使用nav.py的时间戳，如果没有则使用系统时间戳
                const timeA = a.nav_time_unix ? new Date(a.nav_time_unix * 1000) : new Date(a.timestamp);
                const timeB = b.nav_time_unix ? new Date(b.nav_time_unix * 1000) : new Date(b.timestamp);

                // 调试特定飞机的排序（可选）
                // if (a.icao === '78127C' || b.icao === '78127C') {{
                //     console.log('[DEBUG] 排序比较:', a.icao, 'vs', b.icao);
                //     console.log('[DEBUG] 排序结果:', timeB - timeA);
                // }}

                return timeB - timeA; // 降序排列，nav.py最新输出的在前
            }});

            // 调试排序结果（可选）
            // const aircraft78127C = sortedAircraft.find(plane => plane.icao === '78127C');
            // if (aircraft78127C) {{
            //     const index = sortedAircraft.indexOf(aircraft78127C);
            //     console.log('[DEBUG] 78127C排序位置:', index + 1, '/', sortedAircraft.length);
            // }}

            let html = '';
            sortedAircraft.forEach(plane => {{
                const distance = Math.sqrt(plane.enu_e**2 + plane.enu_n**2) / 1000;
                const emoji = plane.altitude < 10000 ? '🛩️' : plane.altitude < 30000 ? '✈️' : '🛫';
                
                // 计算飞行时间
                const firstSeen = new Date(plane.first_seen || plane.timestamp);
                const lastSeen = new Date(plane.last_seen || plane.timestamp);
                const flightDuration = Math.round((lastSeen - firstSeen) / 1000 / 60); // 分钟

                // 计算数据新鲜度 - 基于nav.py的时间戳
                const now = new Date();
                const navTime = plane.nav_time_unix ? new Date(plane.nav_time_unix * 1000) : lastSeen;
                const dataAge = Math.round((now - navTime) / 1000); // 秒，基于nav.py输出时间
                const dataAgeMinutes = Math.round(dataAge / 60); // 分钟

                // 数据新鲜度指示
                let freshnessIndicator = '';
                let freshnessClass = '';
                if (dataAge < 30) {{
                    freshnessIndicator = '🟢 实时';
                    freshnessClass = 'fresh-data';
                }} else if (dataAge < 300) {{
                    freshnessIndicator = '🟡 ' + dataAge + '秒前';
                    freshnessClass = 'recent-data';
                }} else if (dataAgeMinutes < 60) {{
                    freshnessIndicator = '🟠 ' + dataAgeMinutes + '分钟前';
                    freshnessClass = 'old-data';
                }} else {{
                    freshnessIndicator = '🔴 ' + Math.round(dataAgeMinutes/60) + '小时前';
                    freshnessClass = 'very-old-data';
                }}

                // 计算高度变化
                const altChange = plane.max_altitude - plane.min_altitude;

                html += '<div class="aircraft-card ' + freshnessClass + '">' +
                    '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">' +
                        '<h4>' + emoji + ' ' + plane.icao + '</h4>' +
                        '<div style="display: flex; flex-direction: column; align-items: flex-end; font-size: 0.8em;">' +
                            '<span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px; margin-bottom: 3px;">' +
                                (plane.update_count || 1) + ' 次更新' +
                            '</span>' +
                            '<span class="freshness-indicator ' + freshnessClass + '">' +
                                freshnessIndicator +
                            '</span>' +
                        '</div>' +
                    '</div>' +

                    '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">' +
                        '<div>' +
                            '<p><strong>📍 当前位置:</strong><br>' +
                            plane.latitude.toFixed(4) + '°, ' + plane.longitude.toFixed(4) + '°</p>' +
                            '<p><strong>📏 距离:</strong> ' + distance.toFixed(1) + ' km</p>' +
                        '</div>' +
                        '<div>' +
                            '<p><strong>✈️ 当前高度:</strong><br>' +
                            plane.altitude + 'ft (' + Math.round(plane.altitude * 0.3048) + 'm)</p>' +
                            '<p><strong>⚡ 速度:</strong> ' + (plane.speed || 0) + ' km/h</p>' +
                        '</div>' +
                    '</div>' +

                    '<div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 5px; margin-bottom: 8px;">' +
                        '<p style="margin: 2px 0;"><strong>📊 高度统计:</strong></p>' +
                        '<p style="margin: 2px 0; font-size: 0.9em;">' +
                            '最高: ' + plane.max_altitude + 'ft | ' +
                            '最低: ' + plane.min_altitude + 'ft | ' +
                            '平均: ' + plane.avg_altitude + 'ft' +
                            (altChange > 1000 ? '<br><span style="color: #ffd700;">⚠️ 高度变化: ' + altChange + 'ft</span>' : '') +
                        '</p>' +
                    '</div>' +

                    '<div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 5px; margin-bottom: 8px;">' +
                        '<p style="margin: 2px 0;"><strong>🕒 时间信息:</strong></p>' +
                        '<p style="margin: 2px 0; font-size: 0.9em;">' +
                            '首次发现: ' + firstSeen.toLocaleTimeString() + '<br>' +
                            '最后更新: ' + lastSeen.toLocaleTimeString() +
                            (flightDuration > 0 ? '<br>跟踪时长: ' + flightDuration + ' 分钟' : '') +
                        '</p>' +
                    '</div>' +

                    '<details style="margin-top: 8px;">' +
                        '<summary style="cursor: pointer; color: #87ceeb;">🔍 详细坐标信息</summary>' +
                        '<div style="margin-top: 5px; font-size: 0.9em;">' +
                            '<p><strong>ENU坐标:</strong><br>' +
                            'E: ' + plane.enu_e.toFixed(0) + 'm | ' +
                            'N: ' + plane.enu_n.toFixed(0) + 'm | ' +
                            'U: ' + plane.enu_u.toFixed(0) + 'm</p>' +
                            (plane.positions && plane.positions.length > 1 ?
                                '<p><strong>位置历史:</strong> ' + plane.positions.length + ' 个记录点</p>' : '') +
                        '</div>' +
                    '</details>' +
                '</div>';
            }});
            
            listContainer.innerHTML = html;
        }}
        
        // 更新统计信息 - 包含数据新鲜度
        async function updateStatistics() {{
            try {{
                const response = await fetch('/api/statistics/');
                const data = await response.json();

                if (data.status === 'success') {{
                    const stats = data.statistics;
                    const statsContainer = document.getElementById('statistics');

                    statsContainer.innerHTML =
                        '<div class="stat-card">' +
                            '<h4>总飞机数</h4>' +
                            '<h2>' + (stats.total_aircraft || 0) + '</h2>' +
                        '</div>' +
                        '<div class="stat-card">' +
                            '<h4>平均高度</h4>' +
                            '<h2>' + Math.round(stats.average_altitude || 0) + 'ft</h2>' +
                        '</div>' +
                        '<div class="stat-card">' +
                            '<h4>高度分布</h4>' +
                            '<p>低空: ' + ((stats.altitude_distribution && stats.altitude_distribution['低空 (0-10000ft)']) || 0) + '</p>' +
                            '<p>中空: ' + ((stats.altitude_distribution && stats.altitude_distribution['中空 (10000-33000ft)']) || 0) + '</p>' +
                            '<p>高空: ' + ((stats.altitude_distribution && stats.altitude_distribution['高空 (33000ft+)']) || 0) + '</p>' +
                        '</div>' +
                        '<div class="stat-card">' +
                            '<h4>数据新鲜度</h4>' +
                            '<p style="color: #00ff88; text-shadow: 0 0 8px rgba(0,255,136,0.5);">🟢 实时: ' + ((stats.freshness_distribution && stats.freshness_distribution['实时 (<30秒)']) || 0) + '</p>' +
                            '<p style="color: #ffdd00; text-shadow: 0 0 8px rgba(255,221,0,0.5);">🟡 最近: ' + ((stats.freshness_distribution && stats.freshness_distribution['最近 (30秒-5分钟)']) || 0) + '</p>' +
                            '<p style="color: #ff6600; text-shadow: 0 0 8px rgba(255,102,0,0.5);">🟠 较旧: ' + ((stats.freshness_distribution && stats.freshness_distribution['较旧 (5-60分钟)']) || 0) + '</p>' +
                        '</div>';
                }}
            }} catch (error) {{
                console.error('获取统计信息失败:', error);
            }}
        }}
        
        // 刷新数据
        function refreshData() {{
            fetchAircraftData();
        }}
        
        // 切换自动刷新
        function toggleAutoRefresh() {{
            autoRefresh = !autoRefresh;
            const btn = document.getElementById('auto-refresh-btn');
            btn.textContent = autoRefresh ? '⏸️ 停止自动刷新' : '▶️ 开始自动刷新';
        }}

        // 3D地球初始化和渲染函数
        function initEarth() {{
            console.log('开始初始化3D地球...');

            // 检查Three.js是否加载
            if (typeof THREE === 'undefined') {{
                console.error('Three.js库未加载');
                document.getElementById('earth-status').className = 'status-indicator status-offline';

                // 显示备用信息
                const canvas = document.getElementById('earth-canvas');
                if (canvas) {{
                    const ctx = canvas.getContext('2d');
                    canvas.width = canvas.offsetWidth;
                    canvas.height = canvas.offsetHeight;

                    ctx.fillStyle = '#001122';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    ctx.fillStyle = '#00d4ff';
                    ctx.font = '20px Arial';
                    ctx.textAlign = 'center';
                    ctx.fillText('Three.js库加载失败', canvas.width/2, canvas.height/2 - 20);
                    ctx.fillText('请检查网络连接', canvas.width/2, canvas.height/2 + 20);
                }}
                return;
            }}

            if (!earthScene) {{
                const container = document.getElementById('earth-container');
                const canvas = document.getElementById('earth-canvas');

                if (!container || !canvas) {{
                    console.error('找不到3D容器或画布元素');
                    return;
                }}

                // 创建场景
                earthScene = new THREE.Scene();

                // 创建相机
                earthCamera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 10000);
                earthCamera.position.set(0, 0, 3);

                // 创建渲染器
                earthRenderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true, alpha: true }});
                earthRenderer.setSize(container.clientWidth, container.clientHeight);
                earthRenderer.setClearColor(0x000000, 0);

                // 创建地球组
                earthGroup = new THREE.Group();
                earthScene.add(earthGroup);

                // 创建地球几何体
                const earthGeometry = new THREE.SphereGeometry(1, 64, 32);

                // 创建地球材质（简化版，使用纯色）
                const earthMaterial = new THREE.MeshPhongMaterial({{
                    color: 0x2233ff,
                    transparent: true,
                    opacity: 0.8,
                    wireframe: false
                }});

                earthSphere = new THREE.Mesh(earthGeometry, earthMaterial);
                earthGroup.add(earthSphere);

                // 添加地球网格线
                const wireframeGeometry = new THREE.SphereGeometry(1.01, 32, 16);
                const wireframeMaterial = new THREE.MeshBasicMaterial({{
                    color: 0x00d4ff,
                    wireframe: true,
                    transparent: true,
                    opacity: 0.3
                }});
                const wireframeSphere = new THREE.Mesh(wireframeGeometry, wireframeMaterial);
                earthGroup.add(wireframeSphere);

                // 添加光源
                const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
                earthScene.add(ambientLight);

                const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                directionalLight.position.set(1, 1, 1);
                earthScene.add(directionalLight);

                // 创建控制器
                if (typeof THREE.OrbitControls !== 'undefined') {{
                    earthControls = new THREE.OrbitControls(earthCamera, earthRenderer.domElement);
                    earthControls.enableDamping = true;
                    earthControls.dampingFactor = 0.05;
                    earthControls.enableZoom = true;
                    earthControls.autoRotate = false;
                    console.log('OrbitControls初始化成功');
                }} else {{
                    console.warn('OrbitControls未加载，使用基础鼠标控制');
                    // 添加基础鼠标控制
                    let mouseDown = false;
                    let mouseX = 0, mouseY = 0;

                    canvas.addEventListener('mousedown', (e) => {{
                        mouseDown = true;
                        mouseX = e.clientX;
                        mouseY = e.clientY;
                    }});

                    canvas.addEventListener('mouseup', () => {{
                        mouseDown = false;
                    }});

                    canvas.addEventListener('mousemove', (e) => {{
                        if (mouseDown) {{
                            const deltaX = e.clientX - mouseX;
                            const deltaY = e.clientY - mouseY;

                            earthGroup.rotation.y += deltaX * 0.01;
                            earthGroup.rotation.x += deltaY * 0.01;

                            mouseX = e.clientX;
                            mouseY = e.clientY;
                        }}
                    }});

                    canvas.addEventListener('wheel', (e) => {{
                        e.preventDefault();
                        const scale = e.deltaY > 0 ? 1.1 : 0.9;
                        earthCamera.position.multiplyScalar(scale);
                    }});
                }}

                // 窗口大小调整
                window.addEventListener('resize', resizeEarth);

                // 开始渲染循环
                startEarthAnimation();

                console.log('3D地球初始化完成');
                document.getElementById('earth-status').className = 'status-indicator status-online';
            }}
        }}

        function resizeEarth() {{
            const container = document.getElementById('earth-container');
            if (earthCamera && earthRenderer) {{
                earthCamera.aspect = container.clientWidth / container.clientHeight;
                earthCamera.updateProjectionMatrix();
                earthRenderer.setSize(container.clientWidth, container.clientHeight);
            }}
        }}

        function startEarthAnimation() {{
            function animate() {{
                try {{
                    if (earthControls) {{
                        earthControls.update();
                    }}

                    if (autoRotate && earthGroup) {{
                        earthGroup.rotation.y += 0.005;
                    }}

                    renderEarth();
                    earthAnimationId = requestAnimationFrame(animate);
                }} catch (error) {{
                    console.error('3D动画错误:', error);
                    document.getElementById('earth-status').className = 'status-indicator status-offline';
                }}
            }}
            animate();
        }}

        function renderEarth() {{
            try {{
                if (earthRenderer && earthScene && earthCamera) {{
                    earthRenderer.render(earthScene, earthCamera);

                    // 更新FPS显示
                    const fpsElement = document.getElementById('earth-fps');
                    if (fpsElement) {{
                        fpsElement.textContent = 'FPS: 60';
                    }}
                }} else {{
                    console.warn('3D渲染器、场景或相机未初始化');
                }}
            }} catch (error) {{
                console.error('3D渲染错误:', error);
            }}
        }}

        // 视图切换功能
        function showView(viewType) {{
            // 隐藏所有视图
            document.getElementById('view-3d').style.display = 'none';
            document.getElementById('view-radar').style.display = 'none';

            // 移除所有按钮的active类
            document.querySelectorAll('.nav-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});

            // 显示选中的视图
            if (viewType === '3d') {{
                document.getElementById('view-3d').style.display = 'block';
                document.getElementById('btn-3d').classList.add('active');
                initEarth();
            }} else if (viewType === 'radar') {{
                document.getElementById('view-radar').style.display = 'block';
                document.getElementById('btn-radar').classList.add('active');
                initRadar();
            }}
        }}

        // 雷达相关变量
        let radarCanvas, radarCtx;
        let radarRange = 100;
        let radarCenter = {{ x: 0, y: 0 }};
        let sweepAngle = 0;
        let radarAircraftData = {{}};
        let showSweep = true;
        let showTrails = true;
        let showLabels = true;
        let radarAnimationId;
        
        // 初始化雷达
        function initRadar() {{
            if (!radarCanvas) {{
                radarCanvas = document.getElementById('radar-canvas');
                radarCtx = radarCanvas.getContext('2d');

                // 设置画布大小
                resizeRadarCanvas();
                window.addEventListener('resize', resizeRadarCanvas);

                // 开始雷达动画
                startRadarAnimation();
            }}
        }}

        function resizeRadarCanvas() {{
            const container = document.getElementById('radar-container');
            radarCanvas.width = container.clientWidth;
            radarCanvas.height = container.clientHeight;
            radarCenter.x = radarCanvas.width / 2;
            radarCenter.y = radarCanvas.height / 2;
        }}

        function startRadarAnimation() {{
            function animate() {{
                if (showSweep) {{
                    sweepAngle = (sweepAngle + 2) % 360;
                }}
                drawRadar();
                radarAnimationId = requestAnimationFrame(animate);
            }}
            animate();
        }}

        function drawRadar() {{
            // 清空画布
            radarCtx.fillStyle = '#000011';
            radarCtx.fillRect(0, 0, radarCanvas.width, radarCanvas.height);

            // 绘制雷达网格
            drawRadarGrid();

            // 绘制扫描线
            if (showSweep) {{
                drawSweepLine();
            }}

            // 绘制飞机
            drawRadarAircraft();
        }}

        function drawRadarGrid() {{
            radarCtx.strokeStyle = '#00d4ff40';  // 高饱和度青色
            radarCtx.lineWidth = 1;

            const maxRadius = Math.min(radarCanvas.width, radarCanvas.height) * 0.4;
            const step = maxRadius / 4;

            // 绘制同心圆
            for (let i = 1; i <= 4; i++) {{
                const radius = step * i;
                radarCtx.beginPath();
                radarCtx.arc(radarCenter.x, radarCenter.y, radius, 0, Math.PI * 2);
                radarCtx.stroke();

                // 距离标签
                radarCtx.fillStyle = '#00d4ff80';  // 高饱和度青色
                radarCtx.font = '12px Courier New';
                const distance = Math.round(radarRange * i / 4);
                radarCtx.fillText(distance + 'km', radarCenter.x + radius - 20, radarCenter.y - 5);
            }}

            // 绘制方位线
            radarCtx.strokeStyle = '#00d4ff25';  // 高饱和度青色
            for (let angle = 0; angle < 360; angle += 30) {{
                const radian = angle * Math.PI / 180;
                const x2 = radarCenter.x + Math.cos(radian - Math.PI/2) * maxRadius;
                const y2 = radarCenter.y + Math.sin(radian - Math.PI/2) * maxRadius;

                radarCtx.beginPath();
                radarCtx.moveTo(radarCenter.x, radarCenter.y);
                radarCtx.lineTo(x2, y2);
                radarCtx.stroke();
            }}

            // 中心点
            radarCtx.fillStyle = '#ff3366';  // 高饱和度红色
            radarCtx.beginPath();
            radarCtx.arc(radarCenter.x, radarCenter.y, 3, 0, Math.PI * 2);
            radarCtx.fill();
        }}

        function drawSweepLine() {{
            const maxRadius = Math.min(radarCanvas.width, radarCanvas.height) * 0.4;
            const radian = (sweepAngle - 90) * Math.PI / 180;
            const x2 = radarCenter.x + Math.cos(radian) * maxRadius;
            const y2 = radarCenter.y + Math.sin(radian) * maxRadius;

            radarCtx.strokeStyle = '#00d4ff90';  // 高饱和度青色扫描线
            radarCtx.lineWidth = 2;
            radarCtx.beginPath();
            radarCtx.moveTo(radarCenter.x, radarCenter.y);
            radarCtx.lineTo(x2, y2);
            radarCtx.stroke();
        }}

        function drawRadarAircraft() {{
            // 过滤并排序飞机数据 - 优先显示最新消息
            const now = new Date();
            const validAircraft = Object.values(radarAircraftData).filter(aircraft => {{
                // 使用nav.py的时间戳判断数据年龄
                const navTime = aircraft.nav_time_unix ? new Date(aircraft.nav_time_unix * 1000) : new Date(aircraft.timestamp);
                const dataAge = (now - navTime) / 1000; // 秒
                return dataAge < 3600; // 60分钟内的数据
            }}).sort((a, b) => {{
                // 按nav.py输出时间排序
                const timeA = a.nav_time_unix ? new Date(a.nav_time_unix * 1000) : new Date(a.timestamp);
                const timeB = b.nav_time_unix ? new Date(b.nav_time_unix * 1000) : new Date(b.timestamp);
                return timeB - timeA; // nav.py最新输出的优先绘制
            }});

            validAircraft.forEach(aircraft => {{
                const distance = Math.sqrt(aircraft.enu_e**2 + aircraft.enu_n**2) / 1000;
                if (distance > radarRange) return;

                const maxRadius = Math.min(radarCanvas.width, radarCanvas.height) * 0.4;
                const scale = maxRadius / radarRange;

                const x = radarCenter.x + (aircraft.enu_e / 1000) * scale;
                const y = radarCenter.y - (aircraft.enu_n / 1000) * scale;

                // 计算数据新鲜度 - 基于nav.py的时间戳
                const navTime = aircraft.nav_time_unix ? new Date(aircraft.nav_time_unix * 1000) : new Date(aircraft.timestamp);
                const dataAge = (now - navTime) / 1000; // 秒，基于nav.py输出时间

                // 根据数据新鲜度调整显示
                let alpha = 1.0;
                let pulseIntensity = 1.0;
                if (dataAge > 1800) {{ // 30分钟以上
                    alpha = 0.6;
                    pulseIntensity = 0.5;
                }} else if (dataAge > 300) {{ // 5分钟以上
                    alpha = 0.8;
                    pulseIntensity = 0.7;
                }}

                // 绘制飞机点
                radarCtx.globalAlpha = alpha;
                radarCtx.fillStyle = getAircraftRadarColor(aircraft.altitude);
                radarCtx.beginPath();
                radarCtx.arc(x, y, 4, 0, Math.PI * 2);
                radarCtx.fill();

                // 绘制脉冲效果（最新数据更明显）
                if (dataAge < 30) {{ // 30秒内的数据有脉冲效果
                    const pulseRadius = 4 + Math.sin(Date.now() / 200) * 3 * pulseIntensity;
                    radarCtx.strokeStyle = getAircraftRadarColor(aircraft.altitude) + '40';
                    radarCtx.lineWidth = 2;
                    radarCtx.beginPath();
                    radarCtx.arc(x, y, pulseRadius, 0, Math.PI * 2);
                    radarCtx.stroke();
                }}

                // 智能标签显示 - 根据雷达范围和飞机密度调整
                if (showLabels) {{
                    let shouldShowLabel = true;
                    let fontSize = 10;
                    let labelOffset = 6;

                    // 根据雷达范围调整标签显示策略
                    if (radarRange >= 200) {{
                        // 200km范围：只显示距离中心50km内或最新30秒内的飞机标签
                        const centerDistance = Math.sqrt(aircraft.enu_e**2 + aircraft.enu_n**2) / 1000;
                        shouldShowLabel = (centerDistance < 50) || (dataAge < 30);
                        fontSize = 8;
                        labelOffset = 4;
                    }} else if (radarRange >= 100) {{
                        // 100km范围：只显示最新5分钟内的飞机标签
                        shouldShowLabel = dataAge < 300;
                        fontSize = 9;
                        labelOffset = 5;
                    }}

                    // 检查标签重叠（简化版本）
                    if (shouldShowLabel && radarRange >= 200) {{
                        // 在200km范围内，检查是否与其他飞机标签过于接近
                        const minDistance = 15; // 最小标签间距
                        for (let other of validAircraft) {{
                            if (other.icao === aircraft.icao) continue;

                            const otherDistance = Math.sqrt(other.enu_e**2 + other.enu_n**2) / 1000;
                            if (otherDistance > radarRange) continue;

                            const otherX = radarCenter.x + (other.enu_e / 1000) * scale;
                            const otherY = radarCenter.y - (other.enu_n / 1000) * scale;

                            const labelDistance = Math.sqrt((x - otherX)**2 + (y - otherY)**2);
                            if (labelDistance < minDistance) {{
                                // 如果距离太近，只显示数据更新的那个
                                const otherNavTime = other.nav_time_unix ? new Date(other.nav_time_unix * 1000) : new Date(other.timestamp);
                                const thisNavTime = aircraft.nav_time_unix ? new Date(aircraft.nav_time_unix * 1000) : new Date(aircraft.timestamp);
                                shouldShowLabel = thisNavTime > otherNavTime;
                                break;
                            }}
                        }}
                    }}

                    if (shouldShowLabel) {{
                        radarCtx.fillStyle = dataAge < 60 ? '#ffffff' : '#cccccc';
                        radarCtx.font = fontSize + 'px Courier New';
                        radarCtx.fillText(aircraft.icao, x + labelOffset, y - labelOffset);

                        // 显示数据年龄（如果超过5分钟且空间允许）
                        if (dataAge > 300 && radarRange < 200) {{
                            radarCtx.fillStyle = '#ffaa00';
                            radarCtx.font = (fontSize - 2) + 'px Courier New';
                            const ageText = dataAge < 3600 ? Math.round(dataAge/60) + 'm' : Math.round(dataAge/3600) + 'h';
                            radarCtx.fillText(ageText, x + labelOffset, y + labelOffset + 6);
                        }}
                    }}
                }}

                radarCtx.globalAlpha = 1.0; // 重置透明度
            }});
        }}

        function getAircraftRadarColor(altitude) {{
            if (altitude < 10000) return '#ff3366';  // 高饱和度红色
            if (altitude < 33000) return '#ffdd00';  // 高饱和度黄色
            return '#3366ff';  // 高饱和度蓝色
        }}

        function updateRadarData() {{
            radarAircraftData = aircraftData;

            // 更新雷达信息
            const count = Object.keys(radarAircraftData).length;
            document.getElementById('radar-aircraft-count').textContent = count + ' 架飞机';
            document.getElementById('radar-status').className = 'status-indicator status-online';
        }}

        function changeRadarRange() {{
            radarRange = parseInt(document.getElementById('radar-range').value);
            document.getElementById('current-range').textContent = radarRange;

            // 根据雷达范围显示标签密度提示
            const rangeInfo = document.getElementById('range-info');
            if (rangeInfo) {{
                if (radarRange >= 200) {{
                    rangeInfo.textContent = '大范围模式：仅显示核心区域和最新飞机标签';
                    rangeInfo.style.color = '#ff6600';
                    rangeInfo.style.textShadow = '0 0 8px rgba(255,102,0,0.5)';
                }} else if (radarRange >= 100) {{
                    rangeInfo.textContent = '中等范围：显示最近5分钟飞机标签';
                    rangeInfo.style.color = '#ffdd00';
                    rangeInfo.style.textShadow = '0 0 8px rgba(255,221,0,0.5)';
                }} else {{
                    rangeInfo.textContent = '近距离模式：显示所有飞机标签';
                    rangeInfo.style.color = '#00ff88';
                    rangeInfo.style.textShadow = '0 0 8px rgba(0,255,136,0.5)';
                }}
            }}
        }}

        function toggleSweep() {{
            showSweep = document.getElementById('show-sweep').checked;
        }}

        function toggleTrails() {{
            showTrails = document.getElementById('show-trails').checked;
        }}

        function toggleLabels() {{
            showLabels = document.getElementById('show-labels').checked;
        }}

        // 3D地球控制函数
        function changeCameraMode() {{
            cameraMode = document.getElementById('camera-mode').value;

            if (cameraMode === 'overview' && earthCamera) {{
                earthCamera.position.set(0, 0, 5);
                if (earthControls) {{
                    earthControls.reset();
                }}
            }}
        }}

        function toggleOrbits() {{
            showOrbits = document.getElementById('show-orbits').checked;
            // 更新轨迹显示
            Object.values(aircraftTrails).forEach(trail => {{
                if (trail) {{
                    trail.visible = showOrbits;
                }}
            }});
        }}

        function toggleLabels3D() {{
            showLabels3D = document.getElementById('show-labels-3d').checked;
            // 更新3D标签显示
        }}

        function toggleAutoRotate() {{
            autoRotate = document.getElementById('auto-rotate').checked;
            if (earthControls) {{
                earthControls.autoRotate = autoRotate;
            }}
        }}

        function updateEarthData() {{
            earthAircraftData = aircraftData;

            // 更新3D飞机显示
            updateAircraftMeshes();

            // 更新信息面板
            const count = Object.keys(earthAircraftData).length;
            document.getElementById('earth-aircraft-count').textContent = count + ' 架飞机';
            document.getElementById('earth-status').className = 'status-indicator status-online';
        }}

        function updateAircraftMeshes() {{
            // 清理不存在的飞机
            Object.keys(aircraftMeshes).forEach(icao => {{
                if (!earthAircraftData[icao]) {{
                    if (aircraftMeshes[icao]) {{
                        earthGroup.remove(aircraftMeshes[icao]);
                        delete aircraftMeshes[icao];
                    }}
                    if (aircraftTrails[icao]) {{
                        earthGroup.remove(aircraftTrails[icao]);
                        delete aircraftTrails[icao];
                    }}
                }}
            }});

            // 更新或创建飞机网格
            Object.values(earthAircraftData).forEach(aircraft => {{
                const icao = aircraft.icao;

                // 将ENU坐标转换为3D世界坐标
                const scale = 0.001; // 缩放因子
                const x = aircraft.enu_e * scale;
                const y = aircraft.enu_u * scale;
                const z = -aircraft.enu_n * scale; // Z轴反向

                if (!aircraftMeshes[icao]) {{
                    // 创建新的飞机网格
                    const geometry = new THREE.SphereGeometry(0.02, 8, 6);
                    const material = new THREE.MeshBasicMaterial({{
                        color: getAircraft3DColor(aircraft.altitude)
                    }});
                    const mesh = new THREE.Mesh(geometry, material);
                    aircraftMeshes[icao] = mesh;
                    earthGroup.add(mesh);

                    // 创建轨迹
                    if (showOrbits) {{
                        const trailGeometry = new THREE.BufferGeometry();
                        const trailMaterial = new THREE.LineBasicMaterial({{
                            color: getAircraft3DColor(aircraft.altitude),
                            transparent: true,
                            opacity: 0.6
                        }});
                        const trail = new THREE.Line(trailGeometry, trailMaterial);
                        aircraftTrails[icao] = trail;
                        earthGroup.add(trail);
                    }}
                }}

                // 更新位置
                if (aircraftMeshes[icao]) {{
                    aircraftMeshes[icao].position.set(x, y, z);
                }}
            }});
        }}

        function getAircraft3DColor(altitude) {{
            if (altitude < 10000) return 0xff3366;  // 高饱和度红色
            if (altitude < 33000) return 0xffdd00;  // 高饱和度黄色
            return 0x3366ff;  // 高饱和度蓝色
        }}

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {{
            fetchAircraftData();

            // 延迟初始化3D地球视图，确保Three.js库完全加载
            setTimeout(() => {{
                initEarth();
            }}, 1000);

            // 自动刷新
            setInterval(() => {{
                if (autoRefresh) {{
                    fetchAircraftData();
                    if (document.getElementById('view-radar').style.display !== 'none') {{
                        updateRadarData();
                    }}
                    if (document.getElementById('view-3d').style.display !== 'none') {{
                        updateEarthData();
                    }}
                }}
            }}, 2000);
        }});
    </script>
</body>
</html>
        """


class ADSBVisualizationSystem:
    """简化的ADS-B可视化系统"""
    
    def __init__(self):
        self.running = False
        self.data_thread = None
        
    def start_data_processing(self):
        """启动数据处理线程"""
        self.running = True
        self.data_thread = threading.Thread(target=self._data_loop, daemon=True)
        self.data_thread.start()
        
    def _data_loop(self):
        """数据处理循环"""
        global aircraft_data
        
        while self.running:
            try:
                # 获取最新数据
                latest_data = data_reader.get_latest_data()

                if latest_data:
                    for icao, aircraft in latest_data.items():
                        # 数据已经包含ENU坐标，直接使用
                        enu_coords = (aircraft['enu_e'], aircraft['enu_n'], aircraft['enu_u'])
                        
                        # 更新数据 - 整合同一架飞机的历史信息
                        current_time = datetime.now()

                        # 如果是新飞机，初始化数据结构
                        if icao not in aircraft_data:
                            aircraft_data[icao] = {
                                'icao': icao,
                                'latitude': aircraft['latitude'],
                                'longitude': aircraft['longitude'],
                                'altitude': aircraft['altitude'],
                                'enu_e': enu_coords[0],
                                'enu_n': enu_coords[1],
                                'enu_u': enu_coords[2],
                                'timestamp': current_time.isoformat(),
                                'first_seen': current_time.isoformat(),
                                'last_seen': current_time.isoformat(),
                                'update_count': 1,
                                'positions': [enu_coords],  # 位置历史
                                'altitudes': [aircraft['altitude']],  # 高度历史
                                'max_altitude': aircraft['altitude'],
                                'min_altitude': aircraft['altitude'],
                                'avg_altitude': aircraft['altitude'],
                                'speed': 0,  # 初始速度为0
                                'speed_history': [],  # 速度历史用于平滑
                                # 传递nav.py的时间戳字段
                                'nav_timestamp': aircraft.get('nav_timestamp'),
                                'nav_time_unix': aircraft.get('nav_time_unix'),
                            }
                        else:
                            # 更新现有飞机数据
                            prev_data = aircraft_data[icao]

                            # 计算速度（基于nav.py时间戳的精确计算）
                            # 优先使用nav.py的时间戳，如果没有则使用系统时间戳
                            if 'nav_time_unix' in prev_data and prev_data['nav_time_unix'] and aircraft.get('nav_time_unix'):
                                # 使用nav.py的精确时间戳
                                time_diff = aircraft['nav_time_unix'] - prev_data['nav_time_unix']
                            else:
                                # 降级到系统时间戳
                                prev_time = datetime.fromisoformat(prev_data['timestamp'])
                                time_diff = (current_time - prev_time).total_seconds()

                            if time_diff > 0 and time_diff < 300:  # 只计算5分钟内的速度变化
                                # 计算地面距离变化（忽略垂直分量，更符合航空惯例）
                                prev_enu = (prev_data['enu_e'], prev_data['enu_n'], prev_data['enu_u'])
                                ground_distance = ((enu_coords[0] - prev_enu[0])**2 +
                                                 (enu_coords[1] - prev_enu[1])**2)**0.5

                                # 计算瞬时地面速度
                                instant_speed_ms = ground_distance / time_diff if time_diff > 0 else 0
                                instant_speed_kmh = instant_speed_ms * 3.6

                                # 速度合理性检查
                                if instant_speed_kmh > 1200:  # 超音速限制
                                    instant_speed_kmh = prev_data.get('speed', 0)
                                elif instant_speed_kmh < 10 and ground_distance < 50:  # 静止或微小移动
                                    instant_speed_kmh = 0

                                # 速度平滑处理
                                speed_history = prev_data.get('speed_history', [])
                                speed_history.append(instant_speed_kmh)

                                # 保留最近5个速度值用于平滑
                                if len(speed_history) > 5:
                                    speed_history = speed_history[-5:]

                                # 计算平滑速度（去除异常值后的平均值）
                                if len(speed_history) >= 3:
                                    # 去除最高和最低值，计算平均值
                                    sorted_speeds = sorted(speed_history)
                                    if len(sorted_speeds) >= 3:
                                        trimmed_speeds = sorted_speeds[1:-1]  # 去除最高和最低
                                        speed_kmh = sum(trimmed_speeds) / len(trimmed_speeds)
                                    else:
                                        speed_kmh = sum(speed_history) / len(speed_history)
                                else:
                                    speed_kmh = instant_speed_kmh

                                # 更新速度历史
                                prev_data['speed_history'] = speed_history

                            else:
                                # 时间差异常或过长，逐渐降低速度
                                speed_kmh = prev_data.get('speed', 0) * 0.95

                            # 更新位置历史（保留最近20个位置）
                            positions = prev_data.get('positions', [])
                            positions.append(enu_coords)
                            if len(positions) > 20:
                                positions = positions[-20:]

                            # 更新高度历史
                            altitudes = prev_data.get('altitudes', [])
                            altitudes.append(aircraft['altitude'])
                            if len(altitudes) > 20:
                                altitudes = altitudes[-20:]

                            # 计算统计信息
                            max_alt = max(altitudes)
                            min_alt = min(altitudes)
                            avg_alt = sum(altitudes) / len(altitudes)

                            aircraft_data[icao].update({
                                'latitude': aircraft['latitude'],
                                'longitude': aircraft['longitude'],
                                'altitude': aircraft['altitude'],
                                'enu_e': enu_coords[0],
                                'enu_n': enu_coords[1],
                                'enu_u': enu_coords[2],
                                'timestamp': current_time.isoformat(),
                                'last_seen': current_time.isoformat(),
                                'update_count': prev_data.get('update_count', 0) + 1,
                                'speed': round(speed_kmh, 1),
                                'speed_history': prev_data.get('speed_history', []),  # 保持速度历史
                                'positions': positions,
                                'altitudes': altitudes,
                                'max_altitude': max_alt,
                                'min_altitude': min_alt,
                                'avg_altitude': round(avg_alt, 0),
                                # 更新nav.py的时间戳字段
                                'nav_timestamp': aircraft.get('nav_timestamp'),
                                'nav_time_unix': aircraft.get('nav_time_unix'),
                            })
                
                # 清理过期数据（60分钟过期机制） - 基于nav.py时间戳
                current_time = datetime.now()
                expired_icaos = []
                for icao, data in aircraft_data.items():
                    # 优先使用nav.py的时间戳
                    if 'nav_time_unix' in data and data['nav_time_unix']:
                        nav_time = datetime.fromtimestamp(data['nav_time_unix'])
                        time_diff = (current_time - nav_time).total_seconds()
                    else:
                        last_seen = datetime.fromisoformat(data.get('last_seen', data['timestamp']))
                        time_diff = (current_time - last_seen).total_seconds()

                    if time_diff > 86400:  # 24小时过期（临时设置以显示历史数据）
                        expired_icaos.append(icao)
                        # 静默清理过期数据，不输出到终端

                for icao in expired_icaos:
                    del aircraft_data[icao]
                
                time.sleep(2)  # 增加间隔，减少文件访问频率
                
            except Exception as e:
                print(f"数据处理错误: {e}")
                time.sleep(5)


def check_nav_py_status():
    """检查nav.py运行状态"""
    try:
        # 检查日志文件是否存在且最近有更新
        if os.path.exists('adsb_decoded.log'):
            mtime = os.path.getmtime('adsb_decoded.log')
            current_time = time.time()

            if current_time - mtime < 120:  # 2分钟内有更新
                print("[OK] 检测到nav.py正在运行，数据采集正常")
                return True
            else:
                print("[WARN] nav.py可能未运行或无数据输出")
                print(f"   日志文件最后更新: {time.ctime(mtime)}")
                return False
        else:
            print("[WARN] 未找到adsb_decoded.log文件")
            print("   请确保nav.py正在运行并生成数据")
            return False
    except Exception as e:
        print(f"[ERROR] 检查nav.py状态失败: {e}")
        return False

def main():
    """主函数"""
    print("ADS-B 简化可视化系统")
    print("=" * 40)
    print("功能：实时飞机位置可视化")
    print("参考点：北京上空 (39.9°N, 116.4°E, 10000m)")
    print("=" * 40)

    # 检查nav.py状态
    nav_status = check_nav_py_status()
    if not nav_status:
        print("\n建议:")
        print("1. 在另一个终端窗口运行: python nav.py")
        print("2. 确保ADS-B接收器正常工作")
        print("3. 等待数据采集稳定后再启动可视化系统")
        print("\n自动继续启动可视化系统...")
        # 自动继续，不等待用户输入

    print("\n💡 提示: 可视化系统将与nav.py并行运行，不会影响数据采集")
    
    # 启动数据处理
    system = ADSBVisualizationSystem()
    system.start_data_processing()
    
    # 启动HTTP服务器
    def find_available_port(start_port=8000, max_port=8020):
        """查找可用端口"""
        import socket
        for port in range(start_port, max_port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return None

    port = find_available_port()
    if port is None:
        print("❌ 无法找到可用端口 (8000-8020)")
        print("请检查是否有其他程序占用了这些端口")
        return

    if port != 8000:
        print(f"端口 8000 被占用，使用端口 {port}")

    try:
        # 使用 ThreadingTCPServer 避免阻塞其他进程
        class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True
            daemon_threads = True

        with ThreadingTCPServer(("127.0.0.1", port), ADSBHTTPHandler) as httpd:
            print(f"服务器启动成功！")
            print(f"访问地址：")
            print(f"  主页: http://127.0.0.1:{port}/")
            print(f"  雷达: http://127.0.0.1:{port}/radar/")
            print(f"  API:  http://127.0.0.1:{port}/api/aircraft/")
            print(f"\n按 Ctrl+C 停止服务器")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        system.running = False
        print("服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")


if __name__ == '__main__':
    main()
