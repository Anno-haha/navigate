#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from datetime import datetime

def test_simplified_adsb_system():
    """测试简化版ADS-B系统功能"""
    
    print("🧪 ADS-B简化版系统功能测试")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8000"
    
    # 测试1: 主页访问
    print("\n1. 测试主页访问...")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("   ✅ 主页访问成功")
            print(f"   📄 页面大小: {len(response.content)} 字节")
            
            # 检查是否包含关键元素
            content = response.text
            if "ADS-B实时可视化系统" in content:
                print("   ✅ 页面标题正确")
            if "radar-view" in content:
                print("   ✅ 雷达视图元素存在")
            if "Three.js" not in content and "WebGL" not in content:
                print("   ✅ 确认已移除3D相关代码")
            else:
                print("   ⚠️  可能仍包含3D相关代码")
        else:
            print(f"   ❌ 主页访问失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 主页访问错误: {e}")
    
    # 测试2: API接口
    print("\n2. 测试API接口...")
    try:
        response = requests.get(f"{base_url}/api/aircraft/", timeout=5)
        if response.status_code == 200:
            print("   ✅ API接口访问成功")
            
            data = response.json()
            print(f"   📊 返回数据: {data.get('status', 'unknown')}")
            print(f"   ✈️  飞机数量: {data.get('count', 0)}")
            
            # 检查数据结构
            if 'aircraft' in data and isinstance(data['aircraft'], list):
                print("   ✅ 数据结构正确")
                
                if len(data['aircraft']) > 0:
                    aircraft = data['aircraft'][0]
                    required_fields = ['icao', 'lat', 'lon', 'alt', 'timestamp']
                    missing_fields = [field for field in required_fields if field not in aircraft]
                    
                    if not missing_fields:
                        print("   ✅ 飞机数据字段完整")
                        print(f"   📍 示例飞机: {aircraft['icao']} - {aircraft['alt']}ft")
                    else:
                        print(f"   ⚠️  缺少字段: {missing_fields}")
                else:
                    print("   ⚠️  当前无飞机数据")
            else:
                print("   ❌ 数据结构错误")
        else:
            print(f"   ❌ API访问失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API访问错误: {e}")
    
    # 测试3: 性能指标
    print("\n3. 测试性能指标...")
    try:
        start_time = datetime.now()
        response = requests.get(base_url, timeout=5)
        end_time = datetime.now()
        
        load_time = (end_time - start_time).total_seconds()
        page_size = len(response.content)
        
        print(f"   ⏱️  页面加载时间: {load_time:.2f}秒")
        print(f"   📦 页面大小: {page_size / 1024:.1f} KB")
        
        if load_time < 2.0:
            print("   ✅ 加载速度优秀")
        elif load_time < 5.0:
            print("   ✅ 加载速度良好")
        else:
            print("   ⚠️  加载速度较慢")
            
        if page_size < 100000:  # 100KB
            print("   ✅ 页面大小合理")
        else:
            print("   ⚠️  页面大小较大")
            
    except Exception as e:
        print(f"   ❌ 性能测试错误: {e}")
    
    # 测试4: 功能特性检查
    print("\n4. 测试功能特性...")
    try:
        response = requests.get(base_url, timeout=5)
        content = response.text
        
        features = {
            "2D雷达视图": "radar-container" in content,
            "飞机列表": "aircraft-list" in content,
            "统计面板": "stats-grid" in content,
            "自动刷新": "toggleAutoRefresh" in content,
            "响应式设计": "@media" in content,
            "键盘快捷键": "keydown" in content,
            "无3D依赖": "Three.js" not in content and "WebGL" not in content
        }
        
        for feature, exists in features.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {feature}")
            
    except Exception as e:
        print(f"   ❌ 功能检查错误: {e}")
    
    # 测试5: 数据实时性
    print("\n5. 测试数据实时性...")
    try:
        response = requests.get(f"{base_url}/api/aircraft/", timeout=5)
        data = response.json()
        
        if data.get('count', 0) > 0:
            aircraft_list = data['aircraft']
            current_time = datetime.now()
            
            recent_count = 0
            for aircraft in aircraft_list:
                try:
                    timestamp = datetime.strptime(aircraft['timestamp'], '%Y-%m-%d %H:%M:%S')
                    time_diff = (current_time - timestamp).total_seconds()
                    if time_diff < 300:  # 5分钟内
                        recent_count += 1
                except:
                    pass
            
            print(f"   📊 总飞机数: {len(aircraft_list)}")
            print(f"   🟢 活跃飞机: {recent_count} (5分钟内)")
            
            if recent_count > 0:
                print("   ✅ 数据实时性良好")
            else:
                print("   ⚠️  数据可能不够新")
        else:
            print("   ⚠️  当前无飞机数据")
            
    except Exception as e:
        print(f"   ❌ 实时性测试错误: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 简化版ADS-B系统测试完成！")
    print("\n💡 访问地址:")
    print(f"   🌐 主界面: {base_url}/")
    print(f"   📊 API接口: {base_url}/api/aircraft/")
    print("\n🎮 快捷键:")
    print("   Ctrl+1: 总览视图")
    print("   Ctrl+2: 雷达视图") 
    print("   Ctrl+3: 飞机列表")
    print("   Ctrl+R: 刷新数据")

if __name__ == "__main__":
    test_simplified_adsb_system()
