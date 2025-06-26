#!/usr/bin/env python3
"""
WebSocket处理器模块
负责实时数据推送和客户端通信
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set
import threading

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.connections: Set = set()
        self.aircraft_data = {}
        self.last_broadcast = datetime.now()
        self.broadcast_interval = 1.0  # 秒
        
    def add_connection(self, websocket):
        """添加WebSocket连接"""
        self.connections.add(websocket)
        logger.info(f"新的WebSocket连接，当前连接数: {len(self.connections)}")
    
    def remove_connection(self, websocket):
        """移除WebSocket连接"""
        self.connections.discard(websocket)
        logger.info(f"WebSocket连接断开，当前连接数: {len(self.connections)}")
    
    def broadcast_aircraft_data(self, aircraft_data: Dict):
        """广播飞机数据到所有连接的客户端"""
        if not self.connections:
            return
        
        # 检查广播间隔
        now = datetime.now()
        if (now - self.last_broadcast).total_seconds() < self.broadcast_interval:
            return
        
        self.aircraft_data = aircraft_data
        self.last_broadcast = now
        
        # 准备广播数据
        message = {
            'type': 'aircraft_update',
            'timestamp': now.isoformat(),
            'count': len(aircraft_data),
            'aircraft': aircraft_data
        }
        
        # 异步广播（简化版本，实际应该使用异步框架）
        self._broadcast_sync(json.dumps(message))
    
    def _broadcast_sync(self, message: str):
        """同步广播消息（简化实现）"""
        # 这里是简化的实现，实际应该使用Django Channels或其他异步框架
        logger.debug(f"广播消息到 {len(self.connections)} 个连接")
        
        # 移除无效连接
        invalid_connections = set()
        for connection in self.connections:
            try:
                # 这里应该是实际的WebSocket发送逻辑
                # connection.send(message)
                pass
            except Exception as e:
                logger.warning(f"发送消息失败: {e}")
                invalid_connections.add(connection)
        
        # 清理无效连接
        self.connections -= invalid_connections
    
    def broadcast_statistics(self, stats: Dict):
        """广播统计信息"""
        if not self.connections:
            return
        
        message = {
            'type': 'statistics_update',
            'timestamp': datetime.now().isoformat(),
            'statistics': stats
        }
        
        self._broadcast_sync(json.dumps(message))
    
    def broadcast_alert(self, alert_type: str, message: str, aircraft_icao: str = None):
        """广播告警信息"""
        if not self.connections:
            return
        
        alert_message = {
            'type': 'alert',
            'alert_type': alert_type,
            'message': message,
            'aircraft_icao': aircraft_icao,
            'timestamp': datetime.now().isoformat()
        }
        
        self._broadcast_sync(json.dumps(alert_message))
    
    def send_aircraft_detail(self, websocket, icao: str, aircraft_data: Dict):
        """发送特定飞机的详细信息"""
        message = {
            'type': 'aircraft_detail',
            'icao': icao,
            'aircraft': aircraft_data,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # websocket.send(json.dumps(message))
            logger.debug(f"发送飞机详情: {icao}")
        except Exception as e:
            logger.error(f"发送飞机详情失败: {e}")
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.connections)
    
    def get_status(self) -> Dict:
        """获取WebSocket管理器状态"""
        return {
            'connections': len(self.connections),
            'last_broadcast': self.last_broadcast.isoformat(),
            'aircraft_count': len(self.aircraft_data),
            'broadcast_interval': self.broadcast_interval
        }


class MockWebSocketConnection:
    """模拟WebSocket连接（用于测试）"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.connected = True
        self.messages = []
    
    def send(self, message: str):
        """模拟发送消息"""
        if self.connected:
            self.messages.append({
                'timestamp': datetime.now().isoformat(),
                'message': message
            })
            print(f"[{self.client_id}] 收到消息: {message[:100]}...")
        else:
            raise Exception("连接已断开")
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
    
    def get_messages(self) -> List[Dict]:
        """获取接收到的消息"""
        return self.messages.copy()


