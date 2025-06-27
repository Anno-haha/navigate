#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

def check_nav_py_status():
    """检查nav.py运行状态"""
    try:
        # 检查日志文件是否存在且最近有更新
        if os.path.exists('adsb_decoded.log'):
            mtime = os.path.getmtime('adsb_decoded.log')
            current_time = time.time()

            print(f"文件修改时间: {time.ctime(mtime)}")
            print(f"当前时间: {time.ctime(current_time)}")
            print(f"时间差: {current_time - mtime}秒")

            if current_time - mtime < 120:  # 2分钟内有更新
                print("[OK] 检测到nav.py正在运行，数据采集正常")
                return True
            else:
                print("[WARN] nav.py可能未运行或无数据输出")
                print(f"   日志文件最后更新: {time.ctime(mtime)}")
                return False
        else:
            print("[WARN] 未找到adsb_decoded.log文件")
            print("   请确保nav.py正在运行并生成数据")
            return False
    except Exception as e:
        print(f"[ERROR] 检查nav.py状态失败: {e}")
        return False

print("测试nav.py状态检查...")
result = check_nav_py_status()
print(f"结果: {result}")
