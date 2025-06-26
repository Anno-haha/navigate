#!/usr/bin/env python3
"""
ADS-B可视化系统启动脚本
检查环境并启动可视化系统
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime

def check_nav_py_running():
    """检查nav.py是否在运行"""
    try:
        # 检查是否有adsb_decoded.log文件
        if os.path.exists('adsb_decoded.log'):
            # 检查文件是否在最近更新
            mtime = os.path.getmtime('adsb_decoded.log')
            current_time = time.time()
            
            if current_time - mtime < 60:  # 1分钟内有更新
                return True
        
        return False
    except Exception:
        return False

def check_dependencies():
    """检查依赖是否安装"""
    required_modules = ['django', 'channels', 'redis']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    return missing_modules

def start_nav_py():
    """启动nav.py"""
    print("🚀 启动nav.py数据采集程序...")
    
    if not os.path.exists('nav.py'):
        print("❌ 找不到nav.py文件")
        return None
    
    try:
        # 在后台启动nav.py
        process = subprocess.Popen(
            [sys.executable, 'nav.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"✅ nav.py已启动 (PID: {process.pid})")
        return process
    
    except Exception as e:
        print(f"❌ 启动nav.py失败: {e}")
        return None

def monitor_nav_py(process):
    """监控nav.py进程"""
    if not process:
        return
    
    def monitor():
        while True:
            if process.poll() is not None:
                print("⚠️ nav.py进程已停止")
                break
            time.sleep(10)
    
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

def start_visualization():
    """启动可视化系统"""
    print("🌐 启动ADS-B可视化系统...")
    
    try:
        # 导入并运行可视化系统
        import ADS_B_visual
        ADS_B_visual.main()
    
    except ImportError as e:
        print(f"❌ 导入可视化系统失败: {e}")
        print("请确保所有依赖都已安装")
    except Exception as e:
        print(f"❌ 启动可视化系统失败: {e}")

def show_system_info():
    """显示系统信息"""
    print("ADS-B可视化系统启动器")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    print("=" * 50)

def show_usage_info():
    """显示使用说明"""
    print("\n📖 使用说明:")
    print("1. 确保ADS-B接收器已连接并工作正常")
    print("2. nav.py将自动采集ADS-B数据")
    print("3. 可视化系统将实时显示飞机位置")
    print("\n🌐 访问地址:")
    print("- 3D地球视图: http://127.0.0.1:8000/")
    print("- 2D雷达视图: http://127.0.0.1:8000/radar/")
    print("- API接口: http://127.0.0.1:8000/api/aircraft/")
    print("\n⌨️ 快捷键:")
    print("- Ctrl+C: 停止系统")
    print("- 浏览器刷新: 重新加载界面")

def main():
    """主函数"""
    show_system_info()
    
    # 检查依赖
    print("🔍 检查系统依赖...")
    missing_deps = check_dependencies()
    
    if missing_deps:
        print(f"❌ 缺少依赖: {', '.join(missing_deps)}")
        print("请先运行: python install_requirements.py")
        return
    
    print("✅ 依赖检查通过")
    
    # 检查nav.py状态
    print("\n🔍 检查数据采集状态...")
    nav_running = check_nav_py_running()
    nav_process = None
    
    if nav_running:
        print("✅ nav.py正在运行，数据采集正常")
    else:
        print("⚠️ nav.py未运行或无数据输出")
        
        response = input("是否启动nav.py数据采集? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            nav_process = start_nav_py()
            if nav_process:
                monitor_nav_py(nav_process)
                # 等待nav.py启动
                print("等待数据采集启动...")
                time.sleep(3)
            else:
                print("⚠️ nav.py启动失败，可视化系统将显示空数据")
        else:
            print("⚠️ 继续启动可视化系统（可能无数据显示）")
    
    # 显示使用说明
    show_usage_info()
    
    # 启动可视化系统
    print("\n🚀 启动可视化系统...")
    print("请稍候，正在初始化...")
    
    try:
        start_visualization()
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止系统...")
        
        # 停止nav.py进程
        if nav_process and nav_process.poll() is None:
            print("停止nav.py进程...")
            nav_process.terminate()
            nav_process.wait(timeout=5)
        
        print("✅ 系统已停止")
    
    except Exception as e:
        print(f"\n❌ 系统运行出错: {e}")
        
        # 清理进程
        if nav_process and nav_process.poll() is None:
            nav_process.terminate()

def quick_start():
    """快速启动模式"""
    print("🚀 ADS-B可视化系统 - 快速启动")
    print("=" * 40)
    
    # 检查基本文件
    required_files = ['nav.py', 'ADS_B_visual.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ 缺少文件: {', '.join(missing_files)}")
        return
    
    # 直接启动
    try:
        import ADS_B_visual
        ADS_B_visual.main()
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == '__main__':
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_start()
    else:
        main()
