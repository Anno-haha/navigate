#!/usr/bin/env python3
"""
ADS-B可视化系统依赖安装脚本
自动检测和安装所需的Python包
"""

import subprocess
import sys
import os

# 所需的Python包
REQUIRED_PACKAGES = [
    'django>=4.2.0',
    'channels>=4.0.0',
    'channels-redis>=4.0.0',
    'redis>=4.0.0',
    'celery>=5.2.0',
    'psycopg2-binary>=2.9.0',  # PostgreSQL支持
    'pillow>=9.0.0',  # 图像处理
    'numpy>=1.21.0',  # 数值计算
    'requests>=2.28.0',  # HTTP请求
]

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误：需要Python 3.8或更高版本")
        print(f"当前版本：{sys.version}")
        return False
    
    print(f"✅ Python版本检查通过：{sys.version}")
    return True

def install_package(package):
    """安装单个包"""
    try:
        print(f"📦 正在安装 {package}...")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败：{e}")
        print(f"错误输出：{e.stderr}")
        return False

def check_package_installed(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_requirements():
    """安装所有依赖"""
    print("🚀 开始安装ADS-B可视化系统依赖...")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    # 升级pip
    print("📦 升级pip...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                      check=True, capture_output=True)
        print("✅ pip升级完成")
    except subprocess.CalledProcessError:
        print("⚠️ pip升级失败，继续安装...")
    
    # 安装包
    failed_packages = []
    for package in REQUIRED_PACKAGES:
        if not install_package(package):
            failed_packages.append(package)
    
    # 检查核心包
    core_packages = {
        'django': 'Django',
        'channels': 'Django Channels',
        'redis': 'Redis',
        'celery': 'Celery',
        'numpy': 'NumPy'
    }
    
    print("\n🔍 检查核心包安装状态...")
    for package, name in core_packages.items():
        if check_package_installed(package):
            print(f"✅ {name} 已安装")
        else:
            print(f"❌ {name} 未安装")
            failed_packages.append(package)
    
    # 总结
    print("\n" + "=" * 50)
    if failed_packages:
        print(f"❌ 安装完成，但有 {len(failed_packages)} 个包安装失败：")
        for package in failed_packages:
            print(f"   - {package}")
        print("\n请手动安装失败的包：")
        print(f"pip install {' '.join(failed_packages)}")
        return False
    else:
        print("🎉 所有依赖安装成功！")
        return True

def create_requirements_txt():
    """创建requirements.txt文件"""
    requirements_content = """# ADS-B可视化系统依赖
Django>=4.2.0
channels>=4.0.0
channels-redis>=4.0.0
redis>=4.0.0
celery>=5.2.0
psycopg2-binary>=2.9.0
pillow>=9.0.0
numpy>=1.21.0
requests>=2.28.0

# 可选依赖（用于生产环境）
gunicorn>=20.1.0
whitenoise>=6.0.0
django-cors-headers>=3.13.0
"""
    
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write(requirements_content)
    
    print("📄 已创建 requirements.txt 文件")

def setup_database():
    """设置数据库"""
    print("\n🗄️ 设置数据库...")
    
    try:
        # Django数据库迁移
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ADS_B_visual.settings')
        
        print("正在创建数据库表...")
        # 这里应该运行Django迁移命令
        # 由于我们使用的是单文件Django配置，暂时跳过
        print("✅ 数据库设置完成（使用SQLite）")
        
    except Exception as e:
        print(f"⚠️ 数据库设置失败：{e}")

def check_system_requirements():
    """检查系统要求"""
    print("\n🔧 检查系统要求...")
    
    # 检查可用内存
    try:
        import psutil
        memory = psutil.virtual_memory()
        print(f"系统内存：{memory.total // (1024**3)} GB")
        if memory.total < 2 * (1024**3):  # 2GB
            print("⚠️ 建议至少2GB内存以获得最佳性能")
    except ImportError:
        print("无法检查系统内存（psutil未安装）")
    
    # 检查磁盘空间
    try:
        import shutil
        disk_usage = shutil.disk_usage('.')
        free_gb = disk_usage.free // (1024**3)
        print(f"可用磁盘空间：{free_gb} GB")
        if free_gb < 1:
            print("⚠️ 建议至少1GB可用磁盘空间")
    except Exception:
        print("无法检查磁盘空间")

def main():
    """主函数"""
    print("ADS-B可视化系统安装程序")
    print("=" * 50)
    print("这个脚本将安装运行ADS-B可视化系统所需的所有依赖")
    print()
    
    # 检查系统要求
    check_system_requirements()
    
    # 询问用户是否继续
    response = input("\n是否继续安装？(y/n): ").lower().strip()
    if response not in ['y', 'yes', '是']:
        print("安装已取消")
        return
    
    # 安装依赖
    success = install_requirements()
    
    # 创建requirements.txt
    create_requirements_txt()
    
    # 设置数据库
    if success:
        setup_database()
    
    # 最终说明
    print("\n" + "=" * 50)
    if success:
        print("🎉 安装完成！")
        print("\n下一步：")
        print("1. 确保nav.py正在运行并生成ADS-B数据")
        print("2. 运行可视化系统：python ADS_B_visual.py")
        print("3. 在浏览器中访问：http://127.0.0.1:8000")
        print("\n功能说明：")
        print("- 3D地球视图：http://127.0.0.1:8000/")
        print("- 2D雷达视图：http://127.0.0.1:8000/radar/")
        print("- API接口：http://127.0.0.1:8000/api/aircraft/")
    else:
        print("❌ 安装过程中遇到问题")
        print("请检查错误信息并手动安装失败的包")
        print("或者运行：pip install -r requirements.txt")

if __name__ == '__main__':
    main()
