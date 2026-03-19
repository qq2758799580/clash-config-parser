import yaml
import httpx
import base64
import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urlunparse, quote, unquote
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _add_common_params(data: dict, query_params: list, use_semicolon_separator: bool = False) -> None:
    """添加所有协议通用的可选参数
    
    Args:
        data: 代理配置字典
        query_params: 查询参数列表（原地修改）
        use_semicolon_separator: 是否使用分号分隔参数（某些SS客户端使用）
    """
    # UDP设置（默认true，只有false时添加）
    if not data.get('udp', True):
        query_params.append('udp=false')
    
    # TCP Fast Open（默认false，只有true时添加）
    if data.get('tcp-fast-open', False):
        query_params.append('tfo=true')
    
    # HTTP复用设置
    if data.get('mux', False):
        query_params.append('mux=true')
        mux_concurrency = data.get('mux-concurrency', 8)
        if mux_concurrency != 8:
            query_params.append(f'mux-concurrency={mux_concurrency}')
    
    # 跳过证书验证
    if data.get('skip-cert-verify', False):
        query_params.append('allowInsecure=1')
    
    # 客户端指纹
    if 'client-fingerprint' in data:
        query_params.append(f'fp={data["client-fingerprint"]}')
    
    # IP版本（ipv4/ipv6）
    if 'ip-version' in data:
        ip_version = data['ip-version']
        if ip_version in ['ipv4', 'ipv6']:
            query_params.append(f'ipversion={ip_version}')
    
    # 数据包间隔（用于伪装）
    if 'packet-addr' in data:
        query_params.append(f'packet_addr={data["packet-addr"]}')
    
    # 如果使用分号分隔，将参数合并
    if use_semicolon_separator and query_params:
        # 将现有的参数列表合并为分号分隔的字符串
        param_str = ';'.join(query_params)
        query_params.clear()
        query_params.append(param_str)


class ClashProxy(BaseModel):
    """Clash代理节点"""
    name: str
    type: str  # ss, ssr, vmess, vless, trojan, socks5, http, hysteria2, etc.
    server: str
    port: int
    data: Dict[str, Any]  # 原始数据


class ClashConfigAnalysis(BaseModel):
    """Clash配置分析结果"""
    url: str
    filename: str
    proxies: List[ClashProxy]
    proxy_types: Dict[str, int]  # 类型统计
    links: Optional[List[str]] = None  # 转换后的链接
    error: Optional[str] = None


def fetch_clash_config(url: str) -> str:
    """
    从URL获取Clash配置
    
    Args:
        url: Clash配置URL
        
    Returns:
        YAML配置内容
    """
    try:
        logger.info("下载Clash配置: %s", url)
        
        # 设置合理的超时
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            
            # 检测内容类型
            content_type = response.headers.get('content-type', '')
            if 'application/yaml' in content_type or 'text/yaml' in content_type:
                return response.text
            
            # 也可能是纯文本或octet-stream
            return response.text
            
    except httpx.TimeoutException:
        logger.error("下载超时: %s", url)
        raise Exception(f"下载超时: {url}")
    except httpx.HTTPError as e:
        logger.error("HTTP错误: %s, 状态码: %s", url, e.response.status_code if hasattr(e, 'response') else 'unknown')
        raise Exception(f"HTTP错误: {str(e)}")
    except Exception as e:
        logger.error("下载失败: %s, 错误: %s", url, str(e))
        raise Exception(f"下载失败: {str(e)}")


def parse_clash_yaml(yaml_content: str) -> Dict[str, Any]:
    """
    解析Clash YAML配置
    
    Args:
        yaml_content: YAML配置内容
        
    Returns:
        解析后的配置字典
    """
    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        logger.error("YAML解析错误: %s", str(e))
        raise Exception(f"YAML解析错误: {str(e)}")
    except Exception as e:
        logger.error("配置解析错误: %s", str(e))
        raise Exception(f"配置解析错误: {str(e)}")


def _is_base64_encoded(content: str) -> bool:
    """检测内容是否是base64编码"""
    # 去除空白字符
    content = content.strip()
    
    # Base64通常只包含特定字符
    base64_pattern = r'^[A-Za-z0-9+/]+={0,2}$'
    if not re.match(base64_pattern, content):
        return False
    
    # 尝试解码
    try:
        decoded = base64.b64decode(content, validate=True)
        # 解码后的内容可能是文本
        decoded_text = decoded.decode('utf-8', errors='ignore')
        # 检查解码后是否包含常见节点协议
        decoded_lower = decoded_text.lower()
        return any(proto in decoded_lower for proto in ['ss://', 'vmess://', 'vless://', 'trojan://', 'ssr://', 'http://', 'socks://'])
    except Exception:
        return False


