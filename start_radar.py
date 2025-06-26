#!/usr/bin/env python3
"""
2D雷达系统启动脚本
确保与nav.py协调运行，优先保证实时性
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime

def print_status(message, status="INFO"):
    """打印状态信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{status}] {message}")

def check_nav_py_status():
    """检查nav.py运行状态"""
    if os.path.exists('adsb_decoded.log'):
        try:
            mtime = os.path.getmtime('adsb_decoded.log')
            age = time.time() - mtime
            if age < 30:  # 30秒内有更新
                return True, age
        except:
            pass
    return False, None

def check_system_requirements():
    """检查系统要求"""
    print_status("检查系统要求...")
    
    # 检查必要文件
    required_files = ['nav.py', 'radar_2d.py', 'safe_file_reader.py']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print_status(f"缺少文件: {', '.join(missing_files)}", "ERROR")
        return False
    
    print_status("所有必需文件存在", "OK")
    return True

def wait_for_nav_py():
    """等待nav.py稳定运行"""
    print_status("等待nav.py稳定运行...")
    
    for i in range(30):  # 最多等待30秒
        running, age = check_nav_py_status()
        if running:
            print_status(f"nav.py运行正常 (数据年龄: {age:.1f}秒)", "OK")
            return True
        
        if i == 0:
            print_status("nav.py未运行，请在另一个终端启动: python nav.py", "WARN")
        
        print(f"等待nav.py... ({i+1}/30)")
        time.sleep(1)
    
    print_status("nav.py未能稳定运行", "ERROR")
    return False

def start_radar_system():
    """启动雷达系统"""
    print_status("启动2D雷达系统...")
    
    try:
        # 启动雷达系统
        process = subprocess.Popen(
            [sys.executable, 'radar_2d.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待启动
        time.sleep(3)
        
        if process.poll() is None:
            print_status(f"雷达系统启动成功 (PID: {process.pid})", "OK")
            return process
        else:
            stdout, stderr = process.communicate()
            print_status(f"雷达系统启动失败: {stderr[:100]}", "ERROR")
            return None
            
    except Exception as e:
        print_status(f"启动雷达系统时出错: {e}", "ERROR")
        return None

def monitor_radar_system(process):
    """监控雷达系统"""
    print_status("开始监控雷达系统...")
    
    def read_output():
        """读取雷达系统输出"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    print(f"[RADAR] {line.strip()}")
        except:
            pass
    
    # 启动输出读取线程
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()
    
    try:
        while True:
            # 检查进程状态
            if process.poll() is not None:
                print_status("雷达系统进程意外停止", "ERROR")
                break
            
            # 检查nav.py状态
            running, age = check_nav_py_status()
            if not running:
                print_status("nav.py数据流中断", "WARN")
            
            time.sleep(5)  # 每5秒检查一次
            
    except KeyboardInterrupt:
        print_status("收到停止信号", "INFO")
    
    # 停止雷达系统
    if process.poll() is None:
        print_status("停止雷达系统...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    print_status("雷达系统已停止", "OK")

def show_performance_tips():
    """显示性能优化提示"""
    print("\n" + "=" * 60)
    print("2D雷达系统性能优化提示")
    print("=" * 60)
    print("1. 实时性优化:")
    print("   - 数据更新间隔: 500ms")
    print("   - 渲染频率: 60 FPS")
    print("   - 网络延迟监控: 实时显示")
    print()
    print("2. 显示优化:")
    print("   - 可关闭轨迹显示以提高性能")
    print("   - 可调节雷达范围减少计算量")
    print("   - 使用硬件加速的Canvas渲染")
    print()
    print("3. 数据优化:")
    print("   - 自动清理过期飞机数据")
    print("   - 智能轨迹长度限制")
    print("   - 增量数据更新")
    print("=" * 60)

def main():
    """主函数"""
    print("ADS-B 2D雷达系统启动器")
    print("=" * 50)
    print("专为实时性优化的雷达显示系统")
    print("=" * 50)
    
    # 检查系统要求
    if not check_system_requirements():
        return
    
    # 等待nav.py
    if not wait_for_nav_py():
        response = input("\n是否继续启动雷达系统? (y/n): ").lower().strip()
        if response not in ['y', 'yes', '是']:
            print("已取消启动")
            return
    
    # 启动雷达系统
    radar_process = start_radar_system()
    if not radar_process:
        return
    
    # 显示访问信息
    print("\n" + "=" * 50)
    print_status("2D雷达系统启动完成！", "SUCCESS")
    print("\n访问地址:")
    print("  雷达显示: http://127.0.0.1:8001/")
    print("  API接口:  http://127.0.0.1:8001/api/radar/aircraft")
    print("\n功能特性:")
    print("  - 实时雷达扫描动画")
    print("  - 飞机轨迹追踪")
    print("  - 点击查看飞机详情")
    print("  - 可调节雷达范围")
    print("  - 性能监控显示")
    print("\n按 Ctrl+C 停止雷达系统")
    print("=" * 50)
    
    # 显示性能提示
    show_performance_tips()
    
    # 监控系统
    monitor_radar_system(radar_process)

def quick_start():
    """快速启动模式"""
    print("快速启动2D雷达系统...")
    
    # 简单检查
    if not os.path.exists('radar_2d.py'):
        print("错误: 找不到radar_2d.py文件")
        return
    
    # 直接启动
    try:
        import radar_2d
        radar_2d.main()
    except Exception as e:
        print(f"启动失败: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_start()
    else:
        main()
