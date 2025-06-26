#!/usr/bin/env python3
"""
ADS-B数据处理器模块
负责从nav.py获取数据并进行处理
"""

import os
import csv
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ADSBDataProcessor:
    """ADS-B数据处理器"""
    
    def __init__(self):
        self.log_file_path = 'adsb_decoded.log'
        self.last_read_position = 0
        self.last_read_time = datetime.now()
        self.aircraft_cache = {}
        
    def get_latest_adsb_data(self) -> List[Dict]:
        """
        从nav.py的日志文件获取最新ADS-B数据
        
        Returns:
            List[Dict]: 飞机数据列表
        """
        try:
            if not os.path.exists(self.log_file_path):
                return []
            
            # 读取新增的日志行
            new_lines = self._read_new_log_lines()
            
            # 解析数据
            aircraft_data = []
            for line in new_lines:
                parsed_data = self._parse_log_line(line)
                if parsed_data:
                    aircraft_data.append(parsed_data)
            
            # 更新缓存
            self._update_aircraft_cache(aircraft_data)
            
            return aircraft_data
            
        except Exception as e:
            logger.error(f"获取ADS-B数据失败: {e}")
            return []
    
    def _read_new_log_lines(self) -> List[str]:
        """读取日志文件中的新行 - 使用安全的文件读取方式"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.log_file_path):
                return []

            # 获取文件大小
            current_size = os.path.getsize(self.log_file_path)

            # 如果文件变小了，说明被重新创建，重置读取位置
            if current_size < self.last_read_position:
                self.last_read_position = 0

            # 如果没有新内容，直接返回
            if current_size <= self.last_read_position:
                return []

            # 使用共享读取模式打开文件，避免与写入进程冲突
            try:
                with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 移动到上次读取的位置
                    f.seek(self.last_read_position)

                    # 读取新内容
                    new_content = f.read()

                    # 更新读取位置
                    self.last_read_position = f.tell()

                    # 分割成行
                    if new_content:
                        lines = new_content.strip().split('\n')
                        return [line for line in lines if line.strip()]

            except (IOError, OSError) as e:
                # 文件被占用时，等待一小段时间后重试
                import time
                time.sleep(0.1)
                return []

        except Exception as e:
            logger.error(f"读取日志文件失败: {e}")

        return []
    
    def _parse_log_line(self, line: str) -> Optional[Dict]:
        """
        解析日志行数据
        
        格式: 时间戳,ICAO,纬度,经度,高度(英尺),ECEF_X,ECEF_Y,ECEF_Z,ENU_E,ENU_N,ENU_U
        """
        try:
            parts = line.strip().split(',')
            
            if len(parts) >= 11:  # 完整格式（包含ENU）
                return {
                    'timestamp': parts[0],
                    'icao': parts[1],
                    'latitude': float(parts[2]),
                    'longitude': float(parts[3]),
                    'altitude': int(parts[4]),
                    'ecef_x': float(parts[5]),
                    'ecef_y': float(parts[6]),
                    'ecef_z': float(parts[7]),
                    'enu_e': float(parts[8]),
                    'enu_n': float(parts[9]),
                    'enu_u': float(parts[10]),
                }
            elif len(parts) >= 8:  # ECEF格式
                return {
                    'timestamp': parts[0],
                    'icao': parts[1],
                    'latitude': float(parts[2]),
                    'longitude': float(parts[3]),
                    'altitude': int(parts[4]),
                    'ecef_x': float(parts[5]),
                    'ecef_y': float(parts[6]),
                    'ecef_z': float(parts[7]),
                    'enu_e': 0.0,
                    'enu_n': 0.0,
                    'enu_u': 0.0,
                }
            elif len(parts) >= 5:  # 基础格式
                return {
                    'timestamp': parts[0],
                    'icao': parts[1],
                    'latitude': float(parts[2]),
                    'longitude': float(parts[3]),
                    'altitude': int(parts[4]),
                    'ecef_x': 0.0,
                    'ecef_y': 0.0,
                    'ecef_z': 0.0,
                    'enu_e': 0.0,
                    'enu_n': 0.0,
                    'enu_u': 0.0,
                }
                
        except Exception as e:
            logger.warning(f"解析日志行失败: {line[:50]}... - {e}")
        
        return None
    
    def _update_aircraft_cache(self, aircraft_data: List[Dict]):
        """更新飞机数据缓存"""
        current_time = datetime.now()
        
        # 更新新数据
        for aircraft in aircraft_data:
            icao = aircraft['icao']
            aircraft['last_seen'] = current_time
            self.aircraft_cache[icao] = aircraft
        
        # 清理过期数据（超过5分钟）
        expired_icaos = []
        for icao, data in self.aircraft_cache.items():
            if (current_time - data['last_seen']).seconds > 300:
                expired_icaos.append(icao)
        
        for icao in expired_icaos:
            del self.aircraft_cache[icao]
    
    def get_cached_aircraft_data(self) -> Dict:
        """获取缓存的飞机数据"""
        return self.aircraft_cache.copy()
    
    def get_aircraft_by_icao(self, icao: str) -> Optional[Dict]:
        """根据ICAO获取特定飞机数据"""
        return self.aircraft_cache.get(icao)
    
    def get_aircraft_in_range(self, max_distance: float) -> List[Dict]:
        """
        获取指定范围内的飞机
        
        Args:
            max_distance: 最大距离（米）
            
        Returns:
            List[Dict]: 范围内的飞机列表
        """
        aircraft_in_range = []
        
        for aircraft in self.aircraft_cache.values():
            # 计算距离参考点的距离
            enu_e = aircraft.get('enu_e', 0)
            enu_n = aircraft.get('enu_n', 0)
            enu_u = aircraft.get('enu_u', 0)
            
            distance = (enu_e**2 + enu_n**2 + enu_u**2)**0.5
            
            if distance <= max_distance:
                aircraft_copy = aircraft.copy()
                aircraft_copy['distance'] = distance
                aircraft_in_range.append(aircraft_copy)
        
        # 按距离排序
        aircraft_in_range.sort(key=lambda x: x['distance'])
        
        return aircraft_in_range
    
    def get_aircraft_by_altitude_range(self, min_alt: int, max_alt: int) -> List[Dict]:
        """
        获取指定高度范围内的飞机
        
        Args:
            min_alt: 最小高度（英尺）
            max_alt: 最大高度（英尺）
            
        Returns:
            List[Dict]: 高度范围内的飞机列表
        """
        return [
            aircraft for aircraft in self.aircraft_cache.values()
            if min_alt <= aircraft['altitude'] <= max_alt
        ]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.aircraft_cache:
            return {
                'total_aircraft': 0,
                'altitude_stats': {},
                'position_stats': {},
            }
        
        altitudes = [aircraft['altitude'] for aircraft in self.aircraft_cache.values()]
        
        # 高度统计
        altitude_ranges = {
            'low': len([a for a in altitudes if a < 10000]),      # 低空
            'medium': len([a for a in altitudes if 10000 <= a < 33000]),  # 中空
            'high': len([a for a in altitudes if a >= 33000]),    # 高空
        }
        
        # 位置统计
        distances = []
        for aircraft in self.aircraft_cache.values():
            enu_e = aircraft.get('enu_e', 0)
            enu_n = aircraft.get('enu_n', 0)
            distance = (enu_e**2 + enu_n**2)**0.5  # 水平距离
            distances.append(distance)
        
        return {
            'total_aircraft': len(self.aircraft_cache),
            'altitude_stats': {
                'ranges': altitude_ranges,
                'min': min(altitudes) if altitudes else 0,
                'max': max(altitudes) if altitudes else 0,
                'avg': sum(altitudes) / len(altitudes) if altitudes else 0,
            },
            'position_stats': {
                'min_distance': min(distances) if distances else 0,
                'max_distance': max(distances) if distances else 0,
                'avg_distance': sum(distances) / len(distances) if distances else 0,
            },
            'last_update': self.last_read_time.isoformat(),
        }
    
    def export_data(self, filename: str, format: str = 'json'):
        """
        导出数据到文件
        
        Args:
            filename: 文件名
            format: 格式 ('json' 或 'csv')
        """
        try:
            if format.lower() == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.aircraft_cache, f, indent=2, ensure_ascii=False)
            
            elif format.lower() == 'csv':
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if self.aircraft_cache:
                        writer = csv.DictWriter(f, fieldnames=list(next(iter(self.aircraft_cache.values())).keys()))
                        writer.writeheader()
                        for aircraft in self.aircraft_cache.values():
                            writer.writerow(aircraft)
            
            logger.info(f"数据已导出到: {filename}")
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")


def test_data_processor():
    """测试数据处理器"""
    print("测试ADS-B数据处理器...")
    
    processor = ADSBDataProcessor()
    
    # 获取最新数据
    data = processor.get_latest_adsb_data()
    print(f"获取到 {len(data)} 条新数据")
    
    # 获取缓存数据
    cached_data = processor.get_cached_aircraft_data()
    print(f"缓存中有 {len(cached_data)} 架飞机")
    
    # 获取统计信息
    stats = processor.get_statistics()
    print(f"统计信息: {stats}")
    
    # 获取范围内飞机
    nearby_aircraft = processor.get_aircraft_in_range(100000)  # 100km
    print(f"100km范围内有 {len(nearby_aircraft)} 架飞机")


if __name__ == '__main__':
    test_data_processor()