def _parse_base64_subscription(content: str) -> List[str]:
    """解析base64编码的订阅"""
    try:
        decoded = base64.b64decode(content)
        decoded_text = decoded.decode('utf-8')
        
        # 使用正则表达式分割，支持换行和空格分隔
        segments = re.split(r'[\n\r\s]+', decoded_text)
        
        links = []
        for segment in segments:
            segment = segment.strip()
            if segment and any(segment.startswith(proto) for proto in ['ss://', 'ssr://', 'vmess://', 'vless://', 'trojan://', 'http://', 'https://', 'socks://', 'socks5://']):
                links.append(segment)
        
        return links
    except Exception as e:
        logger.error("解析base64订阅失败: %s", str(e))
        return []


def _create_proxy_from_link(link: str, index: int) -> Optional[ClashProxy]:
    """从节点链接创建ClashProxy对象"""
    try:
        # 提取协议类型
        if link.startswith('ss://'):
            proxy_type = 'ss'
        elif link.startswith('ssr://'):
            proxy_type = 'ssr'
        elif link.startswith('vmess://'):
            proxy_type = 'vmess'
        elif link.startswith('vless://'):
            proxy_type = 'vless'
        elif link.startswith('trojan://'):
            proxy_type = 'trojan'
        elif link.startswith('http://') or link.startswith('https://'):
            proxy_type = 'http'
        elif link.startswith('socks://') or link.startswith('socks5://'):
            proxy_type = 'socks5'
        else:
            proxy_type = 'unknown'
        
        # 创建基本代理对象
        name = f"link-{index}"
        
        # 尝试从链接中提取备注名
        if '#' in link:
            parts = link.split('#', 1)
            if len(parts) > 1:
                remark = unquote(parts[1])
                if remark:
                    name = remark
        
        return ClashProxy(
            name=name,
            type=proxy_type,
            server='',  # 无法从原始链接中提取
            port=0,
            data={'raw_link': link}
        )
    except Exception as e:
        logger.warning("从链接创建代理失败: %s, 错误: %s", link[:50], str(e))
        return None


def extract_proxies_from_config(config: Dict[str, Any]) -> List[ClashProxy]:
    """
    从配置中提取proxies节点
    
    Args:
        config: Clash配置字典
        
    Returns:
        代理节点列表
    """
    proxies = []
    
    if not isinstance(config, dict):
        logger.warning("配置不是字典格式")
        return proxies
    
    # 获取proxies列表
    config_proxies = config.get('proxies', [])
    
    if not isinstance(config_proxies, list):
        logger.warning("proxies不是列表格式")
        return proxies
    
    for i, proxy_data in enumerate(config_proxies):
        if not isinstance(proxy_data, dict):
            logger.warning("代理 %d 不是字典格式", i)
            continue
            
        try:
            # 提取基本字段
            name = proxy_data.get('name', f'proxy-{i}')
            proxy_type = proxy_data.get('type', 'unknown').lower()
            server = proxy_data.get('server', '')
            port = proxy_data.get('port', 0)
            
            if not server or not port:
                logger.debug("跳过无效代理: %s, server=%s, port=%s", name, server, port)
                continue
            
            # 创建代理对象
            proxy = ClashProxy(
                name=name,
                type=proxy_type,
                server=server,
                port=port,
                data=proxy_data.copy()  # 保存原始数据用于链接转换
            )
            
            proxies.append(proxy)
            logger.debug("提取代理: %s (%s) %s:%d", name, proxy_type, server, port)
            
        except Exception as e:
            logger.warning("处理代理 %d 失败: %s", i, str(e))
            continue
    
    logger.info("提取 %d 个代理节点", len(proxies))
    return proxies


def analyze_proxy_types(proxies: List[ClashProxy]) -> Dict[str, int]:
    """
    分析代理类型统计
    
    Args:
        proxies: 代理节点列表
        
    Returns:
        类型统计字典
    """
    type_stats = {}
    for proxy in proxies:
        proxy_type = proxy.type
        type_stats[proxy_type] = type_stats.get(proxy_type, 0) + 1
    
    return type_stats


