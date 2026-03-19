#!/usr/bin/env python3
"""
Clash配置解析器测试脚本
用于测试核心解析功能
"""

import os
import sys
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from business.clash_processor import (
        ClashProxy,
        ClashConfigAnalysis,
        parse_clash_yaml,
        extract_proxies_from_config,
        analyze_proxy_types,
        convert_proxy_to_link
    )
    print("✓ 成功导入模块")
except Exception as e:
    print(f"✗ 导入模块失败: {e}")
    print("请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)


def test_yaml_parsing():
    """测试YAML解析"""
    print("\n=== 测试YAML解析 ===")
    
    # 创建一个简单的Clash配置
    test_yaml = """
port: 7890
socks-port: 7891
mode: rule
proxies:
  - name: "Test SS"
    type: ss
    server: example.com
    port: 443
    cipher: aes-256-gcm
    password: test123
    udp: true
    
  - name: "Test VMess"
    type: vmess
    server: vmess.example.com
    port: 8443
    uuid: 12345678-1234-1234-1234-123456789012
    alterId: 0
    cipher: auto
    tls: true
    skip-cert-verify: true
    network: ws
    ws-opts:
      path: /path
      headers:
        Host: example.com
"""
    
    try:
        config = parse_clash_yaml(test_yaml)
        print(f"✓ YAML解析成功")
        print(f"  配置键: {list(config.keys())}")
        return config
    except Exception as e:
        print(f"✗ YAML解析失败: {e}")
        return None


def test_proxy_extraction(config):
    """测试代理提取"""
    print("\n=== 测试代理提取 ===")
    
    if not config:
        print("✗ 无配置数据，跳过测试")
        return []
    
    proxies = extract_proxies_from_config(config)
    print(f"✓ 提取到 {len(proxies)} 个代理")
    
    for i, proxy in enumerate(proxies):
        print(f"  代理 {i+1}: {proxy.name} ({proxy.type}) {proxy.server}:{proxy.port}")
    
    return proxies


def test_type_analysis(proxies):
    """测试类型分析"""
    print("\n=== 测试类型分析 ===")
    
    if not proxies:
        print("✗ 无代理数据，跳过测试")
        return {}
    
    type_stats = analyze_proxy_types(proxies)
    print(f"✓ 类型分析结果:")
    
    for proxy_type, count in type_stats.items():
        print(f"  {proxy_type}: {count}")
    
    return type_stats


def test_link_conversion(proxies):
    """测试链接转换"""
    print("\n=== 测试链接转换 ===")
    
    if not proxies:
        print("✗ 无代理数据，跳过测试")
        return []
    
    links = []
    for proxy in proxies:
        link = convert_proxy_to_link(proxy)
        if link:
            links.append(link)
            print(f"  {proxy.type}: {link[:80]}...")
        else:
            print(f"  {proxy.type}: 不支持的类型或转换失败")
    
    print(f"✓ 生成 {len(links)} 个链接")
    return links


def test_sample_files():
    """测试实际配置文件"""
    print("\n=== 测试实际配置文件 ===")
    
    # 检查下载的配置文件
    sample_dir = "/work/code-work/demo3/clash-configs"
    if os.path.exists(sample_dir):
        print(f"✓ 找到示例配置目录: {sample_dir}")
        
        yaml_files = [f for f in os.listdir(sample_dir) if f.endswith('.yaml')]
        print(f"  找到 {len(yaml_files)} 个配置文件")
        
        for yaml_file in yaml_files[:2]:  # 只测试前2个
            file_path = os.path.join(sample_dir, yaml_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                config = parse_clash_yaml(content)
                proxies = extract_proxies_from_config(config)
                type_stats = analyze_proxy_types(proxies)
                
                print(f"\n  文件: {yaml_file}")
                print(f"    代理数: {len(proxies)}")
                print(f"    类型分布: {type_stats}")
                
                # 显示前几个代理
                for i, proxy in enumerate(proxies[:3]):
                    print(f"    代理 {i+1}: {proxy.name} ({proxy.type})")
                    
            except Exception as e:
                print(f"  ✗ 处理 {yaml_file} 失败: {e}")
    else:
        print(f"✗ 示例配置目录不存在: {sample_dir}")


def main():
    """主测试函数"""
    print("Clash配置解析器测试")
    print("=" * 50)
    
    # 测试1: YAML解析
    config = test_yaml_parsing()
    
    # 测试2: 代理提取
    proxies = test_proxy_extraction(config)
    
    # 测试3: 类型分析
    type_stats = test_type_analysis(proxies)
    
    # 测试4: 链接转换
    links = test_link_conversion(proxies)
    
    # 测试5: 实际配置文件
    test_sample_files()
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试完成!")
    print(f"- YAML解析: {'成功' if config else '失败'}")
    print(f"- 代理提取: {len(proxies)} 个")
    print(f"- 类型分析: {len(type_stats)} 种类型")
    print(f"- 链接转换: {len(links)} 个链接")
    
    if config and proxies and type_stats:
        print("\n✓ 所有核心功能测试通过!")
        return True
    else:
        print("\n✗ 部分测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)