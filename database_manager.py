#!/usr/bin/env python3
"""
数据库管理器模块
负责飞机数据的存储和查询
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = 'adsb_visual.db'):
        self.db_path = db_path
        self.connection = None
        
    def initialize(self):
        """初始化数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # 使结果可以按列名访问
            
            self._create_tables()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _create_tables(self):
        """创建数据表"""
        cursor = self.connection.cursor()
        
        # 飞机数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aircraft_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                icao TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                altitude INTEGER NOT NULL,
                ecef_x REAL,
                ecef_y REAL,
                ecef_z REAL,
                enu_e REAL,
                enu_n REAL,
                enu_u REAL,
                speed REAL,
                heading REAL,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 飞机轨迹表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aircraft_trajectory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                icao TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                altitude INTEGER NOT NULL,
                enu_e REAL,
                enu_n REAL,
                enu_u REAL,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 统计信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                total_aircraft INTEGER,
                total_messages INTEGER,
                avg_altitude REAL,
                max_altitude INTEGER,
                min_altitude INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_aircraft_icao ON aircraft_data(icao)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_aircraft_timestamp ON aircraft_data(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trajectory_icao ON aircraft_trajectory(icao)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trajectory_timestamp ON aircraft_trajectory(timestamp)')
        
        self.connection.commit()
        logger.info("数据表创建完成")
    
    def store_aircraft_data(self, aircraft_data: Dict):
        """存储飞机数据"""
        try:
            cursor = self.connection.cursor()
            
            # 插入主数据表
            cursor.execute('''
                INSERT INTO aircraft_data 
                (icao, latitude, longitude, altitude, ecef_x, ecef_y, ecef_z, 
                 enu_e, enu_n, enu_u, speed, heading, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                aircraft_data['icao'],
                aircraft_data['latitude'],
                aircraft_data['longitude'],
                aircraft_data['altitude'],
                aircraft_data.get('ecef_x', 0),
                aircraft_data.get('ecef_y', 0),
                aircraft_data.get('ecef_z', 0),
                aircraft_data.get('enu_e', 0),
                aircraft_data.get('enu_n', 0),
                aircraft_data.get('enu_u', 0),
                aircraft_data.get('speed', 0),
                aircraft_data.get('heading', 0),
                aircraft_data['timestamp']
            ))
            
            # 插入轨迹表
            cursor.execute('''
                INSERT INTO aircraft_trajectory 
                (icao, latitude, longitude, altitude, enu_e, enu_n, enu_u, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                aircraft_data['icao'],
                aircraft_data['latitude'],
                aircraft_data['longitude'],
                aircraft_data['altitude'],
                aircraft_data.get('enu_e', 0),
                aircraft_data.get('enu_n', 0),
                aircraft_data.get('enu_u', 0),
                aircraft_data['timestamp']
            ))
            
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"存储飞机数据失败: {e}")
            self.connection.rollback()
    
    def get_aircraft_trajectory(self, icao: str, hours: int = 1) -> List[Dict]:
        """获取飞机轨迹"""
        try:
            cursor = self.connection.cursor()
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT * FROM aircraft_trajectory 
                WHERE icao = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            ''', (icao, start_time.isoformat(), end_time.isoformat()))
            
            rows = cursor.fetchall()
            
            trajectory = []
            for row in rows:
                trajectory.append({
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'altitude': row['altitude'],
                    'enu_e': row['enu_e'],
                    'enu_n': row['enu_n'],
                    'enu_u': row['enu_u'],
                    'timestamp': row['timestamp']
                })
            
            return trajectory
            
        except Exception as e:
            logger.error(f"获取飞机轨迹失败: {e}")
            return []
    
    def get_latest_aircraft_data(self, limit: int = 100) -> List[Dict]:
        """获取最新的飞机数据"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                SELECT * FROM aircraft_data 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            
            aircraft_list = []
            for row in rows:
                aircraft_list.append(dict(row))
            
            return aircraft_list
            
        except Exception as e:
            logger.error(f"获取最新飞机数据失败: {e}")
            return []
    
    def get_aircraft_by_icao(self, icao: str) -> Optional[Dict]:
        """根据ICAO获取最新飞机数据"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                SELECT * FROM aircraft_data 
                WHERE icao = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (icao,))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            return None
            
        except Exception as e:
            logger.error(f"获取飞机数据失败: {e}")
            return None
    
    def get_aircraft_in_time_range(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """获取时间范围内的飞机数据"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                SELECT * FROM aircraft_data 
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            rows = cursor.fetchall()
            
            aircraft_list = []
            for row in rows:
                aircraft_list.append(dict(row))
            
            return aircraft_list
            
        except Exception as e:
            logger.error(f"获取时间范围飞机数据失败: {e}")
            return []
    
    def get_statistics(self, date: datetime = None) -> Dict:
        """获取统计信息"""
        try:
            if date is None:
                date = datetime.now().date()
            
            cursor = self.connection.cursor()
            
            # 获取当日统计
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT icao) as unique_aircraft,
                    COUNT(*) as total_messages,
                    AVG(altitude) as avg_altitude,
                    MAX(altitude) as max_altitude,
                    MIN(altitude) as min_altitude
                FROM aircraft_data 
                WHERE DATE(timestamp) = ?
            ''', (date.isoformat(),))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'date': date.isoformat(),
                    'unique_aircraft': row['unique_aircraft'] or 0,
                    'total_messages': row['total_messages'] or 0,
                    'avg_altitude': row['avg_altitude'] or 0,
                    'max_altitude': row['max_altitude'] or 0,
                    'min_altitude': row['min_altitude'] or 0,
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 7):
        """清理旧数据"""
        try:
            cursor = self.connection.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 清理旧的飞机数据
            cursor.execute('''
                DELETE FROM aircraft_data 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_aircraft = cursor.rowcount
            
            # 清理旧的轨迹数据
            cursor.execute('''
                DELETE FROM aircraft_trajectory 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_trajectory = cursor.rowcount
            
            self.connection.commit()
            
            logger.info(f"清理完成: 删除 {deleted_aircraft} 条飞机数据, {deleted_trajectory} 条轨迹数据")
            
            return {
                'deleted_aircraft': deleted_aircraft,
                'deleted_trajectory': deleted_trajectory
            }
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            self.connection.rollback()
            return {}
    
    def export_data(self, filename: str, start_date: datetime = None, end_date: datetime = None):
        """导出数据到JSON文件"""
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=1)
            if end_date is None:
                end_date = datetime.now()
            
            aircraft_data = self.get_aircraft_in_time_range(start_date, end_date)
            
            export_data = {
                'export_time': datetime.now().isoformat(),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_records': len(aircraft_data),
                'aircraft_data': aircraft_data
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"数据已导出到: {filename}")
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")