def fetch_and_parse_clash_config(url: str) -> ClashConfigAnalysis:
    """
    获取并解析Clash配置
    
    Args:
        url: Clash配置URL
        
    Returns:
        配置分析结果
    """
    try:
        # 下载配置
        content = fetch_clash_config(url)
        content = content.strip()
        
        # 从URL提取文件名
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1] or 'config.yaml'
        
        # 尝试1: 检查是否已经是节点链接列表（每行一个 或 空格分隔）
        if any(proto in content.lower() for proto in ['ss://', 'vmess://', 'vless://', 'trojan://', 'ssr://']):
            logger.info("检测到原始节点链接列表")
            links = []
            proxies = []
            
            # 先按行分割，再按空白字符分割（处理空格分隔的情况）
            import re
            # 使用正则表达式分割，同时支持换行和空格分隔
            segments = re.split(r'[\n\r\s]+', content)
            
            for segment in segments:
                segment = segment.strip()
                if segment and any(segment.startswith(proto) for proto in ['ss://', 'ssr://', 'vmess://', 'vless://', 'trojan://', 'http://', 'https://', 'socks://']):
                    links.append(segment)
                    proxy = _create_proxy_from_link(segment, len(proxies))
                    if proxy:
                        proxies.append(proxy)
            
            if proxies:
                proxy_types = analyze_proxy_types(proxies)
                return ClashConfigAnalysis(
                    url=url,
                    filename=filename,
                    proxies=proxies,
                    proxy_types=proxy_types,
                    links=links  # 直接存储原始链接
                )
        
        # 尝试2: 检查是否是base64编码的订阅
        if _is_base64_encoded(content):
            logger.info("检测到base64编码的订阅")
            links = _parse_base64_subscription(content)
            proxies = []
            
            for i, link in enumerate(links):
                proxy = _create_proxy_from_link(link, i)
                if proxy:
                    proxies.append(proxy)
            
            if proxies:
                proxy_types = analyze_proxy_types(proxies)
                return ClashConfigAnalysis(
                    url=url,
                    filename=filename,
                    proxies=proxies,
                    proxy_types=proxy_types,
                    links=links  # 存储解码后的链接
                )
        
        # 尝试3: 作为YAML解析
        try:
            config = parse_clash_yaml(content)
            proxies = extract_proxies_from_config(config)
            proxy_types = analyze_proxy_types(proxies)
            
            return ClashConfigAnalysis(
                url=url,
                filename=filename,
                proxies=proxies,
                proxy_types=proxy_types
            )
        except Exception as yaml_error:
            logger.warning("YAML解析失败: %s", str(yaml_error))
            
            # 如果都失败，尝试最后的手段：检查是否包含proxies关键词
            if 'proxies:' in content or 'Proxy:' in content:
                # 可能是YAML格式但有语法错误
                raise Exception(f"YAML解析失败: {str(yaml_error)}")
            else:
                # 可能是其他格式
                raise Exception(f"无法识别的配置格式。既不是有效的YAML，也不是base64编码订阅或节点链接列表。")
        
    except Exception as e:
        logger.error("解析Clash配置失败: %s, 错误: %s", url, str(e))
        return ClashConfigAnalysis(
            url=url,
            filename='',
            proxies=[],
            proxy_types={},
            error=str(e)
        )


# 链接转换函数
def convert_proxies_to_links(proxies: List[ClashProxy]) -> List[str]:
    """
    将代理节点转换为标准链接格式
    
    Args:
        proxies: 代理节点列表
        
    Returns:
        链接列表
    """
    links = []
    
    for proxy in proxies:
        try:
            link = convert_proxy_to_link(proxy)
            if link:
                links.append(link)
        except Exception as e:
            logger.warning("转换代理链接失败: %s, 错误: %s", proxy.name, str(e))
            continue
    
    return links


