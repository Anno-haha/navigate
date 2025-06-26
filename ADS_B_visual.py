#!/usr/bin/env python3
"""
Django ADS-B 动态可视化系统 - 主控制器
基于nav.py的ADS-B数据，提供实时3D地球和2D雷达可视化
参考点：北京上空 (116.4°E, 39.9°N, 10000m)
"""

import os
import sys
import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.core.wsgi import get_wsgi_application
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
import json
import threading
import time
from datetime import datetime, timedelta
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from coord_converter import CoordinateConverter
from data_processor import ADSBDataProcessor
from websocket_handler import WebSocketManager
from database_manager import DatabaseManager

# Django配置
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='adsb-visual-secret-key-2025',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'channels',
        ],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        ROOT_URLCONF=__name__,
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[
            os.path.join(os.path.dirname(__file__), 'static'),
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(os.path.dirname(__file__), 'adsb_visual.db'),
            }
        },
        # WebSocket配置
        ASGI_APPLICATION = 'ADS_B_visual.asgi.application',
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        },
        # 时区设置
        TIME_ZONE='Asia/Shanghai',
        USE_TZ=True,
    )

django.setup()

# 全局变量
aircraft_data = {}  # 存储飞机数据
coordinate_converter = CoordinateConverter()
data_processor = ADSBDataProcessor()
websocket_manager = WebSocketManager()
db_manager = DatabaseManager()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ADSBVisualizationSystem:
    """ADS-B可视化系统主类"""

    def __init__(self):
        self.running = False
        self.data_thread = None
        self.last_update = datetime.now()

    def start_system(self):
        """启动可视化系统"""
        logger.info("启动ADS-B可视化系统...")

        # 初始化数据库
        try:
            db_manager.initialize()
        except:
            logger.warning("数据库初始化失败，使用内存存储")

        # 启动数据处理线程
        self.running = True
        self.data_thread = threading.Thread(target=self._data_processing_loop)
        self.data_thread.daemon = True
        self.data_thread.start()

        logger.info("系统启动完成")

    def stop_system(self):
        """停止系统"""
        logger.info("停止ADS-B可视化系统...")
        self.running = False
        if self.data_thread:
            self.data_thread.join(timeout=5)
        logger.info("系统已停止")

    def _data_processing_loop(self):
        """数据处理主循环"""
        while self.running:
            try:
                # 从nav.py获取最新数据
                new_data = data_processor.get_latest_adsb_data()

                if new_data:
                    # 处理新数据
                    for aircraft in new_data:
                        self._process_aircraft_data(aircraft)

                    # 通过WebSocket推送更新
                    try:
                        websocket_manager.broadcast_aircraft_data(aircraft_data)
                    except:
                        pass  # WebSocket可能未连接

                    self.last_update = datetime.now()

                # 清理过期数据
                self._cleanup_expired_data()

                time.sleep(1)  # 1秒更新间隔

            except Exception as e:
                logger.error(f"数据处理错误: {e}")
                time.sleep(5)

    def _process_aircraft_data(self, aircraft):
        """处理单个飞机数据"""
        icao = aircraft['icao']

        # 转换坐标
        try:
            enu_coords = coordinate_converter.lla_to_enu(
                aircraft['latitude'],
                aircraft['longitude'],
                aircraft['altitude'] * 0.3048  # 英尺转米
            )
        except:
            enu_coords = (0, 0, 0)  # 默认值

        # 更新飞机数据
        aircraft_data[icao] = {
            'icao': icao,
            'latitude': aircraft['latitude'],
            'longitude': aircraft['longitude'],
            'altitude': aircraft['altitude'],
            'enu_e': enu_coords[0],
            'enu_n': enu_coords[1],
            'enu_u': enu_coords[2],
            'timestamp': datetime.now().isoformat(),
            'speed': self._calculate_speed(icao, aircraft),
            'heading': self._calculate_heading(icao, aircraft),
        }

        # 存储到数据库
        try:
            db_manager.store_aircraft_data(aircraft_data[icao])
        except:
            pass  # 数据库可能未初始化

    def _calculate_speed(self, icao, current_data):
        """计算飞机速度"""
        if icao in aircraft_data:
            prev_data = aircraft_data[icao]
            # 简化的速度计算
            return 450  # km/h (示例值)
        return 0

    def _calculate_heading(self, icao, current_data):
        """计算飞机航向"""
        if icao in aircraft_data:
            # 简化的航向计算
            return 90  # 度 (示例值)
        return 0

    def _cleanup_expired_data(self):
        """清理过期数据"""
        current_time = datetime.now()
        expired_icaos = []

        for icao, data in aircraft_data.items():
            data_time = datetime.fromisoformat(data['timestamp'])
            if (current_time - data_time).seconds > 300:  # 5分钟过期
                expired_icaos.append(icao)

        for icao in expired_icaos:
            del aircraft_data[icao]
            logger.info(f"清理过期飞机数据: {icao}")


