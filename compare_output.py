#!/usr/bin/env python3
"""
对比main.py和nav.py的输出结果
验证重构后的功能是否正确
"""

import subprocess
import time
import threading
import queue
import signal
import sys

def run_program(program_name, output_queue, duration=10):
    """运行程序并收集输出"""
    try:
        process = subprocess.Popen(
            [sys.executable, program_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        start_time = time.time()
        outputs = []
        
        while time.time() - start_time < duration:
            line = process.stdout.readline()
            if line:
                line = line.strip()
                if "ICAO:" in line or "✈️" in line:  # 只收集飞机数据输出
                    outputs.append(line)
                    print(f"[{program_name}] {line}")
            elif process.poll() is not None:
                break
                
        process.terminate()
        process.wait(timeout=2)
        output_queue.put((program_name, outputs))
        
    except Exception as e:
        print(f"运行 {program_name} 时出错: {e}")
        output_queue.put((program_name, []))

def extract_aircraft_data(line):
    """从输出行中提取飞机数据"""
    if "ICAO:" in line:
        # main.py格式: ICAO: 781CDB | 纬度: 39.107941° | 经度: 117.356435° | 高度: 1025英尺
        parts = line.split(" | ")
        if len(parts) >= 4:
            icao = parts[0].split(": ")[1]
            lat = parts[1].split(": ")[1].replace("°", "")
            lon = parts[2].split(": ")[1].replace("°", "")
            alt = parts[3].split(": ")[1].replace("英尺", "")
            return icao, float(lat), float(lon), int(alt)
    elif "✈️" in line:
        # nav.py格式: ✈️ ICAO:780CBE 位置:(39.278229°, 117.326401°) 高度:24600ft
        if "ICAO:" in line and "位置:" in line and "高度:" in line:
            icao_part = line.split("ICAO:")[1].split(" ")[0]
            pos_part = line.split("位置:(")[1].split(")")[0]
            alt_part = line.split("高度:")[1].replace("ft", "")
            
            lat, lon = pos_part.replace("°", "").split(", ")
            return icao_part, float(lat), float(lon), int(alt_part)
    
    return None

def compare_outputs(main_outputs, nav_outputs):
    """比较两个程序的输出"""
    print("\n" + "="*60)
    print("输出对比分析")
    print("="*60)
    
    main_data = []
    nav_data = []
    
    for line in main_outputs:
        data = extract_aircraft_data(line)
        if data:
            main_data.append(data)
    
    for line in nav_outputs:
        data = extract_aircraft_data(line)
        if data:
            nav_data.append(data)
    
    print(f"main.py 解码数据条数: {len(main_data)}")
    print(f"nav.py 解码数据条数: {len(nav_data)}")
    
    if main_data and nav_data:
        print("\n数据样本对比:")
        print("main.py 样本:", main_data[0] if main_data else "无数据")
        print("nav.py 样本:", nav_data[0] if nav_data else "无数据")
        
        # 检查是否有相同的ICAO
        main_icaos = set(data[0] for data in main_data)
        nav_icaos = set(data[0] for data in nav_data)
        common_icaos = main_icaos & nav_icaos
        
        print(f"\n共同检测到的飞机: {len(common_icaos)}")
        if common_icaos:
            print(f"ICAO列表: {list(common_icaos)}")
    
    return len(main_data), len(nav_data)

def main():
    """主函数"""
    print("ADS-B程序输出对比测试")
    print("="*40)
    print("将同时运行main.py和nav.py 10秒钟")
    print("对比它们的解码输出结果")
    print("按Ctrl+C可提前停止")
    print()
    
    output_queue = queue.Queue()
    
    # 创建线程运行两个程序
    main_thread = threading.Thread(
        target=run_program, 
        args=("main.py", output_queue, 10)
    )
    nav_thread = threading.Thread(
        target=run_program, 
        args=("nav.py", output_queue, 10)
    )
    
    try:
        print("启动程序...")
        main_thread.start()
        time.sleep(1)  # 错开启动时间
        nav_thread.start()
        
        # 等待线程完成
        main_thread.join()
        nav_thread.join()
        
        # 收集结果
        results = {}
        while not output_queue.empty():
            program, outputs = output_queue.get()
            results[program] = outputs
        
        # 对比结果
        main_outputs = results.get("main.py", [])
        nav_outputs = results.get("nav.py", [])
        
        main_count, nav_count = compare_outputs(main_outputs, nav_outputs)
        
        print("\n" + "="*60)
        print("测试结论:")
        if main_count > 0 and nav_count > 0:
            ratio = nav_count / main_count if main_count > 0 else 0
            print(f"✅ 两个程序都能正常解码数据")
            print(f"📊 解码效率对比: nav.py/main.py = {ratio:.2f}")
            if ratio >= 0.8:
                print("🎉 nav.py重构成功！解码效率良好")
            else:
                print("⚠️  nav.py解码效率较低，需要优化")
        elif nav_count > 0:
            print("✅ nav.py能正常工作")
            print("⚠️  main.py在测试期间无输出")
        elif main_count > 0:
            print("✅ main.py能正常工作")
            print("❌ nav.py在测试期间无输出，需要检查")
        else:
            print("❌ 两个程序都无输出，可能串口无数据或连接问题")
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    main()
