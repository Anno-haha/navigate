#!/usr/bin/env python3
"""
实时2D雷达视图系统
优先保证实时性，专门用于雷达显示
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

# 导入安全文件读取器
from safe_file_reader import SafeADSBDataReader

# 全局变量
aircraft_data = {}
radar_config = {
    'range_km': 100,
    'center_lat': 39.9,
    'center_lon': 116.4,
    'update_interval': 0.5,  # 500ms更新间隔，保证实时性
}

class RadarHTTPHandler(SimpleHTTPRequestHandler):
    """雷达专用HTTP处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)
        
        # API路由
        if path.startswith('/api/'):
            self.handle_api_request(path, query)
        elif path == '/' or path == '/radar':
            self.serve_radar_page()
        else:
            # 静态文件
            super().do_GET()
    
    def handle_api_request(self, path, query):
        """处理API请求"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')  # 禁用缓存，保证实时性
        self.end_headers()
        
        if path == '/api/radar/aircraft':
            # 获取雷达范围内的飞机数据
            range_km = float(query.get('range', [radar_config['range_km']])[0])
            
            radar_aircraft = {}
            for icao, data in aircraft_data.items():
                # 计算距离
                distance = ((data['enu_e']**2 + data['enu_n']**2)**0.5) / 1000
                if distance <= range_km:
                    # 计算雷达坐标
                    bearing = math.atan2(data['enu_e'], data['enu_n']) * 180 / math.pi
                    bearing = (bearing + 360) % 360
                    
                    radar_aircraft[icao] = {
                        'icao': icao,
                        'distance': round(distance, 1),
                        'bearing': round(bearing, 1),
                        'altitude': data['altitude'],
                        'enu_e': data['enu_e'],
                        'enu_n': data['enu_n'],
                        'speed': data.get('speed', 0),
                        'timestamp': data['timestamp'],
                        'radar_x': data['enu_e'],
                        'radar_y': -data['enu_n'],  # 雷达坐标系Y轴向下
                    }
            
            response = {
                'status': 'success',
                'aircraft': radar_aircraft,
                'config': radar_config,
                'timestamp': datetime.now().isoformat(),
            }
            
        elif path == '/api/radar/config':
            # 更新雷达配置
            if 'range' in query:
                radar_config['range_km'] = float(query['range'][0])
            
            response = {
                'status': 'success',
                'config': radar_config
            }
            
        else:
            response = {'status': 'error', 'message': 'API endpoint not found'}
        
        self.wfile.write(json.dumps(response).encode())
    
    def serve_radar_page(self):
        """提供雷达页面"""
        html = self.get_radar_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def get_radar_html(self):
        """生成实时2D雷达HTML页面"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>实时2D雷达 - ADS-B监控</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #000;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            overflow: hidden;
        }
        
        #radar-container {
            position: relative;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(circle, #001122 0%, #000000 100%);
        }
        
        #radar-canvas {
            position: absolute;
            top: 0;
            left: 0;
            cursor: crosshair;
        }
        
        .radar-controls {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 10px;
            z-index: 100;
        }
        
        .radar-info {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 10px;
            z-index: 100;
            min-width: 200px;
        }
        
        .aircraft-details {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.9);
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 10px;
            z-index: 100;
            max-width: 300px;
            display: none;
        }
        
        .control-group {
            margin-bottom: 10px;
        }
        
        .control-group label {
            display: block;
            margin-bottom: 3px;
            font-size: 12px;
        }
        
        .control-group select, .control-group input {
            background: #000;
            color: #00ff00;
            border: 1px solid #00ff00;
            padding: 3px;
            font-family: inherit;
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-online { background: #00ff00; }
        .status-offline { background: #ff0000; }
        
        .aircraft-count {
            font-size: 14px;
            font-weight: bold;
        }
        
        .sweep-line {
            position: absolute;
            width: 2px;
            background: linear-gradient(to bottom, #00ff00, transparent);
            transform-origin: bottom center;
            pointer-events: none;
            z-index: 50;
        }
    </style>
</head>
<body>
    <div id="radar-container">
        <canvas id="radar-canvas"></canvas>
        
        <!-- 雷达扫描线 -->
        <div id="sweep-line" class="sweep-line"></div>
        
        <!-- 控制面板 -->
        <div class="radar-controls">
            <div class="control-group">
                <label>雷达范围</label>
                <select id="range-select" onchange="changeRange()">
                    <option value="20">20 km</option>
                    <option value="50">50 km</option>
                    <option value="100" selected>100 km</option>
                    <option value="200">200 km</option>
                </select>
            </div>
            
            <div class="control-group">
                <label>
                    <input type="checkbox" id="show-sweep" checked onchange="toggleSweep()">
                    雷达扫描
                </label>
            </div>
            
            <div class="control-group">
                <label>
                    <input type="checkbox" id="show-trails" checked onchange="toggleTrails()">
                    飞机轨迹
                </label>
            </div>
            
            <div class="control-group">
                <label>
                    <input type="checkbox" id="show-labels" checked onchange="toggleLabels()">
                    飞机标签
                </label>
            </div>
        </div>
        
        <!-- 信息面板 -->
        <div class="radar-info">
            <div>
                <span class="status-indicator" id="status-indicator"></span>
                <span>雷达状态</span>
            </div>
            <div class="aircraft-count" id="aircraft-count">0 架飞机</div>
            <div id="last-update">--:--:--</div>
            <div style="margin-top: 10px; font-size: 11px;">
                <div>范围: <span id="current-range">100</span> km</div>
                <div>更新: <span id="update-rate">--</span> Hz</div>
                <div>延迟: <span id="latency">--</span> ms</div>
            </div>
        </div>
        
        <!-- 飞机详情 -->
        <div class="aircraft-details" id="aircraft-details">
            <div id="aircraft-detail-content"></div>
            <button onclick="closeDetails()" style="margin-top: 10px; background: #000; color: #00ff00; border: 1px solid #00ff00; padding: 5px;">关闭</button>
        </div>
    </div>
    
    <script>
        // 雷达参数
        let canvas, ctx;
        let radarRange = 100;
        let radarCenter = { x: 0, y: 0 };
        let sweepAngle = 0;
        let aircraftData = {};
        let aircraftTrails = {};
        let lastUpdateTime = 0;
        let updateCount = 0;
        let showSweep = true;
        let showTrails = true;
        let showLabels = true;
        
        // 性能监控
        let frameCount = 0;
        let lastFrameTime = Date.now();
        
        // 初始化
        function init() {
            canvas = document.getElementById('radar-canvas');
            ctx = canvas.getContext('2d');
            
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            canvas.addEventListener('click', onCanvasClick);
            
            // 开始雷达扫描动画
            startSweepAnimation();
            
            // 开始数据更新
            startDataUpdate();
            
            // 开始渲染循环
            requestAnimationFrame(render);
        }
        
        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            radarCenter.x = canvas.width / 2;
            radarCenter.y = canvas.height / 2;
        }
        
        function startSweepAnimation() {
            setInterval(() => {
                if (showSweep) {
                    sweepAngle = (sweepAngle + 3) % 360;
                    updateSweepLine();
                }
            }, 50); // 20 FPS扫描动画
        }
        
        function updateSweepLine() {
            const sweepLine = document.getElementById('sweep-line');
            const radius = Math.min(canvas.width, canvas.height) * 0.4;
            
            sweepLine.style.height = radius + 'px';
            sweepLine.style.left = (radarCenter.x - 1) + 'px';
            sweepLine.style.bottom = (canvas.height - radarCenter.y) + 'px';
            sweepLine.style.transform = `rotate(${sweepAngle}deg)`;
            sweepLine.style.display = showSweep ? 'block' : 'none';
        }
        
        function startDataUpdate() {
            // 使用requestAnimationFrame优化的数据更新
            let lastFetchTime = 0;
            const fetchInterval = 500; // 500ms

            function updateLoop() {
                const now = Date.now();
                if (now - lastFetchTime >= fetchInterval) {
                    fetchAircraftData();
                    lastFetchTime = now;
                }
                requestAnimationFrame(updateLoop);
            }

            updateLoop();
        }
        
        async function fetchAircraftData() {
            const startTime = Date.now();
            
            try {
                const response = await fetch(`/api/radar/aircraft?range=${radarRange}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    aircraftData = data.aircraft;
                    updateAircraftTrails();
                    updateInfo(data);
                    
                    // 更新状态指示器
                    document.getElementById('status-indicator').className = 'status-indicator status-online';
                    
                    // 计算延迟
                    const latency = Date.now() - startTime;
                    document.getElementById('latency').textContent = latency + '';
                    
                    updateCount++;
                } else {
                    document.getElementById('status-indicator').className = 'status-indicator status-offline';
                }
            } catch (error) {
                console.error('获取数据失败:', error);
                document.getElementById('status-indicator').className = 'status-indicator status-offline';
            }
        }
        
        function updateAircraftTrails() {
            Object.keys(aircraftData).forEach(icao => {
                const aircraft = aircraftData[icao];
                
                if (!aircraftTrails[icao]) {
                    aircraftTrails[icao] = [];
                }
                
                aircraftTrails[icao].push({
                    x: aircraft.radar_x,
                    y: aircraft.radar_y,
                    time: Date.now()
                });
                
                // 限制轨迹长度
                if (aircraftTrails[icao].length > 30) {
                    aircraftTrails[icao].shift();
                }
            });
            
            // 清理过期轨迹
            const currentTime = Date.now();
            Object.keys(aircraftTrails).forEach(icao => {
                if (!aircraftData[icao]) {
                    delete aircraftTrails[icao];
                }
            });
        }
        
        function updateInfo(data) {
            const count = Object.keys(aircraftData).length;
            document.getElementById('aircraft-count').textContent = count + ' 架飞机';
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            // 计算更新频率
            const now = Date.now();
            if (now - lastFrameTime >= 1000) {
                const fps = Math.round(updateCount * 1000 / (now - lastFrameTime));
                document.getElementById('update-rate').textContent = fps + '';
                updateCount = 0;
                lastFrameTime = now;
            }
        }
        
        function render() {
            // 清空画布
            ctx.fillStyle = '#000011';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // 绘制雷达网格
            drawRadarGrid();
            
            // 绘制飞机轨迹
            if (showTrails) {
                drawAircraftTrails();
            }
            
            // 绘制飞机
            drawAircraft();
            
            // 绘制飞机标签
            if (showLabels) {
                drawAircraftLabels();
            }
            
            requestAnimationFrame(render);
        }
        
        function drawRadarGrid() {
            ctx.strokeStyle = '#00ff0030';
            ctx.lineWidth = 1;
            
            const maxRadius = Math.min(canvas.width, canvas.height) * 0.4;
            const step = maxRadius / 4;
            
            // 绘制同心圆
            for (let i = 1; i <= 4; i++) {
                const radius = step * i;
                ctx.beginPath();
                ctx.arc(radarCenter.x, radarCenter.y, radius, 0, Math.PI * 2);
                ctx.stroke();
                
                // 距离标签
                ctx.fillStyle = '#00ff0060';
                ctx.font = '12px Courier New';
                const distance = Math.round(radarRange * i / 4);
                ctx.fillText(distance + 'km', radarCenter.x + radius - 20, radarCenter.y - 5);
            }
            
            // 绘制方位线
            ctx.strokeStyle = '#00ff0020';
            for (let angle = 0; angle < 360; angle += 30) {
                const radian = angle * Math.PI / 180;
                const x2 = radarCenter.x + Math.cos(radian - Math.PI/2) * maxRadius;
                const y2 = radarCenter.y + Math.sin(radian - Math.PI/2) * maxRadius;
                
                ctx.beginPath();
                ctx.moveTo(radarCenter.x, radarCenter.y);
                ctx.lineTo(x2, y2);
                ctx.stroke();
                
                // 方位标签
                ctx.fillStyle = '#00ff0060';
                const labelX = radarCenter.x + Math.cos(radian - Math.PI/2) * (maxRadius + 15);
                const labelY = radarCenter.y + Math.sin(radian - Math.PI/2) * (maxRadius + 15);
                ctx.fillText(angle + '°', labelX - 10, labelY + 5);
            }
            
            // 中心点
            ctx.fillStyle = '#ff0000';
            ctx.beginPath();
            ctx.arc(radarCenter.x, radarCenter.y, 3, 0, Math.PI * 2);
            ctx.fill();
        }
        
        function drawAircraftTrails() {
            Object.keys(aircraftTrails).forEach(icao => {
                const trail = aircraftTrails[icao];
                if (trail.length < 2) return;
                
                const aircraft = aircraftData[icao];
                if (!aircraft) return;
                
                ctx.strokeStyle = getAircraftColor(aircraft.altitude) + '60';
                ctx.lineWidth = 2;
                ctx.beginPath();
                
                for (let i = 0; i < trail.length; i++) {
                    const point = trail[i];
                    const screenPos = enuToScreen(point.x, point.y);
                    
                    if (i === 0) {
                        ctx.moveTo(screenPos.x, screenPos.y);
                    } else {
                        ctx.lineTo(screenPos.x, screenPos.y);
                    }
                }
                
                ctx.stroke();
            });
        }
        
        function drawAircraft() {
            Object.values(aircraftData).forEach(aircraft => {
                const screenPos = enuToScreen(aircraft.radar_x, aircraft.radar_y);
                
                // 绘制飞机点
                ctx.fillStyle = getAircraftColor(aircraft.altitude);
                ctx.beginPath();
                ctx.arc(screenPos.x, screenPos.y, 6, 0, Math.PI * 2);
                ctx.fill();
                
                // 绘制边框
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // 绘制脉冲效果
                const pulseRadius = 6 + Math.sin(Date.now() / 200) * 3;
                ctx.strokeStyle = getAircraftColor(aircraft.altitude) + '40';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(screenPos.x, screenPos.y, pulseRadius, 0, Math.PI * 2);
                ctx.stroke();
            });
        }
        
        function drawAircraftLabels() {
            ctx.font = '11px Courier New';
            
            Object.values(aircraftData).forEach(aircraft => {
                const screenPos = enuToScreen(aircraft.radar_x, aircraft.radar_y);
                
                ctx.fillStyle = '#ffffff';
                ctx.fillText(aircraft.icao, screenPos.x + 10, screenPos.y - 10);
                
                // 距离和高度信息
                ctx.fillStyle = '#00ff0080';
                ctx.font = '9px Courier New';
                ctx.fillText(`${aircraft.distance}km ${aircraft.altitude}ft`, 
                           screenPos.x + 10, screenPos.y + 5);
                ctx.font = '11px Courier New';
            });
        }
        
        function enuToScreen(enu_x, enu_y) {
            const maxRadius = Math.min(canvas.width, canvas.height) * 0.4;
            const scale = maxRadius / (radarRange * 1000);
            
            return {
                x: radarCenter.x + enu_x * scale,
                y: radarCenter.y + enu_y * scale
            };
        }
        
        function getAircraftColor(altitude) {
            if (altitude < 10000) return '#ff4444';      // 红色 - 低空
            if (altitude < 33000) return '#ffff44';      // 黄色 - 中空
            return '#4444ff';                            // 蓝色 - 高空
        }
        
        function onCanvasClick(event) {
            const rect = canvas.getBoundingClientRect();
            const clickX = event.clientX - rect.left;
            const clickY = event.clientY - rect.top;
            
            // 查找点击的飞机
            Object.values(aircraftData).forEach(aircraft => {
                const screenPos = enuToScreen(aircraft.radar_x, aircraft.radar_y);
                const distance = Math.sqrt((clickX - screenPos.x)**2 + (clickY - screenPos.y)**2);
                
                if (distance < 15) {
                    showAircraftDetails(aircraft);
                }
            });
        }
        
        function showAircraftDetails(aircraft) {
            const details = document.getElementById('aircraft-details');
            const content = document.getElementById('aircraft-detail-content');
            
            content.innerHTML = `
                <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">
                    ${aircraft.icao}
                </div>
                <div>距离: ${aircraft.distance} km</div>
                <div>方位: ${aircraft.bearing}°</div>
                <div>高度: ${aircraft.altitude} ft</div>
                <div>速度: ${aircraft.speed} km/h</div>
                <div style="margin-top: 10px; font-size: 10px;">
                    ENU: E${Math.round(aircraft.enu_e)}m N${Math.round(aircraft.enu_n)}m
                </div>
            `;
            
            details.style.display = 'block';
        }
        
        function closeDetails() {
            document.getElementById('aircraft-details').style.display = 'none';
        }
        
        function changeRange() {
            radarRange = parseInt(document.getElementById('range-select').value);
            document.getElementById('current-range').textContent = radarRange;
        }
        
        function toggleSweep() {
            showSweep = document.getElementById('show-sweep').checked;
        }
        
        function toggleTrails() {
            showTrails = document.getElementById('show-trails').checked;
        }
        
        function toggleLabels() {
            showLabels = document.getElementById('show-labels').checked;
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
        """

class RadarDataProcessor:
    """雷达数据处理器"""
    
    def __init__(self):
        self.data_reader = SafeADSBDataReader()
        self.running = False
        self.data_thread = None
        
    def start(self):
        """启动数据处理"""
        self.running = True
        self.data_thread = threading.Thread(target=self._data_loop, daemon=True)
        self.data_thread.start()
        
    def _data_loop(self):
        """数据处理循环 - 优化实时性"""
        global aircraft_data
        
        while self.running:
            try:
                # 获取最新数据
                latest_data = self.data_reader.get_latest_data()
                
                if latest_data:
                    current_time = datetime.now()
                    
                    for icao, aircraft in latest_data.items():
                        # 计算速度（如果有历史数据）
                        speed = 0
                        if icao in aircraft_data:
                            prev_data = aircraft_data[icao]
                            prev_time = datetime.fromisoformat(prev_data['timestamp'])
                            time_diff = (current_time - prev_time).total_seconds()
                            
                            if time_diff > 0:
                                prev_enu = (prev_data['enu_e'], prev_data['enu_n'])
                                curr_enu = (aircraft['enu_e'], aircraft['enu_n'])
                                distance_moved = ((curr_enu[0] - prev_enu[0])**2 + 
                                                (curr_enu[1] - prev_enu[1])**2)**0.5
                                speed = (distance_moved / time_diff) * 3.6  # m/s to km/h
                        
                        # 更新飞机数据
                        aircraft_data[icao] = {
                            'icao': icao,
                            'latitude': aircraft['latitude'],
                            'longitude': aircraft['longitude'],
                            'altitude': aircraft['altitude'],
                            'enu_e': aircraft['enu_e'],
                            'enu_n': aircraft['enu_n'],
                            'enu_u': aircraft['enu_u'],
                            'speed': round(speed, 1),
                            'timestamp': current_time.isoformat(),
                        }
                
                # 清理过期数据（5分钟）
                current_time = datetime.now()
                expired_icaos = []
                for icao, data in aircraft_data.items():
                    data_time = datetime.fromisoformat(data['timestamp'])
                    if (current_time - data_time).seconds > 300:
                        expired_icaos.append(icao)
                
                for icao in expired_icaos:
                    del aircraft_data[icao]
                
                time.sleep(0.2)  # 200ms间隔，保证高实时性
                
            except Exception as e:
                print(f"雷达数据处理错误: {e}")
                time.sleep(1)

def main():
    """主函数"""
    print("实时2D雷达系统")
    print("=" * 40)
    print("优先保证实时性的雷达显示")
    print("更新间隔: 500ms")
    print("=" * 40)
    
    # 导入数学库
    import math
    globals()['math'] = math
    
    # 启动数据处理
    processor = RadarDataProcessor()
    processor.start()
    
    # 查找可用端口
    def find_available_port(start_port=8001):
        import socket
        for port in range(start_port, start_port + 10):
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
        print("无法找到可用端口")
        return
    
    try:
        # 使用ThreadingTCPServer提高并发性能
        class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True
            daemon_threads = True
        
        with ThreadingTCPServer(("127.0.0.1", port), RadarHTTPHandler) as httpd:
            print(f"雷达服务器启动成功！")
            print(f"访问地址: http://127.0.0.1:{port}/")
            print(f"实时性优化: 500ms更新间隔")
            print(f"\n按 Ctrl+C 停止服务器")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n正在停止雷达服务器...")
        processor.running = False
        print("雷达服务器已停止")
    except Exception as e:
        print(f"雷达服务器启动失败: {e}")

if __name__ == '__main__':
    main()