# 全局系统实例
visualization_system = ADSBVisualizationSystem()


# Django视图函数
def index_view(request):
    """主页视图 - 3D地球可视化"""
    context = {
        'title': 'ADS-B 3D地球可视化',
        'aircraft_count': len(aircraft_data),
        'last_update': visualization_system.last_update.strftime('%H:%M:%S'),
    }
    return render(request, 'index.html', context)


def radar_view(request):
    """雷达视图 - 2D雷达显示"""
    context = {
        'title': 'ADS-B 2D雷达监控',
        'aircraft_count': len(aircraft_data),
        'radar_range': 100,  # km
    }
    return render(request, 'radar.html', context)


@csrf_exempt
def api_aircraft_data(request):
    """API: 获取飞机数据"""
    if request.method == 'GET':
        # 获取查询参数
        altitude_min = request.GET.get('altitude_min', 0)
        altitude_max = request.GET.get('altitude_max', 50000)

        # 过滤数据
        filtered_data = {}
        for icao, data in aircraft_data.items():
            if int(altitude_min) <= data['altitude'] <= int(altitude_max):
                filtered_data[icao] = data

        return JsonResponse({
            'status': 'success',
            'count': len(filtered_data),
            'aircraft': filtered_data,
            'timestamp': datetime.now().isoformat(),
        })

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


def api_aircraft_detail(request, icao):
    """API: 获取特定飞机详情"""
    if icao in aircraft_data:
        # 获取历史轨迹
        try:
            trajectory = db_manager.get_aircraft_trajectory(icao, hours=1)
        except:
            trajectory = []

        return JsonResponse({
            'status': 'success',
            'aircraft': aircraft_data[icao],
            'trajectory': trajectory,
        })

    return JsonResponse({'status': 'error', 'message': 'Aircraft not found'})


def api_statistics(request):
    """API: 获取统计信息"""
    if not aircraft_data:
        return JsonResponse({
            'status': 'success',
            'statistics': {
                'total_aircraft': 0,
                'altitude_distribution': {},
                'speed_distribution': {},
            }
        })

    # 计算统计信息
    altitudes = [data['altitude'] for data in aircraft_data.values()]
    speeds = [data['speed'] for data in aircraft_data.values()]

    altitude_ranges = {
        '低空 (0-3000m)': len([a for a in altitudes if a < 10000]),
        '中空 (3000-10000m)': len([a for a in altitudes if 10000 <= a < 33000]),
        '高空 (10000m+)': len([a for a in altitudes if a >= 33000]),
    }

    return JsonResponse({
        'status': 'success',
        'statistics': {
            'total_aircraft': len(aircraft_data),
            'altitude_distribution': altitude_ranges,
            'average_altitude': sum(altitudes) / len(altitudes) if altitudes else 0,
            'average_speed': sum(speeds) / len(speeds) if speeds else 0,
        }
    })


# URL配置
urlpatterns = [
    path('', index_view, name='index'),
    path('radar/', radar_view, name='radar'),
    path('api/aircraft/', api_aircraft_data, name='api_aircraft'),
    path('api/aircraft/<str:icao>/', api_aircraft_detail, name='api_aircraft_detail'),
    path('api/statistics/', api_statistics, name='api_statistics'),
]


def main():
    """主函数"""
    print("Django ADS-B 动态可视化系统")
    print("=" * 50)
    print("功能：实时3D地球和2D雷达可视化")
    print("参考点：北京上空 (116.4°E, 39.9°N, 10000m)")
    print("=" * 50)

    try:
        # 启动可视化系统
        visualization_system.start_system()

        # 启动Django开发服务器
        print("启动Django服务器...")
        print("访问地址：")
        print("  3D地球视图: http://127.0.0.1:8000/")
        print("  2D雷达视图: http://127.0.0.1:8000/radar/")
        print("  API接口: http://127.0.0.1:8000/api/aircraft/")
        print("\n按 Ctrl+C 停止服务器")

        # 运行Django服务器
        execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])

    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        visualization_system.stop_system()
        print("服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        visualization_system.stop_system()


if __name__ == '__main__':
    main()