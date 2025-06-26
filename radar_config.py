#!/usr/bin/env python3
"""
2D雷达系统配置文件
专门优化实时性能
"""

# 雷达显示配置
RADAR_CONFIG = {
    # 实时性配置
    'update_interval_ms': 500,      # 数据更新间隔(毫秒)
    'render_fps': 60,               # 渲染帧率
    'data_fetch_timeout': 100,      # 数据获取超时(毫秒)
    
    # 雷达范围配置
    'default_range_km': 100,        # 默认雷达范围
    'available_ranges': [20, 50, 100, 200, 500],  # 可选范围
    'max_range_km': 500,            # 最大雷达范围
    
    # 显示配置
    'show_sweep_animation': True,   # 显示扫描动画
    'show_aircraft_trails': True,   # 显示飞机轨迹
    'show_aircraft_labels': True,   # 显示飞机标签
    'show_grid': True,              # 显示网格
    'show_range_rings': True,       # 显示距离环
    
    # 性能优化配置
    'max_trail_points': 30,         # 最大轨迹点数
    'trail_fade_time': 60,          # 轨迹淡出时间(秒)
    'aircraft_expire_time': 300,    # 飞机数据过期时间(秒)
    'cleanup_interval': 30,         # 数据清理间隔(秒)
    
    # 颜色配置
    'colors': {
        'background': '#000011',
        'grid': '#00ff0030',
        'grid_text': '#00ff0060',
        'sweep_line': '#00ff00',
        'aircraft_low': '#ff4444',      # 低空(<10000ft)
        'aircraft_mid': '#ffff44',      # 中空(10000-33000ft)
        'aircraft_high': '#4444ff',     # 高空(>33000ft)
        'trail_alpha': '60',            # 轨迹透明度
        'text': '#ffffff',
        'selected': '#ff00ff',
    },
    
    # 参考点配置
    'reference_point': {
        'latitude': 39.9,   # 北京纬度
        'longitude': 116.4, # 北京经度
        'altitude': 10000,  # 参考高度(米)
        'name': '北京上空'
    },
    
    # 网络配置
    'server': {
        'host': '127.0.0.1',
        'port_start': 8001,
        'port_range': 10,
        'enable_cors': True,
        'cache_control': 'no-cache',
    },
    
    # 调试配置
    'debug': {
        'show_performance': True,   # 显示性能信息
        'show_fps': True,          # 显示FPS
        'show_latency': True,      # 显示网络延迟
        'log_aircraft_count': True, # 记录飞机数量
        'verbose_logging': False,   # 详细日志
    }
}

# 性能预设配置
PERFORMANCE_PRESETS = {
    'high_performance': {
        'update_interval_ms': 250,
        'render_fps': 60,
        'max_trail_points': 50,
        'show_sweep_animation': True,
        'show_aircraft_trails': True,
    },
    
    'balanced': {
        'update_interval_ms': 500,
        'render_fps': 30,
        'max_trail_points': 30,
        'show_sweep_animation': True,
        'show_aircraft_trails': True,
    },
    
    'low_resource': {
        'update_interval_ms': 1000,
        'render_fps': 15,
        'max_trail_points': 10,
        'show_sweep_animation': False,
        'show_aircraft_trails': False,
    }
}

def get_config(preset=None):
    """获取配置"""
    config = RADAR_CONFIG.copy()
    
    if preset and preset in PERFORMANCE_PRESETS:
        config.update(PERFORMANCE_PRESETS[preset])
    
    return config

def apply_performance_preset(preset_name):
    """应用性能预设"""
    if preset_name not in PERFORMANCE_PRESETS:
        raise ValueError(f"未知的性能预设: {preset_name}")
    
    preset = PERFORMANCE_PRESETS[preset_name]
    RADAR_CONFIG.update(preset)
    
    print(f"已应用性能预设: {preset_name}")
    return RADAR_CONFIG