def convert_proxy_to_link(proxy: ClashProxy) -> Optional[str]:
    """
    将单个代理节点转换为标准订阅链接
    
    Args:
        proxy: 代理节点
        
    Returns:
        链接字符串或None
    """
    proxy_type = proxy.type.lower()
    data = proxy.data
    
    # 如果是原始链接（从节点链接创建的代理），直接返回原始链接
    if 'raw_link' in data:
        return data['raw_link']
    
    try:
        if proxy_type == 'ss':
            # SS: ss://base64(method:password)@server:port#RemarkName
            return _convert_ss(proxy)
            
        elif proxy_type == 'ssr':
            # SSR: ssr://base64(server:port:protocol:method:obfs:password_base64/?params)#RemarkName
            return _convert_ssr(proxy)
            
        elif proxy_type == 'vmess':
            # VMess: vmess://base64(json)
            return _convert_vmess(proxy)
            
        elif proxy_type == 'vless':
            # VLESS: vless://uuid@server:port?security=tls&type=ws&host=example.com&path=/path#RemarkName
            return _convert_vless(proxy)
            
        elif proxy_type == 'trojan':
            # Trojan: trojan://password@server:port?security=tls&sni=example.com#RemarkName
            return _convert_trojan(proxy)
            
        elif proxy_type == 'hysteria' or proxy_type == 'hysteria2':
            # Hysteria2: hysteria2://password@server:port?insecure=1&sni=example.com#RemarkName
            return _convert_hysteria(proxy)
            
        elif proxy_type == 'http':
            # HTTP/HTTPS: http(s)://[username:password@]server:port
            return _convert_http(proxy)
            
        elif proxy_type == 'socks' or proxy_type == 'socks5':
            # SOCKS5: socks5://[username:password@]server:port
            return _convert_socks(proxy)
        
        elif proxy_type == 'snell':
            # Snell: snell://server:port?psk=key&obfs=http#RemarkName
            return _convert_snell(proxy)
            
        elif proxy_type == 'tuic':
            # TUIC: tuic://uuid:password@server:port?token=TOKEN&alpn=h3#RemarkName
            return _convert_tuic(proxy)
            
        elif proxy_type == 'wireguard':
            # WireGuard: wireguard://[private-key]@server:port?public-key=xxx&preshared-key=xxx&ip=[address]#RemarkName
            return _convert_wireguard(proxy)
            
        else:
            logger.debug("不支持的代理类型: %s, 名称: %s", proxy_type, proxy.name)
            # 尝试通用协议转换
            return _convert_generic(proxy)
            
    except Exception as e:
        logger.warning("转换代理链接失败: %s (%s), 错误: %s", proxy.name, proxy_type, str(e))
        return None


