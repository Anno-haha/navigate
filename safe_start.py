#!/usr/bin/env python3
"""
安全启动脚本 - 确保nav.py和可视化系统不会互相干扰
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime

def print_status(message, status="INFO"):
    """打印状态信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{status}] {message}")

def check_nav_py_running():
    """检查nav.py是否在运行"""
    if os.path.exists('adsb_decoded.log'):
        try:
            mtime = os.path.getmtime('adsb_decoded.log')
            age = time.time() - mtime
            if age < 30:  # 30秒内有更新
                return True, age
        except:
            pass
    return False, None

def wait_for_nav_py_stable():
    """等待nav.py稳定运行"""
    print_status("等待nav.py稳定运行...")
    stable_count = 0
    
    for i in range(30):  # 最多等待30秒
        running, age = check_nav_py_running()
        if running:
            stable_count += 1
            if stable_count >= 3:  # 连续3次检测到稳定
                print_status(f"nav.py运行稳定 (数据年龄: {age:.1f}秒)", "OK")
                return True
        else:
            stable_count = 0
        
        time.sleep(1)
    
    print_status("nav.py未能稳定运行", "WARN")
    return False

def start_nav_py_safe():
    """安全启动nav.py"""
    print_status("检查nav.py状态...")
    
    running, age = check_nav_py_running()
    if running:
        print_status(f"nav.py已在运行 (数据年龄: {age:.1f}秒)", "OK")
        return "already_running"
    
    print_status("启动nav.py...")
    try:
        # 确保没有残留的日志锁定
        if os.path.exists('adsb_decoded.log.lock'):
            os.remove('adsb_decoded.log.lock')
        
        # 启动nav.py
        process = subprocess.Popen(
            [sys.executable, 'nav.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待启动
        time.sleep(3)
        
        if process.poll() is None:
            print_status(f"nav.py启动成功 (PID: {process.pid})", "OK")
            
            # 等待稳定
            if wait_for_nav_py_stable():
                return process
            else:
                print_status("nav.py启动但不稳定，终止进程", "WARN")
                process.terminate()
                return None
        else:
            stdout, stderr = process.communicate()
            print_status(f"nav.py启动失败: {stderr[:100]}", "ERROR")
            return None
            
    except Exception as e:
        print_status(f"启动nav.py时出错: {e}", "ERROR")
        return None

def start_visual_safe():
    """安全启动可视化系统"""
    print_status("启动可视化系统...")
    
    try:
        # 等待一段时间，确保nav.py稳定
        time.sleep(2)
        
        # 启动可视化系统
        process = subprocess.Popen(
            [sys.executable, 'simple_visual.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.PIPE
        )
        
        # 自动回答启动确认
        try:
            process.stdin.write('y\n')
            process.stdin.flush()
            process.stdin.close()
        except:
            pass
        
        # 等待启动
        time.sleep(3)
        
        if process.poll() is None:
            print_status(f"可视化系统启动成功 (PID: {process.pid})", "OK")
            return process
        else:
            stdout, stderr = process.communicate()
            print_status(f"可视化系统启动失败: {stderr[:100]}", "ERROR")
            return None
            
    except Exception as e:
        print_status(f"启动可视化系统时出错: {e}", "ERROR")
        return None

def monitor_processes(nav_process, visual_process):
    """监控进程状态"""
    print_status("开始监控进程状态...")
    
    while True:
        try:
            # 检查nav.py状态
            if nav_process != "already_running":
                if nav_process and nav_process.poll() is not None:
                    print_status("nav.py进程意外停止", "ERROR")
                    break
            
            # 检查可视化系统状态
            if visual_process and visual_process.poll() is not None:
                print_status("可视化系统进程意外停止", "ERROR")
                break
            
            # 检查数据流
            running, age = check_nav_py_running()
            if not running:
                print_status("nav.py数据流中断", "WARN")
            
            time.sleep(10)  # 每10秒检查一次
            
        except KeyboardInterrupt:
            print_status("收到停止信号", "INFO")
            break
        except Exception as e:
            print_status(f"监控过程中出错: {e}", "ERROR")
            time.sleep(5)

def cleanup_processes(nav_process, visual_process):
    """清理进程"""
    print_status("正在清理进程...")
    
    # 停止可视化系统
    if visual_process and visual_process.poll() is None:
        print_status("停止可视化系统...")
        visual_process.terminate()
        try:
            visual_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            visual_process.kill()
    
    # 停止nav.py（如果是我们启动的）
    if nav_process != "already_running" and nav_process and nav_process.poll() is None:
        print_status("停止nav.py...")
        nav_process.terminate()
        try:
            nav_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            nav_process.kill()
    
    print_status("清理完成", "OK")

def main():
    """主函数"""
    print("=" * 60)
    print("ADS-B 安全启动脚本")
    print("=" * 60)
    print("功能: 安全启动nav.py和可视化系统，避免文件冲突")
    print("=" * 60)
    
    nav_process = None
    visual_process = None
    
    try:
        # 启动nav.py
        nav_process = start_nav_py_safe()
        if not nav_process:
            print_status("nav.py启动失败，退出", "ERROR")
            return
        
        # 启动可视化系统
        visual_process = start_visual_safe()
        if not visual_process:
            print_status("可视化系统启动失败", "ERROR")
            if nav_process != "already_running":
                cleanup_processes(nav_process, None)
            return
        
        # 显示访问信息
        print("\n" + "=" * 60)
        print_status("系统启动完成！", "SUCCESS")
        print("访问地址:")
        print("  主页: http://127.0.0.1:8000/")
        print("  雷达: http://127.0.0.1:8000/radar/")
        print("  API:  http://127.0.0.1:8000/api/aircraft/")
        print("\n按 Ctrl+C 停止所有程序")
        print("=" * 60)
        
        # 监控进程
        monitor_processes(nav_process, visual_process)
        
    except KeyboardInterrupt:
        print_status("收到停止信号", "INFO")
    except Exception as e:
        print_status(f"运行过程中出错: {e}", "ERROR")
    finally:
        cleanup_processes(nav_process, visual_process)

if __name__ == '__main__':
    main()
