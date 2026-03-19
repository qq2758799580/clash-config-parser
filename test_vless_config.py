#!/usr/bin/env python3
"""
测试VLESS配置解析
"""

import sys
sys.path.insert(0, '.')

from business.clash_processor import ClashProxy, convert_proxy_to_link
from urllib.parse import unquote

def test_vless_config():
    """测试提供的VLESS配置"""
    
    # 模拟代理数据
    data = {
        'name': 'fr-000',
        'type': 'vless',
        'server': '213.176.73.206',
        'port': 2083,
        'uuid': '95abaefc-7861-417a-81b7-166cb788ce1a',
        'encryption': 'none',
        'udp': True,
        'skip-cert-verify': False,
        'tfo': False,
        'tls': True,
        'reality-opts': {
            'public-key': 'J6NuOlIq3ypdTFc1TMhDDKmF8BWPnNWZq1EkxD7K-lQ',
            'short-id': '6da16b1335651b38'
        },
        'servername': 'apple.com',
        'client-fingerprint': 'chrome',
        'network': 'grpc',
        'grpc-opts': {
            'grpc-service-name': 'UpdateService',
            'grpc-dial-options': {
                'with-insecure-skip-verify': False
            }
        }
    }
    
    # 创建代理对象
    proxy = ClashProxy(
        name=data['name'],
        type=data['type'],
        server=data['server'],
        port=data['port'],
        data=data
    )
    
    # 转换
    result = convert_proxy_to_link(proxy)
    
    print("=== VLESS配置解析测试 ===")
    print(f"原始配置: {data}")
    print(f"生成的链接: {result}")
    
    if result:
        # 解析链接
        parts = result.split('#')
        base = parts[0]
        remark = unquote(parts[1]) if len(parts) > 1 else ''
        
        print(f"\n解码备注: {remark}")
        
        # 检查参数
        if '?' in base:
            url, params = base.split('?', 1)
            params_list = params.split('&')
            print(f"\nURL: {url}")
            print("参数:")
            for param in params_list:
                print(f"  {param}")
        
        # 检查关键参数是否存在
        expected_params = [
            ('95abaefc-7861-417a-81b7-166cb788ce1a', 'UUID匹配'),
            ('@213.176.73.206:2083', '服务器端口匹配'),
            ('security=tls', 'TLS安全模式'),
            ('sni=apple.com', 'SNI配置'),
            ('fp=chrome', '客户端指纹'),
            ('type=grpc', 'gRPC传输'),
            ('serviceName=UpdateService', 'gRPC服务名'),
            ('encryption=', '加密配置（应该不存在，因为encryption=none）')
        ]
        
        print("\n=== 参数验证 ===")
        all_present = True
        for param, desc in expected_params:
            if param == 'encryption=':
                # encryption=none 不应该出现在链接中
                if 'encryption' in result:
                    print(f"❌ {desc}: encryption参数不应出现（因为值为none）")
                    all_present = False
                else:
                    print(f"✅ {desc}: encryption参数正确省略")
            else:
                if param in result:
                    print(f"✅ {desc}: 存在")
                else:
                    print(f"❌ {desc}: 缺失")
                    all_present = False
        
        # 检查reality-opts（不应该出现，因为tls是true不是reality）
        if 'pbk=' in result:
            print(f"❌ reality-opts参数: 不应出现，因为tls=true，不是reality")
            all_present = False
        else:
            print(f"✅ reality-opts参数: 正确省略（tls=true模式）")
        
        # 检查skip-cert-verify=false是否处理正确
        if 'allowInsecure=1' in result:
            print(f"❌ allowInsecure参数: 不应出现，因为skip-cert-verify=false")
            all_present = False
        else:
            print(f"✅ allowInsecure参数: 正确省略（skip-cert-verify=false）")
        
        return all_present
    else:
        print("❌ 转换失败，返回None")
        return False

if __name__ == "__main__":
    success = test_vless_config()
    print(f"\n=== 测试结果: {'成功' if success else '失败'} ===")
    sys.exit(0 if success else 1)