def _convert_ss(proxy: ClashProxy) -> Optional[str]:
    """转换Shadowsocks代理"""
    data = proxy.data
    method = data.get('cipher', 'aes-256-gcm')
    password = data.get('password', '')
    server = proxy.server
    port = proxy.port
    
    if not server or not port or not password:
        return None
    
    # Base64编码认证信息
    auth = f"{method}:{password}"
    encoded = base64.urlsafe_b64encode(auth.encode()).decode().rstrip('=')
    
    # 构建基础URL
    base_url = f"ss://{encoded}@{server}:{port}"
    
    # 查询参数（可选）
    query_params = []
    
    # 插件支持 - 特殊处理分号分隔格式
    if 'plugin' in data:
        plugin = data['plugin']
        plugin_opts = data.get('plugin-opts', {})
        
        if plugin == 'obfs':
            # 构建分号分隔的插件参数
            plugin_parts = ['obfs-local']
            if isinstance(plugin_opts, dict):
                mode = plugin_opts.get('mode', 'http')
                host = plugin_opts.get('host', '')
                plugin_parts.append(f'obfs={mode}')
                if host:
                    # 注意：这里不对host进行quote，因为分号分隔的参数需要整体引用
                    plugin_parts.append(f'obfs-host={host}')
            plugin_str = ';'.join(plugin_parts)
            query_params.append(f'plugin={quote(plugin_str, safe="")}')
        elif plugin == 'v2ray-plugin':
            # v2ray-plugin也使用分号分隔格式
            plugin_parts = ['v2ray-plugin']
            if isinstance(plugin_opts, dict):
                mode = plugin_opts.get('mode', 'websocket')
                tls = plugin_opts.get('tls', False)
                host = plugin_opts.get('host', '')
                path = plugin_opts.get('path', '/')
                plugin_parts.append(f'mode={mode}')
                if tls:
                    plugin_parts.append('tls=true')
                if host:
                    plugin_parts.append(f'host={host}')
                if path and path != '/':
                    plugin_parts.append(f'path={path}')
            plugin_str = ';'.join(plugin_parts)
            query_params.append(f'plugin={quote(plugin_str, safe="")}')
    
    # 添加通用参数
    _add_common_params(data, query_params, use_semicolon_separator=False)
    
    # 构建查询字符串
    query_str = '&'.join(query_params)
    # 备注名 - 保留原始名称，支持Unicode
    remark_name = quote(proxy.name, safe='')
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_ssr(proxy: ClashProxy) -> Optional[str]:
    """转换ShadowsocksR代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    protocol = data.get('protocol', 'origin')
    method = data.get('cipher', 'aes-256-cfb')
    obfs = data.get('obfs', 'plain')
    password = data.get('password', '')
    
    if not server or not port or not password:
        return None
    
    # Base64编码密码
    password_b64 = base64.urlsafe_b64encode(password.encode()).decode().rstrip('=')
    
    # 构建参数
    params = []
    if 'protocolparam' in data:
        params.append(f'protoparam={base64.urlsafe_b64encode(str(data["protocolparam"]).encode()).decode()}')
    if 'obfsparam' in data:
        params.append(f'obfsparam={base64.urlsafe_b64encode(str(data["obfsparam"]).encode()).decode()}')
    
    params_str = '&'.join(params)
    
    # 构建原始SSR字符串
    ssr_raw = f"{server}:{port}:{protocol}:{method}:{obfs}:{password_b64}"
    if params_str:
        ssr_raw = f"{ssr_raw}/?{params_str}"
    
    # Base64编码整个字符串
    encoded = base64.urlsafe_b64encode(ssr_raw.encode()).decode().rstrip('=')
    remark_name = quote(proxy.name)
    
    return f"ssr://{encoded}#{remark_name}"


def _convert_vmess(proxy: ClashProxy) -> Optional[str]:
    """转换VMess代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    uuid = data.get('uuid', '')
    
    if not server or not port or not uuid:
        return None
    
    # 构建VMess配置
    vmess_config = {
        "v": "2",
        "ps": proxy.name,
        "add": server,
        "port": port,
        "id": uuid,
        "aid": data.get('alterId', 0),
        "scy": data.get('cipher', 'auto'),
        "net": data.get('network', 'tcp'),
        "type": data.get('type', 'none'),
        "host": data.get('host', ''),
        "path": data.get('path', ''),
        "tls": data.get('tls', 'none'),
        "sni": data.get('sni', data.get('servername', '')),
        "alpn": data.get('alpn', ''),
        "fp": data.get('client-fingerprint', data.get('fingerprint', '')),
    }
    
    # packet-encoding参数
    if 'packet-encoding' in data:
        vmess_config["packetEncoding"] = data["packet-encoding"]
    
    # 清理空值
    vmess_config = {k: v for k, v in vmess_config.items() if v or k in ["v", "port", "aid"]}
    
    # WS额外参数
    if data.get('network') == 'ws' and 'ws-opts' in data:
        ws_opts = data['ws-opts']
        if isinstance(ws_opts, dict):
            headers = ws_opts.get('headers', {})
            if isinstance(headers, dict):
                for k, v in headers.items():
                    if k.lower() == 'host':
                        vmess_config["host"] = v
    
    import json
    vmess_json = json.dumps(vmess_config, separators=(',', ':'))
    encoded = base64.urlsafe_b64encode(vmess_json.encode()).decode().rstrip('=')
    
    return f"vmess://{encoded}"


