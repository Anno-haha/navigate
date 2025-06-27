#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime, timedelta

print("=== ADS-B系统诊断测试 ===")
print(f"当前时间: {datetime.now()}")
print(f"工作目录: {os.getcwd()}")

# 检查数据文件
print("\n1. 检查数据文件:")
files_to_check = ['adsb_decoded.log', 'adsb_raw.log']
for filename in files_to_check:
    if os.path.exists(filename):
        stat = os.stat(filename)
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
        print(f"  {filename}: 存在, 大小={size}字节, 修改时间={mtime}")
    else:
        print(f"  {filename}: 不存在")

# 检查数据内容
print("\n2. 检查数据内容:")
try:
    with open('adsb_decoded.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        total_lines = len(lines)
        print(f"  总行数: {total_lines}")
        
        if total_lines > 0:
            # 显示最后几行
            print("  最后5行:")
            for line in lines[-5:]:
                print(f"    {line.strip()}")
                
            # 分析数据时间
            current_time = datetime.now()
            recent_count = 0
            old_count = 0
            
            for line in lines[-100:]:  # 检查最后100行
                try:
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        timestamp_str = parts[0]
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        time_diff = (current_time - timestamp).total_seconds()
                        
                        if time_diff < 3600:  # 1小时内
                            recent_count += 1
                        else:
                            old_count += 1
                except:
                    pass
            
            print(f"  最近100行中: 1小时内={recent_count}行, 1小时外={old_count}行")
        
except Exception as e:
    print(f"  读取adsb_decoded.log失败: {e}")

# 检查nav.py进程
print("\n3. 检查nav.py进程:")
try:
    import subprocess
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                          capture_output=True, text=True)
    if 'python.exe' in result.stdout:
        print("  发现python.exe进程在运行")
        # 计算进程数量
        lines = result.stdout.split('\n')
        python_processes = [line for line in lines if 'python.exe' in line]
        print(f"  Python进程数量: {len(python_processes)}")
    else:
        print("  没有发现python.exe进程")
except Exception as e:
    print(f"  检查进程失败: {e}")

# 测试数据解析
print("\n4. 测试数据解析:")
try:
    aircraft_data = {}
    current_time = datetime.now()
    
    with open('adsb_decoded.log', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            try:
                parts = line.split(',')
                if len(parts) >= 5:
                    timestamp_str = parts[0]
                    icao = parts[1]
                    lat = float(parts[2])
                    lon = float(parts[3])
                    alt = int(parts[4])
                    
                    # 检查时间
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    time_diff = (current_time - timestamp).total_seconds()
                    
                    if time_diff <= 86400:  # 24小时内
                        aircraft_data[icao] = {
                            'timestamp': timestamp_str,
                            'lat': lat,
                            'lon': lon,
                            'alt': alt,
                            'time_diff': time_diff
                        }
            except Exception as e:
                continue
    
    print(f"  解析成功的飞机数量: {len(aircraft_data)}")
    
    # 显示前5架飞机
    count = 0
    for icao, data in aircraft_data.items():
        if count < 5:
            print(f"    {icao}: lat={data['lat']}, lon={data['lon']}, alt={data['alt']}, 时间差={data['time_diff']:.0f}秒")
            count += 1
        else:
            break
            
except Exception as e:
    print(f"  数据解析失败: {e}")

print("\n=== 诊断完成 ===")