def test_database_manager():
    """测试数据库管理器"""
    print("测试数据库管理器...")
    
    # 创建测试数据库
    db_manager = DatabaseManager('test_adsb.db')
    db_manager.initialize()
    
    # 测试数据
    test_aircraft = {
        'icao': 'TEST01',
        'latitude': 39.9,
        'longitude': 116.4,
        'altitude': 35000,
        'enu_e': 1000,
        'enu_n': 2000,
        'enu_u': 5000,
        'speed': 450,
        'heading': 90,
        'timestamp': datetime.now().isoformat()
    }
    
    # 存储数据
    db_manager.store_aircraft_data(test_aircraft)
    print("测试数据已存储")
    
    # 获取数据
    aircraft = db_manager.get_aircraft_by_icao('TEST01')
    print(f"获取到飞机数据: {aircraft['icao'] if aircraft else 'None'}")
    
    # 获取轨迹
    trajectory = db_manager.get_aircraft_trajectory('TEST01', hours=1)
    print(f"轨迹点数: {len(trajectory)}")
    
    # 获取统计信息
    stats = db_manager.get_statistics()
    print(f"统计信息: {stats}")
    
    # 清理测试数据库
    db_manager.close()
    if os.path.exists('test_adsb.db'):
        os.remove('test_adsb.db')
    
    print("测试完成")


if __name__ == '__main__':
    test_database_manager()
