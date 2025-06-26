#!/usr/bin/env python3
"""
同时启动nav.py和可视化系统的脚本
确保两个程序可以并行运行而不冲突
"""

import os
import sys
import time
import subprocess
import threading
import signal

def check_file_exists(filename):
    """检查文件是否存在"""
    return os.path.exists(filename)

def check_nav_py_running():
    """检查nav.py是否已经在运行"""
    # 检查日志文件是否最近有更新
    if os.path.exists('adsb_decoded.log'):
        mtime = os.path.getmtime('adsb_decoded.log')
        if time.time() - mtime < 60:  # 1分钟内有更新
            return True, "active"
    return False, None

def start_nav_py():
    """启动nav.py数据采集"""
    print("[INFO] 启动nav.py数据采集程序...")

    # 先检查是否已经在运行
    is_running, pid = check_nav_py_running()
    if is_running:
        print(f"[INFO] nav.py已经在运行 (PID: {pid})")
        return "already_running"

    if not check_file_exists('nav.py'):
        print("[ERROR] 找不到nav.py文件")
        return None

    try:
        # 启动nav.py进程
        process = subprocess.Popen(
            [sys.executable, 'nav.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        print(f"[OK] nav.py已启动 (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"[ERROR] 启动nav.py失败: {e}")
        return None

def start_visualization():
    """启动可视化系统"""
    print("🌐 启动可视化系统...")
    
    if not check_file_exists('simple_visual.py'):
        print("❌ 找不到simple_visual.py文件")
        return None
    
    try:
        # 启动可视化系统
        process = subprocess.Popen(
            [sys.executable, 'simple_visual.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            stdin=subprocess.PIPE
        )
        
        # 自动回答启动确认
        time.sleep(2)
        try:
            process.stdin.write('y\n')
            process.stdin.flush()
        except:
            pass
        
        print(f"✅ 可视化系统已启动 (PID: {process.pid})")
        return process
        
    except Exception as e:
        print(f"❌ 启动可视化系统失败: {e}")
        return None

def monitor_process(process, name):
    """监控进程状态"""
    def monitor():
        while True:
            if process.poll() is not None:
                print(f"⚠️ {name} 进程已停止")
                break
            time.sleep(5)
    
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    return monitor_thread

def read_process_output(process, name):
    """读取进程输出"""
    def read_stdout():
        try:
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    print(f"[{name}] {line.strip()}")
        except:
            pass
    
    def read_stderr():
        try:
            for line in iter(process.stderr.readline, ''):
                if line.strip():
                    print(f"[{name}] ERROR: {line.strip()}")
        except:
            pass
    
    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    
    stdout_thread.start()
    stderr_thread.start()
    
    return stdout_thread, stderr_thread

def main():
    """主函数"""
    print("ADS-B 系统启动器")
    print("=" * 50)
    print("将同时启动nav.py数据采集和可视化系统")
    print("=" * 50)
    
    nav_process = None
    visual_process = None
    
    try:
        # 启动nav.py
        nav_process = start_nav_py()
        nav_already_running = False

        if nav_process == "already_running":
            nav_already_running = True
            nav_process = None
            print("[INFO] 使用现有的nav.py进程")
        elif nav_process:
            monitor_process(nav_process, "nav.py")
            # 等待nav.py稳定
            print("[INFO] 等待nav.py稳定运行...")
            time.sleep(3)

        # 启动可视化系统
        visual_process = start_visualization()
        if visual_process:
            monitor_process(visual_process, "可视化系统")
            # 读取可视化系统输出
            read_process_output(visual_process, "可视化")
        
        # 等待一段时间让系统稳定
        time.sleep(3)
        
        # 显示访问信息
        print("\n" + "=" * 50)
        print("[SUCCESS] 系统启动完成！")
        print("\n[STATUS] 系统状态:")

        # 检查nav.py状态
        nav_running, _ = check_nav_py_running()
        if nav_running:
            print("  [OK] nav.py数据采集: 运行中")
        else:
            print("  [WARN] nav.py数据采集: 未检测到")

        if visual_process and visual_process.poll() is None:
            print("  [OK] 可视化系统: 运行中")
        else:
            print("  [ERROR] 可视化系统: 未运行")
        
        print("\n🌐 访问地址:")
        print("  主页: http://127.0.0.1:8000/ (或其他可用端口)")
        print("  雷达: http://127.0.0.1:8000/radar/")
        print("  API: http://127.0.0.1:8000/api/aircraft/")
        
        print("\n💡 使用说明:")
        print("  - 两个程序将并行运行，互不干扰")
        print("  - nav.py负责数据采集，可视化系统负责显示")
        print("  - 按 Ctrl+C 可同时停止两个程序")
        
        print("\n⌨️ 按 Ctrl+C 停止所有程序...")
        
        # 等待用户中断
        while True:
            time.sleep(1)
            
            # 检查进程状态
            if nav_process and nav_process.poll() is not None:
                print("⚠️ nav.py进程意外停止")
                break
            
            if visual_process and visual_process.poll() is not None:
                print("⚠️ 可视化系统进程意外停止")
                break
    
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止所有程序...")
        
        # 停止进程
        if visual_process and visual_process.poll() is None:
            print("停止可视化系统...")
            visual_process.terminate()
            try:
                visual_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                visual_process.kill()
        
        if nav_process and nav_process.poll() is None:
            print("停止nav.py...")
            nav_process.terminate()
            try:
                nav_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                nav_process.kill()
        
        print("✅ 所有程序已停止")
    
    except Exception as e:
        print(f"\n❌ 运行过程中出错: {e}")
        
        # 清理进程
        for process in [nav_process, visual_process]:
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=3)
                except:
                    try:
                        process.kill()
                    except:
                        pass

def quick_check():
    """快速检查系统状态"""
    print("🔍 快速系统检查")
    print("-" * 30)
    
    # 检查文件
    files_to_check = ['nav.py', 'simple_visual.py', 'coord_converter.py', 'data_processor.py']
    missing_files = [f for f in files_to_check if not check_file_exists(f)]
    
    if missing_files:
        print(f"❌ 缺少文件: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 所有必需文件存在")
    
    # 检查日志文件
    if check_file_exists('adsb_decoded.log'):
        mtime = os.path.getmtime('adsb_decoded.log')
        age = time.time() - mtime
        if age < 300:  # 5分钟内
            print("✅ 发现最近的ADS-B数据")
        else:
            print(f"⚠️ ADS-B数据较旧 ({age/60:.1f}分钟前)")
    else:
        print("⚠️ 未发现ADS-B数据文件")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        quick_check()
    else:
        if quick_check():
            print()
            main()
        else:
            print("\n请先解决上述问题后再启动系统")