# Django Channels WebSocket Consumer (示例)
class AircraftWebSocketConsumer:
    """
    Django Channels WebSocket消费者
    实际使用时需要安装channels并配置ASGI
    """
    
    def __init__(self):
        self.websocket_manager = WebSocketManager()
    
    async def connect(self):
        """WebSocket连接建立"""
        await self.accept()
        self.websocket_manager.add_connection(self)
        
        # 发送初始数据
        await self.send_initial_data()
    
    async def disconnect(self, close_code):
        """WebSocket连接断开"""
        self.websocket_manager.remove_connection(self)
    
    async def receive(self, text_data):
        """接收客户端消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_aircraft_detail':
                icao = data.get('icao')
                await self.send_aircraft_detail(icao)
            
            elif message_type == 'set_filter':
                # 处理过滤器设置
                await self.handle_filter_update(data)
            
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的JSON格式'
            }))
    
    async def send_initial_data(self):
        """发送初始数据"""
        message = {
            'type': 'initial_data',
            'aircraft': self.websocket_manager.aircraft_data,
            'timestamp': datetime.now().isoformat()
        }
        await self.send(text_data=json.dumps(message))
    
    async def send_aircraft_detail(self, icao: str):
        """发送飞机详情"""
        # 这里应该从数据处理器获取详细信息
        aircraft_data = self.websocket_manager.aircraft_data.get(icao)
        
        if aircraft_data:
            message = {
                'type': 'aircraft_detail',
                'icao': icao,
                'aircraft': aircraft_data,
                'timestamp': datetime.now().isoformat()
            }
            await self.send(text_data=json.dumps(message))
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'未找到飞机: {icao}'
            }))
    
    async def handle_filter_update(self, data):
        """处理过滤器更新"""
        # 实现过滤器逻辑
        filters = data.get('filters', {})
        
        # 应用过滤器并发送更新的数据
        filtered_aircraft = self._apply_filters(
            self.websocket_manager.aircraft_data, 
            filters
        )
        
        message = {
            'type': 'filtered_aircraft',
            'aircraft': filtered_aircraft,
            'filters': filters,
            'timestamp': datetime.now().isoformat()
        }
        await self.send(text_data=json.dumps(message))
    
    def _apply_filters(self, aircraft_data: Dict, filters: Dict) -> Dict:
        """应用过滤器"""
        filtered_data = {}
        
        min_alt = filters.get('min_altitude', 0)
        max_alt = filters.get('max_altitude', 50000)
        max_distance = filters.get('max_distance', float('inf'))
        
        for icao, aircraft in aircraft_data.items():
            # 高度过滤
            if not (min_alt <= aircraft['altitude'] <= max_alt):
                continue
            
            # 距离过滤
            enu_e = aircraft.get('enu_e', 0)
            enu_n = aircraft.get('enu_n', 0)
            distance = (enu_e**2 + enu_n**2)**0.5
            
            if distance > max_distance:
                continue
            
            filtered_data[icao] = aircraft
        
        return filtered_data


def test_websocket_manager():
    """测试WebSocket管理器"""
    print("测试WebSocket管理器...")
    
    manager = WebSocketManager()
    
    # 创建模拟连接
    conn1 = MockWebSocketConnection("client1")
    conn2 = MockWebSocketConnection("client2")
    
    manager.add_connection(conn1)
    manager.add_connection(conn2)
    
    print(f"连接数: {manager.get_connection_count()}")
    
    # 模拟飞机数据
    aircraft_data = {
        'CA1234': {
            'icao': 'CA1234',
            'latitude': 39.9,
            'longitude': 116.4,
            'altitude': 35000,
            'enu_e': 1000,
            'enu_n': 2000,
            'enu_u': 5000
        }
    }
    
    # 广播数据
    manager.broadcast_aircraft_data(aircraft_data)
    
    # 广播统计信息
    stats = {'total_aircraft': 1, 'avg_altitude': 35000}
    manager.broadcast_statistics(stats)
    
    # 广播告警
    manager.broadcast_alert('proximity', '飞机接近告警', 'CA1234')
    
    # 断开一个连接
    conn1.disconnect()
    manager.remove_connection(conn1)
    
    print(f"断开后连接数: {manager.get_connection_count()}")
    print(f"管理器状态: {manager.get_status()}")


if __name__ == '__main__':
    test_websocket_manager()