def _convert_vless(proxy: ClashProxy) -> Optional[str]:
    """转换VLESS代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    uuid = data.get('uuid', '')
    
    if not server or not port or not uuid:
        return None
    
    query_params = []
    
    # 必需参数 - tls可以是布尔值或字符串
    tls_value = data.get('tls', 'tls')
    
    # 处理布尔值
    if tls_value is True:
        security = 'tls'
    elif tls_value is False:
        security = 'none'
    elif tls_value == 'reality':
        security = 'reality'
    else:
        security = str(tls_value)  # 处理字符串值
    
    if security == 'reality' and 'reality-opts' in data:
        query_params.append('security=reality')
        reality_opts = data['reality-opts']
        if isinstance(reality_opts, dict):
            if 'public-key' in reality_opts:
                query_params.append(f'pbk={reality_opts["public-key"]}')
            if 'short-id' in reality_opts:
                query_params.append(f'sid={reality_opts["short-id"]}')
    else:
        query_params.append(f'security={security}')
    
    # encryption参数
    if 'encryption' in data and data['encryption'] != 'none':
        query_params.append(f'encryption={data["encryption"]}')
    
    # flow参数
    if 'flow' in data:
        query_params.append(f'flow={data["flow"]}')
    
    # 传输层
    network = data.get('network', 'tcp')
    if network != 'tcp':
        query_params.append(f'type={network}')
        
        # WebSocket配置
        if network == 'ws' and 'ws-opts' in data:
            ws_opts = data['ws-opts']
            if isinstance(ws_opts, dict):
                if 'path' in ws_opts:
                    query_params.append(f'path={quote(ws_opts["path"])}')
                if 'headers' in ws_opts:
                    headers = ws_opts['headers']
                    if isinstance(headers, dict):
                        for k, v in headers.items():
                            if k.lower() == 'host':
                                query_params.append(f'host={quote(v)}')
                            else:
                                query_params.append(f'header={quote(f"{k}:{v}")}')
        
        # HTTP/2配置
        elif network == 'h2' and 'h2-opts' in data:
            h2_opts = data['h2-opts']
            if isinstance(h2_opts, dict):
                if 'host' in h2_opts:
                    hosts = h2_opts['host']
                    if isinstance(hosts, list) and len(hosts) > 0:
                        query_params.append(f'host={quote(hosts[0])}')
        
        # gRPC配置
        elif network == 'grpc' and 'grpc-opts' in data:
            grpc_opts = data['grpc-opts']
            if isinstance(grpc_opts, dict):
                if 'grpc-service-name' in grpc_opts:
                    query_params.append(f'serviceName={quote(grpc_opts["grpc-service-name"])}')
    
    # SNI/服务器名称
    sni = data.get('sni', data.get('servername', ''))
    if sni:
        query_params.append(f'sni={sni}')
    
    # ALPN
    if 'alpn' in data:
        alpn = data['alpn']
        if isinstance(alpn, list):
            query_params.append(f'alpn={",".join(alpn)}')
        elif isinstance(alpn, str):
            query_params.append(f'alpn={alpn}')
    
    # 指纹
    fp = data.get('client-fingerprint', data.get('fingerprint', ''))
    if fp:
        query_params.append(f'fp={fp}')
    
    # 跳过证书验证
    if data.get('skip-cert-verify', False):
        query_params.append('allowInsecure=1')
    
    # packet-encoding
    if 'packet-encoding' in data:
        query_params.append(f'packetEncoding={data["packet-encoding"]}')
    
    base_url = f"vless://{uuid}@{server}:{port}"
    query_str = '&'.join(query_params)
    remark_name = quote(proxy.name)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_trojan(proxy: ClashProxy) -> Optional[str]:
    """转换Trojan代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    password = data.get('password', '')
    
    if not server or not port or not password:
        return None
    
    query_params = []
    
    # 必需参数
    query_params.append('security=tls')
    
    # SNI
    if 'sni' in data:
        query_params.append(f'sni={data["sni"]}')
    elif 'servername' in data:
        query_params.append(f'sni={data["servername"]}')
    
    # ALPN
    if 'alpn' in data:
        alpn = data['alpn']
        if isinstance(alpn, list):
            query_params.append(f'alpn={",".join(alpn)}')
        elif isinstance(alpn, str):
            query_params.append(f'alpn={alpn}')
    
    # 指纹
    fp = data.get('client-fingerprint', data.get('fingerprint', ''))
    if fp:
        query_params.append(f'fp={fp}')
    
    # 跳过证书验证
    if data.get('skip-cert-verify', False):
        query_params.append('allowInsecure=1')
    
    # transport
    network = data.get('network', 'tcp')
    if network != 'tcp':
        query_params.append(f'type={network}')
        
        # WebSocket配置
        if network == 'ws' and 'ws-opts' in data:
            ws_opts = data['ws-opts']
            if isinstance(ws_opts, dict):
                if 'path' in ws_opts:
                    query_params.append(f'path={quote(ws_opts["path"])}')
                if 'headers' in ws_opts:
                    headers = ws_opts['headers']
                    if isinstance(headers, dict):
                        for k, v in headers.items():
                            if k.lower() == 'host':
                                query_params.append(f'host={quote(v)}')
        
        # gRPC配置
        elif network == 'grpc' and 'grpc-opts' in data:
            grpc_opts = data['grpc-opts']
            if isinstance(grpc_opts, dict):
                if 'grpc-service-name' in grpc_opts:
                    query_params.append(f'serviceName={quote(grpc_opts["grpc-service-name"])}')
    
    # reality
    if data.get('tls') == 'reality' and 'reality-opts' in data:
        reality_opts = data['reality-opts']
        if isinstance(reality_opts, dict):
            if 'public-key' in reality_opts:
                query_params.append(f'pbk={reality_opts["public-key"]}')
            if 'short-id' in reality_opts:
                query_params.append(f'sid={reality_opts["short-id"]}')
    
    base_url = f"trojan://{quote(password)}@{server}:{port}"
    query_str = '&'.join(query_params)
    remark_name = quote(proxy.name)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_hysteria(proxy: ClashProxy) -> Optional[str]:
    """转换Hysteria/Hysteria2代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    password = data.get('password', '')
    
    if not server or not port or not password:
        return None
    
    protocol = 'hysteria2' if proxy.type.lower() == 'hysteria2' else 'hysteria'
    
    query_params = []
    
    # SNI
    if 'sni' in data:
        query_params.append(f'sni={data["sni"]}')
    
    # 跳过证书验证
    if data.get('skip-cert-verify', False):
        query_params.append('insecure=1')
    
    # 指纹
    if 'fingerprint' in data:
        query_params.append(f'pinSHA256={data["fingerprint"]}')
    
    # ALPN
    if 'alpn' in data:
        alpn = data['alpn']
        if isinstance(alpn, list):
            query_params.append(f'alpn={",".join(alpn)}')
        elif isinstance(alpn, str):
            query_params.append(f'alpn={alpn}')
    
    # 混淆
    if 'obfs' in data:
        obfs = data['obfs']
        if isinstance(obfs, dict):
            obfs_type = obfs.get('type')
            obfs_password = obfs.get('password')
            if obfs_type:
                query_params.append(f'obfs={obfs_type}')
                if obfs_password:
                    query_params.append(f'obfs-password={obfs_password}')
        elif isinstance(obfs, str):
            query_params.append(f'obfs={obfs}')
            if 'obfs-password' in data:
                query_params.append(f'obfs-password={data["obfs-password"]}')
    
    # 端口跳跃
    if 'ports' in data and isinstance(data['ports'], str):
        query_params.append(f'mports={data["ports"]}')
    
    # 上行/下行速率
    if 'up' in data:
        query_params.append(f'upmbps={_parse_bandwidth(data["up"])}')
    if 'down' in data:
        query_params.append(f'downmbps={_parse_bandwidth(data["down"])}')
    
    base_url = f"{protocol}://{quote(password)}@{server}:{port}"
    query_str = '&'.join(query_params)
    remark_name = quote(proxy.name)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _parse_bandwidth(bw: Any) -> str:
    """解析带宽值，转换为Mbps"""
    if isinstance(bw, (int, float)):
        return str(bw)
    elif isinstance(bw, str):
        bw_lower = bw.lower()
        if 'mbps' in bw_lower:
            return bw_lower.replace('mbps', '').strip()
        elif 'kbps' in bw_lower:
            kbps = float(bw_lower.replace('kbps', '').strip())
            return str(kbps / 1000)
        elif 'gbps' in bw_lower:
            gbps = float(bw_lower.replace('gbps', '').strip())
            return str(gbps * 1000)
        else:
            try:
                return str(float(bw))
            except:
                return bw
    return '0'


def _convert_http(proxy: ClashProxy) -> Optional[str]:
    """转换HTTP/HTTPS代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    
    if not server or not port:
        return None
    
    # 认证信息
    username = data.get('username', '')
    password = data.get('password', '')
    
    # TLS设置
    tls = data.get('tls', False)
    protocol = 'https' if tls else 'http'
    
    # 认证信息
    auth_part = ''
    if username and password:
        auth_part = f"{quote(username)}:{quote(password)}@"
    
    base_url = f"{protocol}://{auth_part}{server}:{port}"
    remark_name = quote(proxy.name)
    
    # 查询参数
    query_params = []
    if 'sni' in data:
        query_params.append(f'sni={data["sni"]}')
    if data.get('skip-cert-verify', False):
        query_params.append('allowInsecure=1')
    
    query_str = '&'.join(query_params)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_socks(proxy: ClashProxy) -> Optional[str]:
    """转换SOCKS5代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    
    if not server or not port:
        return None
    
    # 认证信息
    username = data.get('username', '')
    password = data.get('password', '')
    
    # TLS设置
    tls = data.get('tls', False)
    protocol = 'socks5s' if tls else 'socks5'
    
    # 认证信息
    auth_part = ''
    if username and password:
        auth_part = f"{quote(username)}:{quote(password)}@"
    
    base_url = f"{protocol}://{auth_part}{server}:{port}"
    remark_name = quote(proxy.name)
    
    # 查询参数
    query_params = []
    if 'sni' in data:
        query_params.append(f'sni={data["sni"]}')
    if data.get('skip-cert-verify', False):
        query_params.append('allowInsecure=1')
    
    query_str = '&'.join(query_params)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_snell(proxy: ClashProxy) -> Optional[str]:
    """转换Snell代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    psk = data.get('psk', '')
    
    if not server or not port or not psk:
        return None
    
    query_params = []
    query_params.append(f'psk={quote(psk)}')
    
    # 版本
    if 'version' in data:
        query_params.append(f'version={data["version"]}')
    
    # 混淆
    if 'obfs-opts' in data:
        obfs_opts = data['obfs-opts']
        if isinstance(obfs_opts, dict):
            if 'mode' in obfs_opts:
                query_params.append(f'obfs={obfs_opts["mode"]}')
            if 'host' in obfs_opts:
                query_params.append(f'obfs-host={quote(obfs_opts["host"])}')
    
    base_url = f"snell://{server}:{port}"
    query_str = '&'.join(query_params)
    remark_name = quote(proxy.name)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_tuic(proxy: ClashProxy) -> Optional[str]:
    """转换TUIC代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    token = data.get('token', '')
    uuid = data.get('uuid', '')
    password = data.get('password', '')
    
    if not server or not port:
        return None
    
    # TUIC v4需要token，v5需要uuid+password
    if not token and (not uuid or not password):
        return None
    
    # 认证信息
    auth_part = ''
    if uuid and password:
        auth_part = f"{uuid}:{quote(password)}@"
    else:
        auth_part = f"{quote(token)}@"
    
    query_params = []
    
    # ALPN
    if 'alpn' in data:
        alpn = data['alpn']
        if isinstance(alpn, list):
            query_params.append(f'alpn={",".join(alpn)}')
        elif isinstance(alpn, str):
            query_params.append(f'alpn={alpn}')
    
    # SNI
    if 'sni' in data:
        query_params.append(f'sni={data["sni"]}')
    
    # 跳过证书验证
    if data.get('skip-cert-verify', False):
        query_params.append('allowInsecure=1')
    
    # UDP中继模式
    if 'udp-relay-mode' in data:
        query_params.append(f'udp-relay-mode={data["udp-relay-mode"]}')
    
    # 拥塞控制
    if 'congestion-controller' in data:
        query_params.append(f'congestion-controller={data["congestion-controller"]}')
    
    base_url = f"tuic://{auth_part}{server}:{port}"
    query_str = '&'.join(query_params)
    remark_name = quote(proxy.name)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_wireguard(proxy: ClashProxy) -> Optional[str]:
    """转换WireGuard代理"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    private_key = data.get('private-key', '')
    
    if not server or not port or not private_key:
        return None
    
    query_params = []
    
    # 公钥
    if 'public-key' in data:
        query_params.append(f'public-key={data["public-key"]}')
    
    # 预共享密钥
    if 'preshared-key' in data:
        query_params.append(f'preshared-key={data["preshared-key"]}')
    
    # IP地址
    if 'ip' in data:
        query_params.append(f'ip={data["ip"]}')
    
    # MTU
    if 'mtu' in data:
        query_params.append(f'mtu={data["mtu"]}')
    
    # 保留的端点端口
    if 'reserved' in data:
        reserved = data['reserved']
        if isinstance(reserved, list):
            query_params.append(f'reserved={",".join(str(r) for r in reserved)}')
    
    base_url = f"wireguard://{quote(private_key)}@{server}:{port}"
    query_str = '&'.join(query_params)
    remark_name = quote(proxy.name)
    
    if query_str:
        return f"{base_url}?{query_str}#{remark_name}"
    else:
        return f"{base_url}#{remark_name}"


def _convert_generic(proxy: ClashProxy) -> Optional[str]:
    """通用协议转换"""
    data = proxy.data
    server = proxy.server
    port = proxy.port
    proxy_type = proxy.type.lower()
    
    if not server or not port:
        return None
    
    # 简单协议格式
    if proxy_type in ['http', 'https', 'socks', 'socks5']:
        return f"{proxy_type}://{server}:{port}#{quote(proxy.name)}"
    else:
        # 尝试构建基本链接
        return f"clash://{proxy_type}@{server}:{port}#{quote(proxy.name)}"