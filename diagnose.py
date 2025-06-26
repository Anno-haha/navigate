#!/usr/bin/env python3
"""
ADS-B系统诊断工具
快速检查nav.py和可视化系统的状态
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

def check_files():
    """检查必要文件"""
    print_header("文件检查")
    
    required_files = [
        'nav.py',
        'simple_visual.py', 
        'coord_converter.py',
        'data_processor.py',
        'websocket_handler.py',
        'database_manager.py'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"[OK] {file} ({size} bytes)")
        else:
            print(f"[MISSING] {file}")
            missing_files.append(file)
    
    return len(missing_files) == 0

def check_nav_py_status():
    """检查nav.py状态"""
    print_header("nav.py状态检查")
    
    # 检查日志文件
    if os.path.exists('adsb_decoded.log'):
        stat = os.stat('adsb_decoded.log')
        size = stat.st_size
        mtime = stat.st_mtime
        age = time.time() - mtime
        
        print(f"[OK] adsb_decoded.log 存在")
        print(f"     文件大小: {size} bytes")
        print(f"     最后修改: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     文件年龄: {age:.1f} 秒")
        
        if age < 60:
            print(f"[OK] nav.py 正在活跃运行 (最近 {age:.0f} 秒有更新)")
            return True
        elif age < 300:
            print(f"[WARN] nav.py 可能暂停 (最近 {age/60:.1f} 分钟无更新)")
            return False
        else:
            print(f"[ERROR] nav.py 可能已停止 (超过 {age/60:.1f} 分钟无更新)")
            return False
    else:
        print("[ERROR] adsb_decoded.log 不存在")
        print("        nav.py 可能从未运行或运行失败")
        return False

def check_ports():
    """检查端口占用"""
    print_header("端口检查")
    
    import socket
    
    ports_to_check = [8000, 8001, 8002, 8003]
    available_ports = []
    
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                print(f"[AVAILABLE] 端口 {port}")
                available_ports.append(port)
        except OSError:
            print(f"[OCCUPIED] 端口 {port} 被占用")
    
    return available_ports

def test_nav_py():
    """测试nav.py是否能启动"""
    print_header("nav.py启动测试")
    
    if not os.path.exists('nav.py'):
        print("[ERROR] nav.py 文件不存在")
        return False
    
    try:
        print("[INFO] 尝试启动nav.py (5秒测试)...")
        process = subprocess.Popen(
            [sys.executable, 'nav.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待5秒
        time.sleep(5)
        
        if process.poll() is None:
            print("[OK] nav.py 启动成功，正在运行")
            process.terminate()
            process.wait(timeout=3)
            return True
        else:
            stdout, stderr = process.communicate()
            print("[ERROR] nav.py 启动失败")
            if stderr:
                print(f"错误信息: {stderr[:200]}...")
            return False
            
    except Exception as e:
        print(f"[ERROR] 测试nav.py时出错: {e}")
        return False

def test_simple_visual():
    """测试simple_visual.py是否能启动"""
    print_header("simple_visual.py启动测试")
    
    if not os.path.exists('simple_visual.py'):
        print("[ERROR] simple_visual.py 文件不存在")
        return False
    
    try:
        print("[INFO] 尝试导入simple_visual模块...")
        # 尝试导入检查语法
        result = subprocess.run(
            [sys.executable, '-c', 'import simple_visual; print("Import OK")'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("[OK] simple_visual.py 语法正确")
            return True
        else:
            print("[ERROR] simple_visual.py 有语法错误")
            print(f"错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 测试simple_visual.py时出错: {e}")
        return False

def check_data_flow():
    """检查数据流"""
    print_header("数据流检查")
    
    if not os.path.exists('adsb_decoded.log'):
        print("[ERROR] 没有数据文件")
        return False
    
    try:
        # 读取最后几行
        with open('adsb_decoded.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            print("[ERROR] 数据文件为空")
            return False
        
        print(f"[OK] 数据文件包含 {len(lines)} 行")
        
        # 显示最后几行
        print("最近的数据:")
        for line in lines[-3:]:
            parts = line.strip().split(',')
            if len(parts) >= 5:
                print(f"  {parts[0]} - {parts[1]} - 高度:{parts[4]}ft")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 读取数据文件失败: {e}")
        return False

def provide_solutions():
    """提供解决方案"""
    print_header("解决方案建议")
    
    print("如果nav.py无法输出数据:")
    print("1. 检查ADS-B接收器连接")
    print("2. 确认串口号正确 (通常是COM3)")
    print("3. 重启nav.py: python nav.py")
    print("4. 检查串口权限和驱动")
    
    print("\n如果start_both.py无法运行:")
    print("1. 先单独启动: python nav.py")
    print("2. 再启动可视化: python simple_visual.py")
    print("3. 检查端口占用情况")
    print("4. 确保没有重复启动")
    
    print("\n推荐的启动顺序:")
    print("1. python nav.py        # 终端1")
    print("2. python simple_visual.py  # 终端2")

def main():
    """主诊断函数"""
    print("ADS-B系统诊断工具")
    print("当前时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 执行所有检查
    checks = [
        ("文件完整性", check_files),
        ("nav.py状态", check_nav_py_status),
        ("端口可用性", lambda: len(check_ports()) > 0),
        ("数据流", check_data_flow),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"[ERROR] {name}检查失败: {e}")
            results[name] = False
    
    # 总结
    print_header("诊断总结")
    for name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    # 提供解决方案
    if not all(results.values()):
        provide_solutions()
    else:
        print("\n[SUCCESS] 系统状态正常！")
        print("可以运行: python start_both.py")

if __name__ == '__main__':
    main()
