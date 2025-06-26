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
                
        elif path == '/api/statistics/':
            # 统计信息
            if aircraft_data:
                altitudes = [data['altitude'] for data in aircraft_data.values()]
                altitude_ranges = {
                    '低空 (0-10000ft)': len([a for a in altitudes if a < 10000]),
                    '中空 (10000-33000ft)': len([a for a in altitudes if 10000 <= a < 33000]),
                    '高空 (33000ft+)': len([a for a in altitudes if a >= 33000]),
                }
                
                response = {
                    'status': 'success',
                    'statistics': {
                        'total_aircraft': len(aircraft_data),
                        'altitude_distribution': altitude_ranges,
                        'average_altitude': sum(altitudes) / len(altitudes),
                    }
                }
            else:
                response = {
                    'status': 'success',
                    'statistics': {
                        'total_aircraft': 0,
                        'altitude_distribution': {},
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
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
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
            color: white;
            text-decoration: none;
            margin: 0 15px;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            border: none;
            cursor: pointer;
            font-family: inherit;
            font-size: inherit;
            transition: all 0.3s ease;
        }}
        .nav-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}
        .nav-btn.active {{
            background: rgba(0,123,255,0.8);
            box-shadow: 0 0 10px rgba(0,123,255,0.5);
        }}
        .content {{
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .aircraft-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .aircraft-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 15px;
            border: 1px solid rgba(255,255,255,0.2);
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

        /* 雷达视图样式 */
        #radar-container {{
            position: relative;
            width: 100%;
            height: 500px;
            background: radial-gradient(circle, #001122 0%, #000000 100%);
            border-radius: 10px;
            overflow: hidden;
        }}

        #radar-canvas {{
            width: 100%;
            height: 100%;
            cursor: crosshair;
        }}

        .radar-controls {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 10px;
            z-index: 100;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 12px;
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
            background: #000;
            color: #00ff00;
            border: 1px solid #00ff00;
            padding: 2px;
            font-family: inherit;
            font-size: 11px;
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
                <h3>🌍 3D地球可视化区域</h3>
                <p>在这里将显示3D地球和飞机位置</p>
                <p>使用Three.js渲染真实地球模型</p>
                <div id="visualization-placeholder" style="margin-top: 20px;">
                    <p>🚧 3D可视化功能开发中...</p>
                    <p>当前显示简化版本，完整3D可视化需要安装Three.js</p>
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
        
        // 更新飞机列表
        function updateAircraftList(aircraft) {{
            const listContainer = document.getElementById('aircraft-list');
            
            if (Object.keys(aircraft).length === 0) {{
                listContainer.innerHTML = '<div class="aircraft-card"><p>暂无飞机数据</p></div>';
                return;
            }}
            
            let html = '';
            Object.values(aircraft).forEach(plane => {{
                const distance = Math.sqrt(plane.enu_e**2 + plane.enu_n**2) / 1000;
                const emoji = plane.altitude < 10000 ? '🛩️' : plane.altitude < 30000 ? '✈️' : '🛫';
                
                // 计算飞行时间
                const firstSeen = new Date(plane.first_seen || plane.timestamp);
                const lastSeen = new Date(plane.last_seen || plane.timestamp);
                const flightDuration = Math.round((lastSeen - firstSeen) / 1000 / 60); // 分钟

                // 计算高度变化
                const altChange = plane.max_altitude - plane.min_altitude;

                html += `
                    <div class="aircraft-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h4>${{emoji}} ${{plane.icao}}</h4>
                            <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">
                                ${{plane.update_count || 1}} 次更新
                            </span>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                            <div>
                                <p><strong>📍 当前位置:</strong><br>
                                ${{plane.latitude.toFixed(4)}}°, ${{plane.longitude.toFixed(4)}}°</p>
                                <p><strong>📏 距离:</strong> ${{distance.toFixed(1)}} km</p>
                            </div>
                            <div>
                                <p><strong>✈️ 当前高度:</strong><br>
                                ${{plane.altitude}}ft (${{Math.round(plane.altitude * 0.3048)}}m)</p>
                                <p><strong>⚡ 速度:</strong> ${{plane.speed || 0}} km/h</p>
                            </div>
                        </div>

                        <div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 5px; margin-bottom: 8px;">
                            <p style="margin: 2px 0;"><strong>📊 高度统计:</strong></p>
                            <p style="margin: 2px 0; font-size: 0.9em;">
                                最高: ${{plane.max_altitude}}ft |
                                最低: ${{plane.min_altitude}}ft |
                                平均: ${{plane.avg_altitude}}ft
                                ${{altChange > 1000 ? '<br><span style="color: #ffd700;">⚠️ 高度变化: ' + altChange + 'ft</span>' : ''}}
                            </p>
                        </div>

                        <div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 5px; margin-bottom: 8px;">
                            <p style="margin: 2px 0;"><strong>🕒 时间信息:</strong></p>
                            <p style="margin: 2px 0; font-size: 0.9em;">
                                首次发现: ${{firstSeen.toLocaleTimeString()}}<br>
                                最后更新: ${{lastSeen.toLocaleTimeString()}}
                                ${{flightDuration > 0 ? '<br>跟踪时长: ' + flightDuration + ' 分钟' : ''}}
                            </p>
                        </div>

                        <details style="margin-top: 8px;">
                            <summary style="cursor: pointer; color: #87ceeb;">🔍 详细坐标信息</summary>
                            <div style="margin-top: 5px; font-size: 0.9em;">
                                <p><strong>ENU坐标:</strong><br>
                                E: ${{plane.enu_e.toFixed(0)}}m |
                                N: ${{plane.enu_n.toFixed(0)}}m |
                                U: ${{plane.enu_u.toFixed(0)}}m</p>
                                ${{plane.positions && plane.positions.length > 1 ?
                                    '<p><strong>位置历史:</strong> ' + plane.positions.length + ' 个记录点</p>' : ''}}
                            </div>
                        </details>
                    </div>
                `;
            }});
            
            listContainer.innerHTML = html;
        }}
        
        // 更新统计信息
        async function updateStatistics() {{
            try {{
                const response = await fetch('/api/statistics/');
                const data = await response.json();
                
                if (data.status === 'success') {{
                    const stats = data.statistics;
                    const statsContainer = document.getElementById('statistics');
                    
                    statsContainer.innerHTML = `
                        <div class="stat-card">
                            <h4>总飞机数</h4>
                            <h2>${{stats.total_aircraft || 0}}</h2>
                        </div>
                        <div class="stat-card">
                            <h4>平均高度</h4>
                            <h2>${{Math.round(stats.average_altitude || 0)}}ft</h2>
                        </div>
                        <div class="stat-card">
                            <h4>高度分布</h4>
                            <p>低空: ${{(stats.altitude_distribution && stats.altitude_distribution['低空 (0-10000ft)']) || 0}}</p>
                            <p>中空: ${{(stats.altitude_distribution && stats.altitude_distribution['中空 (10000-33000ft)']) || 0}}</p>
                            <p>高空: ${{(stats.altitude_distribution && stats.altitude_distribution['高空 (33000ft+)']) || 0}}</p>
                        </div>
                    `;
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
            radarCtx.strokeStyle = '#00ff0030';
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
                radarCtx.fillStyle = '#00ff0060';
                radarCtx.font = '12px Courier New';
                const distance = Math.round(radarRange * i / 4);
                radarCtx.fillText(distance + 'km', radarCenter.x + radius - 20, radarCenter.y - 5);
            }}

            // 绘制方位线
            radarCtx.strokeStyle = '#00ff0020';
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
            radarCtx.fillStyle = '#ff0000';
            radarCtx.beginPath();
            radarCtx.arc(radarCenter.x, radarCenter.y, 3, 0, Math.PI * 2);
            radarCtx.fill();
        }}

        function drawSweepLine() {{
            const maxRadius = Math.min(radarCanvas.width, radarCanvas.height) * 0.4;
            const radian = (sweepAngle - 90) * Math.PI / 180;
            const x2 = radarCenter.x + Math.cos(radian) * maxRadius;
            const y2 = radarCenter.y + Math.sin(radian) * maxRadius;

            radarCtx.strokeStyle = '#00ff0080';
            radarCtx.lineWidth = 2;
            radarCtx.beginPath();
            radarCtx.moveTo(radarCenter.x, radarCenter.y);
            radarCtx.lineTo(x2, y2);
            radarCtx.stroke();
        }}

        function drawRadarAircraft() {{
            Object.values(radarAircraftData).forEach(aircraft => {{
                const distance = Math.sqrt(aircraft.enu_e**2 + aircraft.enu_n**2) / 1000;
                if (distance > radarRange) return;

                const maxRadius = Math.min(radarCanvas.width, radarCanvas.height) * 0.4;
                const scale = maxRadius / radarRange;

                const x = radarCenter.x + (aircraft.enu_e / 1000) * scale;
                const y = radarCenter.y - (aircraft.enu_n / 1000) * scale;

                // 绘制飞机点
                radarCtx.fillStyle = getAircraftRadarColor(aircraft.altitude);
                radarCtx.beginPath();
                radarCtx.arc(x, y, 4, 0, Math.PI * 2);
                radarCtx.fill();

                // 绘制标签
                if (showLabels) {{
                    radarCtx.fillStyle = '#ffffff';
                    radarCtx.font = '10px Courier New';
                    radarCtx.fillText(aircraft.icao, x + 6, y - 6);
                }}
            }});
        }}

        function getAircraftRadarColor(altitude) {{
            if (altitude < 10000) return '#ff4444';
            if (altitude < 33000) return '#ffff44';
            return '#4444ff';
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

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {{
            fetchAircraftData();

            // 自动刷新
            setInterval(() => {{
                if (autoRefresh) {{
                    fetchAircraftData();
                    if (document.getElementById('view-radar').style.display !== 'none') {{
                        updateRadarData();
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
                            }
                        else:
                            # 更新现有飞机数据
                            prev_data = aircraft_data[icao]

                            # 计算速度（简化计算）
                            prev_time = datetime.fromisoformat(prev_data['timestamp'])
                            time_diff = (current_time - prev_time).total_seconds()

                            if time_diff > 0:
                                # 计算距离变化
                                prev_enu = (prev_data['enu_e'], prev_data['enu_n'], prev_data['enu_u'])
                                distance_moved = ((enu_coords[0] - prev_enu[0])**2 +
                                                (enu_coords[1] - prev_enu[1])**2 +
                                                (enu_coords[2] - prev_enu[2])**2)**0.5
                                speed_ms = distance_moved / time_diff if time_diff > 0 else 0
                                speed_kmh = speed_ms * 3.6
                            else:
                                speed_kmh = prev_data.get('speed', 0)

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
                                'positions': positions,
                                'altitudes': altitudes,
                                'max_altitude': max_alt,
                                'min_altitude': min_alt,
                                'avg_altitude': round(avg_alt, 0),
                            })
                
                # 清理过期数据（延长到10分钟，避免频繁清理）
                current_time = datetime.now()
                expired_icaos = []
                for icao, data in aircraft_data.items():
                    last_seen = datetime.fromisoformat(data.get('last_seen', data['timestamp']))
                    if (current_time - last_seen).seconds > 600:  # 10分钟过期
                        expired_icaos.append(icao)
                        print(f"清理过期飞机数据: {icao} (最后更新: {last_seen.strftime('%H:%M:%S')})")

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

        response = input("\n是否继续启动可视化系统? (y/n): ").lower().strip()
        if response not in ['y', 'yes', '是']:
            print("已取消启动")
            return

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