def optimize_for_aircraft_count(aircraft_count):
    """根据飞机数量优化配置"""
    if aircraft_count > 100:
        # 大量飞机时降低性能要求
        RADAR_CONFIG.update({
            'update_interval_ms': 1000,
            'max_trail_points': 10,
            'show_sweep_animation': False,
        })
        print("检测到大量飞机，已切换到低资源模式")
    
    elif aircraft_count > 50:
        # 中等数量飞机时平衡性能
        RADAR_CONFIG.update({
            'update_interval_ms': 750,
            'max_trail_points': 20,
            'show_sweep_animation': True,
        })
        print("检测到中等数量飞机，已切换到平衡模式")
    
    else:
        # 少量飞机时最高性能
        RADAR_CONFIG.update({
            'update_interval_ms': 500,
            'max_trail_points': 30,
            'show_sweep_animation': True,
        })
    
    return RADAR_CONFIG

def get_color_scheme(scheme='default'):
    """获取颜色方案"""
    color_schemes = {
        'default': RADAR_CONFIG['colors'],
        
        'green_radar': {
            'background': '#000000',
            'grid': '#00ff0040',
            'grid_text': '#00ff0080',
            'sweep_line': '#00ff00',
            'aircraft_low': '#00ff00',
            'aircraft_mid': '#80ff80',
            'aircraft_high': '#40ff40',
            'trail_alpha': '80',
            'text': '#00ff00',
            'selected': '#ffff00',
        },
        
        'blue_radar': {
            'background': '#000011',
            'grid': '#0080ff40',
            'grid_text': '#0080ff80',
            'sweep_line': '#0080ff',
            'aircraft_low': '#ff4040',
            'aircraft_mid': '#ffff40',
            'aircraft_high': '#4040ff',
            'trail_alpha': '60',
            'text': '#ffffff',
            'selected': '#ff8000',
        },
        
        'night_vision': {
            'background': '#001100',
            'grid': '#00ff0020',
            'grid_text': '#00ff0040',
            'sweep_line': '#00ff0080',
            'aircraft_low': '#ff0000',
            'aircraft_mid': '#ffff00',
            'aircraft_high': '#00ff00',
            'trail_alpha': '40',
            'text': '#00ff00',
            'selected': '#ffffff',
        }
    }
    
    return color_schemes.get(scheme, color_schemes['default'])

def validate_config(config):
    """验证配置有效性"""
    errors = []
    
    # 检查必需字段
    required_fields = ['update_interval_ms', 'render_fps', 'default_range_km']
    for field in required_fields:
        if field not in config:
            errors.append(f"缺少必需配置: {field}")
    
    # 检查数值范围
    if config.get('update_interval_ms', 0) < 100:
        errors.append("update_interval_ms 不能小于100ms")
    
    if config.get('render_fps', 0) > 120:
        errors.append("render_fps 不建议超过120")
    
    if config.get('max_trail_points', 0) > 100:
        errors.append("max_trail_points 过大可能影响性能")
    
    return errors

def print_current_config():
    """打印当前配置"""
    print("当前雷达配置:")
    print("=" * 40)
    print(f"更新间隔: {RADAR_CONFIG['update_interval_ms']}ms")
    print(f"渲染帧率: {RADAR_CONFIG['render_fps']} FPS")
    print(f"默认范围: {RADAR_CONFIG['default_range_km']} km")
    print(f"最大轨迹点: {RADAR_CONFIG['max_trail_points']}")
    print(f"扫描动画: {'开启' if RADAR_CONFIG['show_sweep_animation'] else '关闭'}")
    print(f"飞机轨迹: {'开启' if RADAR_CONFIG['show_aircraft_trails'] else '关闭'}")
    print(f"飞机标签: {'开启' if RADAR_CONFIG['show_aircraft_labels'] else '关闭'}")
    print("=" * 40)

if __name__ == '__main__':
    # 测试配置
    print("雷达配置测试")
    print_current_config()
    
    # 测试性能预设
    print("\n应用高性能预设:")
    apply_performance_preset('high_performance')
    print_current_config()
    
    # 测试配置验证
    print("\n配置验证:")
    errors = validate_config(RADAR_CONFIG)
    if errors:
        print("发现配置错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("配置验证通过")
