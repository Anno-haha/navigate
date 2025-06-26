# ADS-B 动态可视化系统

## 🎯 项目概述

基于Django的实时航空数据可视化平台，将ADS-B接收器获取的飞机位置数据转换为动态3D地球和2D雷达显示。系统以北京上空(116.4°E, 39.9°N, 10000m)为参考点，提供实时飞行监控、历史轨迹回放和飞机状态分析功能。

## ✨ 主要功能

### 🌍 3D地球可视化
- 真实地球模型渲染
- 实时飞机位置显示
- 飞行轨迹追踪
- 高度分层显示（颜色编码）
- 交互式控制面板

### 📡 2D雷达监控
- 极坐标雷达显示
- 距离环和方位指示
- 实时扫描效果
- 飞机轨迹回放
- 可调节雷达范围

### 📊 数据分析
- 实时统计仪表盘
- 飞机数量和分布
- 高度/速度分析
- 历史数据查询

### 🔄 实时通信
- WebSocket实时数据推送
- 自动数据更新
- 连接状态监控
- 告警系统

## 🏗️ 系统架构

```
nav.py (数据采集) → ADS-B数据 → 坐标转换 → Django后端 → WebSocket → 前端可视化
                                    ↓
                               SQLite数据库
```

### 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **主控制器** | `ADS_B_visual.py` | Django应用和系统协调 |
| **坐标转换** | `coord_converter.py` | LLA→ECEF→ENU转换 |
| **数据处理** | `data_processor.py` | ADS-B数据解析和缓存 |
| **WebSocket** | `websocket_handler.py` | 实时数据推送 |
| **数据库** | `database_manager.py` | 数据存储和查询 |

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- 2GB+ 内存
- 1GB+ 磁盘空间
- 现代浏览器（支持WebGL）

### 2. 安装依赖
```bash
# 自动安装所有依赖
python install_requirements.py

# 或手动安装
pip install django channels redis celery numpy
```

### 3. 启动系统
```bash
# 完整启动（推荐）
python start_visualization.py

# 快速启动
python start_visualization.py --quick

# 直接启动
python ADS_B_visual.py
```

### 4. 访问界面
- **3D地球视图**: http://127.0.0.1:8000/
- **2D雷达视图**: http://127.0.0.1:8000/radar/
- **API接口**: http://127.0.0.1:8000/api/aircraft/

## 📁 项目结构

```
navigate/
├── ADS_B_visual.py          # 主应用程序
├── nav.py                   # ADS-B数据采集
├── coord_converter.py       # 坐标转换器
├── data_processor.py        # 数据处理器
├── websocket_handler.py     # WebSocket管理
├── database_manager.py      # 数据库管理
├── start_visualization.py   # 启动脚本
├── install_requirements.py # 依赖安装
├── templates/               # HTML模板
│   ├── base.html           # 基础模板
│   ├── index.html          # 3D地球视图
│   └── radar.html          # 2D雷达视图
├── static/                  # 静态文件
└── adsb_visual.db          # SQLite数据库
```

## 🔧 配置说明

### 参考点设置
```python
# coord_converter.py
REF_LATITUDE = 39.9    # 北京纬度
REF_LONGITUDE = 116.4  # 北京经度
REF_ALTITUDE = 10000.0 # 参考高度(米)
```

### 数据源配置
```python
# data_processor.py
log_file_path = 'adsb_decoded.log'  # nav.py输出文件
cache_timeout = 300  # 数据缓存时间(秒)
```

### 可视化参数
```javascript
// 3D地球
camera.position.set(0, 0, 50);  // 相机位置
earth.rotation.y += 0.002;      // 自动旋转速度

// 2D雷达
radarRange = 100;  // 雷达范围(km)
sweepAngle += 2;   // 扫描速度
```

## 📊 API接口

### 获取飞机数据
```http
GET /api/aircraft/
GET /api/aircraft/?altitude_min=0&altitude_max=50000
```

### 获取飞机详情
```http
GET /api/aircraft/{icao}/
```

### 获取统计信息
```http
GET /api/statistics/
```

### 响应格式
```json
{
  "status": "success",
  "count": 5,
  "aircraft": {
    "CA1234": {
      "icao": "CA1234",
      "latitude": 39.9,
      "longitude": 116.4,
      "altitude": 35000,
      "enu_e": 1000.0,
      "enu_n": 2000.0,
      "enu_u": 5000.0,
      "timestamp": "2025-06-26T19:30:00"
    }
  }
}
```

## 🎨 界面功能

### 3D地球视图
- **鼠标控制**: 拖拽旋转，滚轮缩放
- **高度过滤**: 按英尺范围过滤飞机
- **显示选项**: 轨迹/标签/自动旋转开关
- **飞机列表**: 实时飞机信息面板
- **统计信息**: 数量/高度/距离统计

### 2D雷达视图
- **雷达范围**: 20/50/100/200km可选
- **扫描效果**: 模拟雷达扫描线
- **轨迹显示**: 飞机历史轨迹
- **点击详情**: 点击飞机查看详细信息
- **高度图例**: 颜色编码说明

## 🔍 故障排除

### 常见问题

1. **无飞机数据显示**
   - 检查nav.py是否运行
   - 确认adsb_decoded.log文件存在且有数据
   - 检查串口连接状态

2. **页面加载缓慢**
   - 检查网络连接
   - 清除浏览器缓存
   - 确认系统内存充足

3. **WebSocket连接失败**
   - 检查防火墙设置
   - 确认端口8000未被占用
   - 重启Django服务

4. **3D渲染问题**
   - 更新浏览器到最新版本
   - 检查WebGL支持
   - 降低渲染质量设置

### 调试模式
```bash
# 启用Django调试模式
export DJANGO_DEBUG=True
python ADS_B_visual.py

# 查看详细日志
tail -f adsb_decoded.log
```

## 🔮 扩展功能

### 添加新坐标系
```python
# coord_converter.py
def lla_to_custom(self, lat, lon, alt):
    # 实现自定义坐标转换
    pass
```

### 自定义可视化
```javascript
// 添加新的飞机模型
function createCustomAircraft(aircraft) {
    // Three.js自定义几何体
}
```

### 数据导出
```python
# database_manager.py
def export_to_format(self, format='json'):
    # 支持JSON/CSV/KML等格式
```

## 📄 许可证

本项目基于MIT许可证开源。

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📞 技术支持

- 问题反馈：GitHub Issues
- 技术讨论：项目Wiki
- 文档更新：README.md

---

**享受实时航空数据可视化的乐趣！** ✈️🌍📡
