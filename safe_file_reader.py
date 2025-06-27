#!/usr/bin/env python3
"""
安全文件读取器 - 避免与nav.py的文件写入冲突
"""

import os
import time
import errno
from datetime import datetime
from typing import List, Optional

# 尝试导入fcntl（仅在Unix/Linux系统可用）
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

class SafeFileReader:
    """安全的文件读取器，避免与写入进程冲突"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.last_position = 0
        self.last_size = 0
        
    def read_new_lines(self, max_retries: int = 3) -> List[str]:
        """安全读取文件新行"""
        for attempt in range(max_retries):
            try:
                return self._read_with_lock()
            except (IOError, OSError) as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EACCES:
                    # 文件被锁定，等待后重试
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    # 其他错误，直接返回空列表
                    return []
            except Exception:
                # 任何其他异常，等待后重试
                time.sleep(0.1 * (attempt + 1))
                continue
        
        return []
    
    def _read_with_lock(self) -> List[str]:
        """使用文件锁读取文件"""
        if not os.path.exists(self.file_path):
            return []
        
        try:
            # 获取文件大小
            current_size = os.path.getsize(self.file_path)
            
            # 如果文件变小，说明被重新创建
            if current_size < self.last_size:
                self.last_position = 0
            
            # 如果没有新内容
            if current_size <= self.last_position:
                self.last_size = current_size
                return []
            
            # 打开文件并尝试获取共享锁
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 在Windows上或没有fcntl时，使用简单读取
                if not HAS_FCNTL or os.name == 'nt':
                    return self._read_windows_safe(f, current_size)
                else:
                    return self._read_unix_safe(f, current_size)
                    
        except Exception:
            return []
    
    def _read_windows_safe(self, f, current_size: int) -> List[str]:
        """Windows安全读取"""
        try:
            f.seek(self.last_position)
            new_content = f.read(current_size - self.last_position)
            self.last_position = current_size
            self.last_size = current_size
            
            if new_content:
                lines = new_content.strip().split('\n')
                return [line.strip() for line in lines if line.strip()]
            
        except Exception:
            pass
        
        return []
    
    def _read_unix_safe(self, f, current_size: int) -> List[str]:
        """Unix/Linux安全读取（使用文件锁）"""
        if not HAS_FCNTL:
            return self._read_windows_safe(f, current_size)

        try:
            # 尝试获取共享锁（非阻塞）
            fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)

            f.seek(self.last_position)
            new_content = f.read(current_size - self.last_position)
            self.last_position = current_size
            self.last_size = current_size

            # 释放锁
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            if new_content:
                lines = new_content.strip().split('\n')
                return [line.strip() for line in lines if line.strip()]

        except (IOError, OSError) as e:
            if e.errno == errno.EAGAIN or e.errno == errno.EACCES:
                # 文件被锁定
                raise
        except Exception:
            pass

        return []


class SafeADSBDataReader:
    """安全的ADS-B数据读取器"""
    
    def __init__(self, log_file_path: str = 'adsb_decoded.log'):
        self.log_file_path = log_file_path
        self.file_reader = SafeFileReader(log_file_path)
        self.data_cache = {}
        self.last_cleanup = time.time()
        
    def get_latest_data(self) -> dict:
        """获取最新的飞机数据"""
        try:
            # 读取新行
            new_lines = self.file_reader.read_new_lines()
            
            # 解析新数据
            for line in new_lines:
                aircraft_data = self._parse_line(line)
                if aircraft_data:
                    icao = aircraft_data['icao']
                    self.data_cache[icao] = aircraft_data
            
            # 定期清理过期数据
            current_time = time.time()
            if current_time - self.last_cleanup > 60:  # 每分钟清理一次
                self._cleanup_expired_data()
                self.last_cleanup = current_time
            
            return dict(self.data_cache)
            
        except Exception as e:
            print(f"读取ADS-B数据时出错: {e}")
            return dict(self.data_cache)
    
    def _parse_line(self, line: str) -> Optional[dict]:
        """解析日志行 - 使用nav.py的原始时间戳"""
        try:
            parts = line.strip().split(',')
            if len(parts) >= 11:
                # 解析nav.py输出的时间戳格式: 'YYYY-MM-DD HH:MM:SS'
                nav_timestamp = parts[0]
                nav_time = datetime.strptime(nav_timestamp, '%Y-%m-%d %H:%M:%S')
                nav_time_unix = nav_time.timestamp()

                icao = parts[1]

                # 调试特定飞机的时间戳解析（可选）
                # if icao == '78127C':
                #     print(f"[DEBUG] 解析78127C: nav_timestamp={nav_timestamp}, nav_time_unix={nav_time_unix}")

                return {
                    'nav_timestamp': nav_timestamp,  # nav.py的原始时间戳
                    'nav_time_unix': nav_time_unix,  # 转换为Unix时间戳用于排序
                    'icao': icao,
                    'latitude': float(parts[2]),
                    'longitude': float(parts[3]),
                    'altitude': int(parts[4]),
                    'ecef_x': float(parts[5]),
                    'ecef_y': float(parts[6]),
                    'ecef_z': float(parts[7]),
                    'enu_e': float(parts[8]),
                    'enu_n': float(parts[9]),
                    'enu_u': float(parts[10]),
                    'last_seen': time.time(),  # 系统接收时间
                    'timestamp': nav_timestamp  # 保持兼容性
                }
        except (ValueError, IndexError) as e:
            print(f"[ERROR] 解析日志行失败: {e}, line: {line[:100]}")

        return None
    
    def _cleanup_expired_data(self):
        """清理过期数据 - 60分钟过期机制"""
        current_time = time.time()
        expired_icaos = []

        for icao, data in self.data_cache.items():
            data_age = current_time - data.get('last_seen', 0)
            if data_age > 3600:  # 60分钟过期
                expired_icaos.append(icao)

        for icao in expired_icaos:
            del self.data_cache[icao]

        if expired_icaos:
            print(f"清理了 {len(expired_icaos)} 个过期飞机数据（60分钟无更新）")


# 测试函数
def test_safe_reader():
    """测试安全读取器"""
    reader = SafeADSBDataReader()
    
    print("测试安全文件读取器...")
    for i in range(10):
        data = reader.get_latest_data()
        print(f"第{i+1}次读取: 发现 {len(data)} 架飞机")
        time.sleep(2)

if __name__ == '__main__':
    test_safe_reader()
