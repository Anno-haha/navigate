#!/usr/bin/env python3

import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class MinimalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/aircraft/':
            # 读取数据文件
            aircraft_data = {}
            try:
                if os.path.exists('adsb_decoded.log'):
                    with open('adsb_decoded.log', 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        current_time = datetime.now()
                        
                        for line in lines[-100:]:  # 只处理最后100行
                            try:
                                parts = line.strip().split(',')
                                if len(parts) >= 5:
                                    timestamp_str = parts[0]
                                    icao = parts[1]
                                    lat = float(parts[2])
                                    lon = float(parts[3])
                                    alt = int(parts[4])

                                    # 解析额外的坐标信息
                                    ecef_x = ecef_y = ecef_z = None
                                    enu_e = enu_n = enu_u = None

                                    if len(parts) >= 8:  # ECEF坐标
                                        try:
                                            ecef_x = float(parts[5])
                                            ecef_y = float(parts[6])
                                            ecef_z = float(parts[7])
                                        except:
                                            pass

                                    if len(parts) >= 11:  # ENU坐标
                                        try:
                                            enu_e = float(parts[8])
                                            enu_n = float(parts[9])
                                            enu_u = float(parts[10])
                                        except:
                                            pass

                                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                    time_diff = (current_time - timestamp).total_seconds()

                                    if time_diff <= 86400:  # 24小时内
                                        aircraft_data[icao] = {
                                            'icao': icao,
                                            'lat': lat,
                                            'lon': lon,
                                            'alt': alt,
                                            'timestamp': timestamp_str,
                                            'time_diff': time_diff,
                                            'ecef_x': ecef_x,
                                            'ecef_y': ecef_y,
                                            'ecef_z': ecef_z,
                                            'enu_e': enu_e,
                                            'enu_n': enu_n,
                                            'enu_u': enu_u
                                        }
                            except:
                                continue
            except Exception as e:
                pass
            
            # 返回JSON响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'success',
                'count': len(aircraft_data),
                'aircraft': list(aircraft_data.values())
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        elif self.path == '/api/statistics/':
            # 统计信息
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'success',
                'total_aircraft': 0,
                'altitude_distribution': {
                    'low': 0,
                    'medium': 0,
                    'high': 0
                }
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        else:
            # 返回HTML页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>ADS-B可视化系统 - 简化版</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.6;
            overflow-x: hidden;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            padding: 40px 0 30px 0;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }

        .header .subtitle {
            font-size: 1.2rem;
            color: #86868b;
            font-weight: 400;
        }

        .status {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            margin: 20px 0;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .status.online {
            background: rgba(52, 199, 89, 0.1);
            color: #34c759;
            border: 1px solid rgba(52, 199, 89, 0.2);
        }

        .status.offline {
            background: rgba(255, 59, 48, 0.1);
            color: #ff3b30;
            border: 1px solid rgba(255, 59, 48, 0.2);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status.online .status-dot {
            background: #34c759;
        }

        .status.offline .status-dot {
            background: #ff3b30;
        }

        .main-layout {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }

        .panel {
            background: #ffffff;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            border: 1px solid rgba(0, 0, 0, 0.04);
        }

        .panel:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        }

        .panel h3 {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
        }

        .panel h3 .icon {
            margin-right: 8px;
            font-size: 1.1em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
        }

        .stat-item {
            background: #f6f6f6;
            padding: 20px 16px;
            border-radius: 12px;
            text-align: center;
            transition: all 0.3s ease;
            border: 1px solid rgba(0, 0, 0, 0.04);
        }

        .stat-item:hover {
            background: #f0f0f0;
            transform: translateY(-1px);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #007aff;
            margin-bottom: 4px;
            font-variant-numeric: tabular-nums;
        }

        .stat-label {
            font-size: 0.85rem;
            color: #86868b;
            font-weight: 500;
        }

        .radar-section {
            grid-column: 1 / -1;
            margin-top: 20px;
        }

        .radar-container {
            width: 100%;
            height: 500px;
            background: #ffffff;
            border-radius: 16px;
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(0, 0, 0, 0.04);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }

        .radar-grid {
            position: absolute;
            width: 100%;
            height: 100%;
            background-image:
                radial-gradient(circle, transparent 24%, rgba(0, 122, 255, 0.05) 25%, rgba(0, 122, 255, 0.05) 26%, transparent 27%),
                radial-gradient(circle, transparent 49%, rgba(0, 122, 255, 0.05) 50%, rgba(0, 122, 255, 0.05) 51%, transparent 52%),
                radial-gradient(circle, transparent 74%, rgba(0, 122, 255, 0.05) 75%, rgba(0, 122, 255, 0.05) 76%, transparent 77%);
            background-size: 100% 100%;
            background-position: center;
        }

        .radar-crosshair {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent 0%, rgba(0, 122, 255, 0.3) 50%, transparent 100%);
            transform: translate(-50%, -50%);
        }

        .radar-crosshair::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 1px;
            height: 500px;
            background: linear-gradient(0deg, transparent 0%, rgba(0, 122, 255, 0.3) 50%, transparent 100%);
            transform: translate(-50%, -50%);
        }
        .aircraft-dot {
            position: absolute;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            cursor: pointer;
            transition: all 0.3s ease;
            border: 3px solid #ffffff;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.2);
            z-index: 5;
        }

        .aircraft-dot:hover {
            transform: translate(-50%, -50%) scale(1.4);
            z-index: 15;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }

        .aircraft-label {
            position: absolute;
            top: -30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255, 255, 255, 0.95);
            color: #1d1d1f;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            z-index: 20;
        }

        .aircraft-dot:hover .aircraft-label {
            opacity: 1;
        }

        .aircraft-tooltip {
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.4;
            max-width: 280px;
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .aircraft-list-section {
            grid-column: 1 / -1;
            margin-top: 20px;
        }

        .aircraft-list {
            max-height: 500px;
            overflow-y: auto;
            padding: 0;
            background: #ffffff;
            border-radius: 16px;
            border: 1px solid rgba(0, 0, 0, 0.04);
        }

        .aircraft-list::-webkit-scrollbar {
            width: 8px;
        }

        .aircraft-list::-webkit-scrollbar-track {
            background: #f5f5f7;
            border-radius: 4px;
        }

        .aircraft-list::-webkit-scrollbar-thumb {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
        }

        .aircraft-list::-webkit-scrollbar-thumb:hover {
            background: rgba(0, 0, 0, 0.3);
        }

        .aircraft-item {
            padding: 20px 24px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
            display: block;
        }

        .aircraft-item:last-child {
            border-bottom: none;
        }

        .aircraft-item:hover {
            background: #f8f9fa;
            transform: translateX(4px);
        }

        .aircraft-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .aircraft-item .icao {
            font-weight: 700;
            font-size: 20px;
            color: #1d1d1f;
            letter-spacing: 0.5px;
        }

        .aircraft-status {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .altitude-badge {
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .altitude-low { background: rgba(52, 199, 89, 0.15); color: #34c759; }
        .altitude-med { background: rgba(255, 149, 0, 0.15); color: #ff9500; }
        .altitude-high { background: rgba(255, 59, 48, 0.15); color: #ff3b30; }

        .aircraft-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 8px;
        }

        .detail-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .detail-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 15px;
        }

        .detail-label {
            color: #86868b;
            font-weight: 500;
            min-width: 80px;
        }

        .detail-value {
            color: #1d1d1f;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            text-align: right;
        }

        .distance-indicator {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: rgba(0, 122, 255, 0.1);
            color: #007aff;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }

        .activity-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-left: 8px;
        }

        .activity-active {
            background: #34c759;
            box-shadow: 0 0 0 2px rgba(52, 199, 89, 0.3);
        }

        .activity-inactive {
            background: #ff9500;
            box-shadow: 0 0 0 2px rgba(255, 149, 0, 0.3);
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin: 30px 0;
            flex-wrap: wrap;
        }

        button {
            background: #007aff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0, 122, 255, 0.2);
            font-family: inherit;
        }

        button:hover {
            background: #0056d6;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
        }

        button:active {
            transform: translateY(0px);
            box-shadow: 0 2px 4px rgba(0, 122, 255, 0.2);
        }

        button.secondary {
            background: #f6f6f6;
            color: #1d1d1f;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        button.secondary:hover {
            background: #e5e5e7;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .range-label {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 11px;
            font-weight: 500;
            color: #86868b;
        }

        .full-width {
            grid-column: 1 / -1;
        }

        @media (max-width: 1024px) {
            .main-layout {
                grid-template-columns: 1fr 1fr;
            }
        }

        @media (max-width: 768px) {
            .main-layout {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 2.5rem;
            }

            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .radar-container {
                height: 400px;
            }

            .controls {
                flex-direction: column;
                align-items: center;
            }

            button {
                width: 200px;
            }
        }

        @media (max-width: 480px) {
            .container {
                padding: 16px;
            }

            .header {
                padding: 20px 0;
            }

            .header h1 {
                font-size: 2rem;
            }

            .panel {
                padding: 16px;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ADS-B 可视化系统</h1>
            <p class="subtitle">实时航空器监控与追踪</p>
            <div id="status" class="status offline">
                <div class="status-dot"></div>
                <span id="status-text">检查中...</span>
            </div>
        </div>

        <div class="main-layout">
            <!-- 统计面板 -->
            <div class="panel">
                <h3><span class="icon">📊</span>实时统计</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="total-aircraft">0</div>
                        <div class="stat-label">总飞机数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="active-aircraft">0</div>
                        <div class="stat-label">活跃飞机</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="update-time">--:--</div>
                        <div class="stat-label">最后更新</div>
                    </div>
                </div>
            </div>

            <!-- 高度分布面板 -->
            <div class="panel">
                <h3><span class="icon">📈</span>高度分布</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="low-alt">0</div>
                        <div class="stat-label">低空</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="med-alt">0</div>
                        <div class="stat-label">中空</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="high-alt">0</div>
                        <div class="stat-label">高空</div>
                    </div>
                </div>
            </div>

            <!-- 系统信息面板 -->
            <div class="panel">
                <h3><span class="icon">⚙️</span>系统信息</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="data-rate">0</div>
                        <div class="stat-label">数据速率</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="coverage">100km</div>
                        <div class="stat-label">覆盖范围</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="uptime">--:--</div>
                        <div class="stat-label">运行时间</div>
                    </div>
                </div>
            </div>

            <!-- 雷达视图 -->
            <div class="panel radar-section">
                <h3><span class="icon">📡</span>雷达视图 - 天津区域</h3>
                <div class="radar-container" id="radar-container">
                    <div class="radar-grid"></div>
                    <div class="radar-crosshair"></div>
                    <div id="radar-aircraft"></div>
                </div>
                <div style="text-align: center; margin-top: 12px; font-size: 12px; color: #86868b;">
                    <span style="color: #34c759;">●</span> 低空 (0-10k ft) &nbsp;&nbsp;
                    <span style="color: #ff9500;">●</span> 中空 (10-33k ft) &nbsp;&nbsp;
                    <span style="color: #ff3b30;">●</span> 高空 (33k+ ft)
                </div>
            </div>

            <!-- 飞机列表 -->
            <div class="panel aircraft-list-section">
                <h3><span class="icon">✈️</span>飞机列表</h3>
                <div id="aircraft-count" style="margin-bottom: 16px; font-size: 14px; color: #86868b;">正在加载...</div>
                <div class="aircraft-list" id="aircraft-data"></div>
            </div>
        </div>

        <div class="controls">
            <button onclick="refreshData()">刷新数据</button>
            <button class="secondary" onclick="window.open('/api/aircraft/', '_blank')">查看 API</button>
            <button onclick="toggleAutoRefresh()"><span id="auto-refresh-text">启用自动刷新</span></button>
        </div>
    </div>
    
    <script>
        let autoRefreshEnabled = false;
        let autoRefreshInterval = null;
        let aircraftData = [];
        let startTime = new Date();

        // 移除标签页切换功能，所有内容在一个页面显示

        function refreshData() {
            fetch('/api/aircraft/')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').className = 'status online';
                    document.getElementById('status-text').textContent = `系统正常运行`;

                    aircraftData = Object.values(data.aircraft);
                    updateStatistics();
                    updateAircraftList();
                    updateRadarView();
                    updateSystemInfo();

                    // 更新时间
                    const now = new Date();
                    document.getElementById('update-time').textContent =
                        now.getHours().toString().padStart(2, '0') + ':' +
                        now.getMinutes().toString().padStart(2, '0');
                })
                .catch(error => {
                    console.error('数据获取失败:', error);
                    document.getElementById('status').className = 'status offline';
                    document.getElementById('status-text').textContent = '连接失败';
                    document.getElementById('aircraft-count').textContent = '无法获取数据';
                });
        }

        function updateSystemInfo() {
            // 计算数据速率 (飞机数/分钟)
            const dataRate = aircraftData.length;
            document.getElementById('data-rate').textContent = dataRate + '/min';

            // 计算运行时间
            const now = new Date();
            const uptime = Math.floor((now - startTime) / 1000 / 60); // 分钟
            const hours = Math.floor(uptime / 60);
            const minutes = uptime % 60;
            document.getElementById('uptime').textContent =
                hours.toString().padStart(2, '0') + ':' +
                minutes.toString().padStart(2, '0');
        }

        function updateStatistics() {
            const total = aircraftData.length;
            const active = aircraftData.filter(a => a.time_diff < 300).length; // 5分钟内活跃

            let lowAlt = 0, medAlt = 0, highAlt = 0;
            aircraftData.forEach(aircraft => {
                if (aircraft.alt < 10000) lowAlt++;
                else if (aircraft.alt < 33000) medAlt++;
                else highAlt++;
            });

            // 使用更平滑的动画效果
            animateNumber('total-aircraft', total);
            animateNumber('active-aircraft', active);
            animateNumber('low-alt', lowAlt);
            animateNumber('med-alt', medAlt);
            animateNumber('high-alt', highAlt);
        }

        function animateNumber(elementId, targetValue) {
            const element = document.getElementById(elementId);
            const currentValue = parseInt(element.textContent) || 0;

            if (currentValue === targetValue) return;

            // 使用更平滑的动画
            const duration = 800; // 动画持续时间
            const startTime = performance.now();
            const startValue = currentValue;

            function animate(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // 使用缓动函数
                const easeOutQuart = 1 - Math.pow(1 - progress, 4);
                const currentNumber = Math.round(startValue + (targetValue - startValue) * easeOutQuart);

                element.textContent = currentNumber;

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    element.textContent = targetValue;
                }
            }

            requestAnimationFrame(animate);
        }

        function updateAircraftList() {
            const activeCount = aircraftData.filter(a => a.time_diff < 300).length;
            document.getElementById('aircraft-count').textContent =
                `${aircraftData.length} 架飞机 · ${activeCount} 架活跃`;

            // 按活跃状态和高度排序
            const sortedAircraft = aircraftData.sort((a, b) => {
                const aActive = a.time_diff < 300 ? 0 : 1;
                const bActive = b.time_diff < 300 ? 0 : 1;
                if (aActive !== bActive) return aActive - bActive;
                return b.alt - a.alt; // 高度降序
            });

            let html = '';
            sortedAircraft.forEach(aircraft => {
                const isActive = aircraft.time_diff < 300;
                const altitudeCategory = aircraft.alt < 10000 ? '低空' :
                                       aircraft.alt < 33000 ? '中空' : '高空';
                const altitudeBadgeClass = aircraft.alt < 10000 ? 'altitude-low' :
                                          aircraft.alt < 33000 ? 'altitude-med' : 'altitude-high';

                const timeAgo = Math.round(aircraft.time_diff);
                const timeText = timeAgo < 60 ? `${timeAgo}秒前` :
                               timeAgo < 3600 ? `${Math.round(timeAgo/60)}分钟前` :
                               `${Math.round(timeAgo/3600)}小时前`;

                // 计算距离观测点的距离 (天津: 39.1, 117.2)
                const observerLat = 39.1;
                const observerLon = 117.2;
                const distance = calculateDistance(observerLat, observerLon, aircraft.lat, aircraft.lon);

                // 计算速度 (如果有历史数据)
                const speed = aircraft.speed || calculateSpeed(aircraft);

                html += `<div class="aircraft-item">
                    <div class="aircraft-header">
                        <div class="icao">${aircraft.icao}</div>
                        <div class="aircraft-status">
                            <div class="altitude-badge ${altitudeBadgeClass}">${altitudeCategory}</div>
                            <div class="activity-indicator ${isActive ? 'activity-active' : 'activity-inactive'}"></div>
                        </div>
                    </div>
                    <div class="aircraft-details">
                        <div class="detail-group">
                            <div class="detail-item">
                                <span class="detail-label">坐标</span>
                                <span class="detail-value">${aircraft.lat.toFixed(4)}, ${aircraft.lon.toFixed(4)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">高度</span>
                                <span class="detail-value">${aircraft.alt.toLocaleString()} ft</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">距离</span>
                                <span class="detail-value">
                                    <span class="distance-indicator">📍 ${distance.toFixed(1)} km</span>
                                </span>
                            </div>
                        </div>
                        <div class="detail-group">
                            <div class="detail-item">
                                <span class="detail-label">速度</span>
                                <span class="detail-value">${speed ? speed.toFixed(0) + ' km/h' : 'N/A'}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">时间</span>
                                <span class="detail-value">${aircraft.timestamp.split(' ')[1]}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">更新</span>
                                <span class="detail-value">${timeText}</span>
                            </div>
                        </div>
                    </div>
                </div>`;
            });
            document.getElementById('aircraft-data').innerHTML = html;
        }

        function calculateDistance(lat1, lon1, lat2, lon2) {
            const R = 6371; // 地球半径 (km)
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                      Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }

        function calculateSpeed(aircraft) {
            // 简单的速度估算，基于位置变化
            // 实际应用中需要历史数据来计算
            if (aircraft.prevLat && aircraft.prevLon && aircraft.prevTime) {
                const distance = calculateDistance(aircraft.prevLat, aircraft.prevLon, aircraft.lat, aircraft.lon);
                const timeDiff = (new Date(aircraft.timestamp) - new Date(aircraft.prevTime)) / 1000 / 3600; // 小时
                return distance / timeDiff; // km/h
            }
            return null;
        }

        function updateRadarView() {
            const container = document.getElementById('radar-aircraft');
            if (!container) return;

            container.innerHTML = '';

            // 计算显示范围 (以天津为中心，约100km范围)
            const centerLat = 39.1;
            const centerLon = 117.2;
            const range = 1.0; // 约100km

            // 获取容器尺寸
            const radarContainer = document.getElementById('radar-container');
            const containerRect = radarContainer.getBoundingClientRect();
            const centerX = containerRect.width / 2;
            const centerY = containerRect.height / 2;
            const radarRadius = Math.min(centerX, centerY) - 20; // 留边距

            aircraftData.forEach(aircraft => {
                // 转换坐标到雷达显示
                const relLat = (aircraft.lat - centerLat) / range;
                const relLon = (aircraft.lon - centerLon) / range;

                // 计算距离中心的距离
                const distance = Math.sqrt(relLat * relLat + relLon * relLon);

                // 只显示范围内的飞机 (圆形范围)
                if (distance <= 1.0) {
                    // 转换到极坐标然后到屏幕坐标
                    const x = centerX + (relLon * radarRadius);
                    const y = centerY - (relLat * radarRadius); // Y轴翻转

                    const dot = document.createElement('div');
                    dot.className = 'aircraft-dot';
                    dot.style.left = x + 'px';
                    dot.style.top = y + 'px';

                    // 根据活跃状态和高度设置颜色和样式
                    const isActive = aircraft.time_diff < 300;
                    let color;

                    if (aircraft.alt < 10000) {
                        color = '#34c759'; // 苹果绿 - 低空
                    } else if (aircraft.alt < 33000) {
                        color = '#ff9500'; // 苹果橙 - 中空
                    } else {
                        color = '#ff3b30'; // 苹果红 - 高空
                    }

                    // 非活跃飞机显示为半透明
                    if (!isActive) {
                        dot.style.opacity = '0.6';
                    }

                    dot.style.backgroundColor = color;

                    // 添加飞机标签
                    const label = document.createElement('div');
                    label.className = 'aircraft-label';
                    label.textContent = aircraft.icao;
                    dot.appendChild(label);

                    // 计算距离
                    const observerLat = 39.1;
                    const observerLon = 117.2;
                    const distance = calculateDistance(observerLat, observerLon, aircraft.lat, aircraft.lon);

                    // 详细信息
                    const timeAgo = Math.round(aircraft.time_diff);
                    const status = isActive ? '活跃' : '非活跃';
                    const altCategory = aircraft.alt < 10000 ? '低空' :
                                       aircraft.alt < 33000 ? '中空' : '高空';

                    // 悬停显示详细信息
                    dot.addEventListener('mouseenter', (e) => {
                        showTooltip(e, aircraft, distance, status, altCategory, timeAgo);
                    });

                    dot.addEventListener('mouseleave', () => {
                        hideTooltip();
                    });

                    dot.addEventListener('mousemove', (e) => {
                        updateTooltipPosition(e);
                    });

                    // 点击显示详细信息弹窗
                    dot.addEventListener('click', () => {
                        showAircraftModal(aircraft, distance, status, altCategory, timeAgo);
                    });

                    container.appendChild(dot);
                }
            });

            // 添加范围标签
            addRangeLabels(container, centerX, centerY, radarRadius);
        }

        function addRangeLabels(container, centerX, centerY, radarRadius) {
            // 清除旧的标签
            container.querySelectorAll('.range-label').forEach(label => label.remove());

            // 添加距离圈标签
            const ranges = [25, 50, 75, 100]; // km
            ranges.forEach((range, index) => {
                const radius = (radarRadius * (index + 1)) / 4;
                const label = document.createElement('div');
                label.className = 'range-label';
                label.style.position = 'absolute';
                label.style.left = (centerX + radius - 12) + 'px';
                label.style.top = (centerY - 8) + 'px';
                label.style.pointerEvents = 'none';
                label.textContent = range + 'km';
                container.appendChild(label);
            });

            // 添加方向标签
            const directions = [
                {text: 'N', x: centerX - 6, y: 8},
                {text: 'E', x: centerX * 2 - 20, y: centerY - 8},
                {text: 'S', x: centerX - 6, y: centerY * 2 - 20},
                {text: 'W', x: 8, y: centerY - 8}
            ];

            directions.forEach(dir => {
                const label = document.createElement('div');
                label.className = 'range-label';
                label.style.position = 'absolute';
                label.style.left = dir.x + 'px';
                label.style.top = dir.y + 'px';
                label.style.pointerEvents = 'none';
                label.style.textAlign = 'center';
                label.style.width = '12px';
                label.style.fontWeight = '600';
                label.textContent = dir.text;
                container.appendChild(label);
            });
        }

        function toggleAutoRefresh() {
            autoRefreshEnabled = !autoRefreshEnabled;
            const button = document.getElementById('auto-refresh-text');

            if (autoRefreshEnabled) {
                button.textContent = '停止自动刷新';
                button.parentElement.style.background = '#ff9500';
                autoRefreshInterval = setInterval(refreshData, 3000);
                console.log('自动刷新已启用 (3秒间隔)');
            } else {
                button.textContent = '启用自动刷新';
                button.parentElement.style.background = '#007aff';
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
                console.log('自动刷新已停止');
            }
        }

        // 窗口大小改变时重新计算雷达视图
        window.addEventListener('resize', () => {
            setTimeout(updateRadarView, 100);
        });

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        refreshData();
                        break;
                }
            }
        });

        // 初始化
        console.log('ADS-B 可视化系统初始化中...');
        refreshData();

        // 延迟启用自动刷新，确保首次数据加载完成
        setTimeout(() => {
            toggleAutoRefresh();
            console.log('系统初始化完成');
        }, 2000);

        // 添加页面可见性检测，页面不可见时停止刷新
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (autoRefreshEnabled && autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    console.log('页面不可见，暂停自动刷新');
                }
            } else {
                if (autoRefreshEnabled && !autoRefreshInterval) {
                    autoRefreshInterval = setInterval(refreshData, 3000);
                    console.log('页面可见，恢复自动刷新');
                    refreshData(); // 立即刷新一次
                }
            }
        });

        let tooltip = null;

        function showTooltip(event, aircraft, distance, status, altCategory, timeAgo) {
            hideTooltip(); // 先隐藏之前的提示

            tooltip = document.createElement('div');
            tooltip.className = 'aircraft-tooltip';
            tooltip.innerHTML = `
                <div style="font-weight: 600; margin-bottom: 6px;">${aircraft.icao}</div>
                <div>高度: ${aircraft.alt.toLocaleString()} ft (${altCategory})</div>
                <div>坐标: ${aircraft.lat.toFixed(4)}, ${aircraft.lon.toFixed(4)}</div>
                <div>距离: ${distance.toFixed(1)} km</div>
                <div>状态: ${status} (${timeAgo}秒前)</div>
                <div style="margin-top: 6px; font-size: 11px; color: #ccc;">点击查看详细信息</div>
            `;

            document.body.appendChild(tooltip);
            updateTooltipPosition(event);

            // 显示动画
            setTimeout(() => {
                tooltip.style.opacity = '1';
            }, 10);
        }

        function hideTooltip() {
            if (tooltip) {
                tooltip.style.opacity = '0';
                setTimeout(() => {
                    if (tooltip && tooltip.parentNode) {
                        tooltip.parentNode.removeChild(tooltip);
                    }
                    tooltip = null;
                }, 300);
            }
        }

        function updateTooltipPosition(event) {
            if (!tooltip) return;

            const x = event.clientX;
            const y = event.clientY;
            const tooltipRect = tooltip.getBoundingClientRect();
            const windowWidth = window.innerWidth;
            const windowHeight = window.innerHeight;

            let left = x + 10;
            let top = y - tooltipRect.height - 10;

            // 防止超出屏幕边界
            if (left + tooltipRect.width > windowWidth) {
                left = x - tooltipRect.width - 10;
            }
            if (top < 0) {
                top = y + 10;
            }

            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
        }

        function showAircraftModal(aircraft, distance, status, altCategory, timeAgo) {
            const speed = aircraft.speed || calculateSpeed(aircraft);
            const modalContent = `
飞机详细信息

ICAO代码: ${aircraft.icao}
飞行高度: ${aircraft.alt.toLocaleString()} ft (${altCategory})
经纬度坐标: ${aircraft.lat.toFixed(6)}, ${aircraft.lon.toFixed(6)}
距离观测点: ${distance.toFixed(2)} km
飞行速度: ${speed ? speed.toFixed(0) + ' km/h' : '数据不可用'}
数据时间: ${aircraft.timestamp}
活跃状态: ${status} (${timeAgo}秒前)

${aircraft.ecef_x ? `ECEF坐标: X=${aircraft.ecef_x.toFixed(0)}, Y=${aircraft.ecef_y.toFixed(0)}, Z=${aircraft.ecef_z.toFixed(0)}` : ''}
${aircraft.enu_e ? `ENU坐标: E=${aircraft.enu_e.toFixed(0)}, N=${aircraft.enu_n.toFixed(0)}, U=${aircraft.enu_u.toFixed(0)}` : ''}
            `;

            alert(modalContent);
        }
    </script>
</body>
</html>'''
            
            self.wfile.write(html.encode('utf-8'))

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8000), MinimalHandler)
    server.serve_forever()
