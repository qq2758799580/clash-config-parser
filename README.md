# Clash配置解析器 (clash-config-parser)

[![GitHub](https://img.shields.io/badge/GitHub-qq2758799580%2Fclash--config--parser-blue)](https://github.com/qq2758799580/clash-config-parser)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

一个功能完整的Clash配置解析工具，支持多格式输入、全协议转换、Web界面操作和批量处理。可将Clash配置、原始节点链接、base64订阅转换为标准节点链接格式，便于分享和使用。

## ✨ 核心功能

### 🔍 **多格式智能解析**
- **Clash YAML配置**：标准Clash配置文件解析
- **原始节点链接**：直接识别 `ss://`、`vmess://`、`vless://`、`trojan://`、`ssr://` 等协议链接
- **Base64订阅**：自动检测和解码base64编码的订阅列表  
- **混合格式支持**：换行分隔、空格分隔、任意空白符分隔
- **自动识别**：智能判断输入格式，无需手动选择

### 🌐 **全协议支持**
| 协议 | 支持状态 | 特性说明 |
|------|----------|----------|
| **Shadowsocks (SS)** | ✅ 完整 | 所有主流加密方法，支持obfs/v2ray-plugin插件，完整Unicode和Emoji支持 |
| **ShadowsocksR (SSR)** | ✅ 完整 | 协议/混淆参数，协议参数base64编码 |
| **VMess** | ✅ 完整 | V2Ray核心协议，支持TLS、WebSocket、gRPC、HTTP/2传输 |
| **VLESS** | ✅ 完整 | Xray轻量协议，支持Reality、XTLS、Vision流控 |
| **Trojan** | ✅ 完整 | TLS伪装协议，支持SNI、ALPN设置 |
| **Hysteria/Hysteria2** | ✅ 完整 | UDP加速协议，支持混淆、带宽配置 |
| **HTTP/HTTPS** | ✅ 基础 | HTTP代理协议 |
| **SOCKS5** | ✅ 基础 | SOCKS5代理协议 |
| **Snell** | ✅ | Snell代理协议 |
| **TUIC** | ✅ | TUIC v5协议 |
| **WireGuard** | ✅ | WireGuard VPN协议 |

### 🔄 **智能转换系统**
- **协议精确映射**：基于MetaCubeX/mihomo官方文档的精确参数转换
- **原始链接保持**：识别原始链接时保持完整格式和所有参数
- **通用参数处理**：UDP、TCP Fast Open、HTTP复用、客户端指纹等统一处理
- **特殊格式兼容**：支持 `plugin=obfs-local;obfs=tls;obfs-host=...` 分号分隔格式
- **Unicode完整支持**：国家旗帜🇨🇳、Emoji、中文字符完美支持

### 🖥️ **现代化Web界面**
- **URL批量管理**：添加、删除、保存、加载默认URL列表(可在app/routers的clash.py中增加default_urls的值)
- **折叠式结果展示**：按URL分组，可收起/展开的节点列表
- **实时统计数据**：URL数量、成功解析数、节点总数、协议分布
- **一键批量操作**：复制所有链接、导出为文本文件
- **代理详情查看**：点击查看完整节点信息和原始链接
- **响应式设计**：适配桌面和移动设备

### ⚡ **高级特性**
- **批量并发处理**：同时解析多个URL配置，提高效率
- **本地存储**：URL列表自动保存到浏览器本地存储
- **Docker容器化**：开箱即用的Docker镜像和Docker Compose配置
- **配置驱动**：环境变量驱动的灵活配置系统
- **可扩展架构**：模块化设计，易于添加新协议支持

## 🚀 快速开始

### 环境要求
- Python 3.12+ 或 Docker
- Redis（可选，用于高级缓存功能）

### 本地运行
```bash
# 克隆项目
git clone https://github.com/qq2758799580/clash-config-parser.git
cd clash-config-parser

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env.example .env.dev
# 编辑 .env.dev 根据需要调整配置

# 运行应用
ENVIRONMENT=dev python run.py

# 访问 http://localhost:8080
```

### Docker部署
```bash
# 使用Docker Compose（推荐）
docker-compose up -d

# 或直接使用Docker
docker run -d \
  -p 8080:8080 \
  -e ENVIRONMENT=prod \
  -e PORT=8080 \
  --name clash-parser \
  qq2758799580/clash-config-parser:latest
```

## 📖 使用指南

### 基本使用流程
1. **添加URL**：输入Clash配置URL、原始节点链接列表或base64订阅
2. **解析配置**：点击"解析配置"按钮，等待解析完成
3. **查看结果**：展开URL分组查看节点详情和转换后的链接
4. **批量操作**：使用"复制全部"或"导出"按钮处理所有节点链接

### 支持的输入格式示例
```yaml
# 1. Clash YAML配置
proxies:
  - name: "My Proxy"
    type: ss
    server: example.com
    port: 443
    cipher: aes-256-gcm
    password: mypassword

# 2. 原始节点链接列表（每行一个）
ss://Base64EncodedString@example.com:443?plugin=obfs-local#ExampleNode
ssr://Base64EncodedSSRString#ExampleSSR

# 3. Base64编码订阅
Base64EncodedSubscriptionString

# 4. 空格分隔链接
ss://link1 ss://link2 vmess://link3
```

### Web界面操作
1. **URL管理区域**：
   - 输入URL或直接粘贴节点链接
   - 点击"加载默认URL"快速添加示例配置
   - 使用开关控制是否转换为节点链接

2. **解析结果区域**：
   - 每个URL显示为可折叠卡片
   - 点击标题栏展开/收起节点列表
   - 查看协议类型统计和节点数量
   - 点击节点查看完整代理详情

3. **快捷操作栏**：
   - "复制全部"：一键复制所有节点链接到剪贴板
   - "导出"：下载所有链接为文本文件（`clash-proxies-{timestamp}.txt`）

### API接口
```bash
# 获取默认URL列表
GET /api/clash/default-urls

# 解析配置
POST /api/clash/parse
Content-Type: application/json

{
  "urls": [
    "https://example.com/clash/config.yaml",
    "https://example.com/subscription/base64"
  ],
  "convert_to_links": true
}

# 响应示例
{
  "status": "success",
  "summary": {
    "total_urls": 2,
    "successful_urls": 2,
    "total_proxies": 25
  },
  "results": [
    {
      "url": "https://example.com/clash/config.yaml",
      "filename": "config.yaml",
      "proxies": [...],
      "proxy_types": {"ss": 10, "vmess": 8, "vless": 5, "trojan": 2},
      "links": ["ss://...", "vmess://...", "vless://...", "trojan://..."]
    }
  ]
}
```

## 🏗️ 项目架构

```
clash-config-parser/
├── app/                    # Web应用层
│   ├── main.py            # FastAPI应用入口
│   └── routers/           # API路由
│       └── clash.py       # Clash配置解析API
├── business/              # 业务逻辑层
│   └── clash_processor.py # 核心解析和转换逻辑（1200+行完整实现）
├── framework/             # 框架层
│   ├── config.py          # 配置管理系统
│   └── logging.py         # 日志配置
├── frontend/              # 前端界面
│   └── static/
│       ├── index.html     # 主界面（折叠式设计）
│       ├── script.js      # 前端业务逻辑
│       └── favicon.ico    # 网站图标
├── tests/                 # 测试文件
│   ├── test_clash_parser.py
│   └── test_vless_config.py
├── requirements.txt       # Python依赖
├── run.py                # 启动脚本
├── Dockerfile            # Docker容器配置
├── docker-compose.yml    # Docker Compose配置
├── .env.example          # 环境配置示例
└── README.md            # 项目文档
```

### 技术栈
- **后端**：FastAPI + Uvicorn + Pydantic
- **前端**：Bootstrap 5 + 原生JavaScript
- **解析库**：PyYAML + httpx + base64
- **部署**：Docker + Docker Compose
- **协议支持**：基于MetaCubeX/mihomo官方文档的完整实现

## 🔧 配置说明

### 环境变量
```env
# 运行环境
ENVIRONMENT=dev                 # dev/test/prod
PORT=8080                       # 服务器端口

# 日志配置
LOG_LEVEL=info                  # debug/info/warning/error

# 性能优化
UVICORN_WORKERS=1               # Uvicorn工作进程数

# Redis缓存（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_TIMEOUT=30
```

### Docker Compose配置
```yaml
version: '3.8'
services:
  clash-parser:
    build: .
    ports:
      - "8080:8080"
    environment:
      - ENVIRONMENT=prod
      - PORT=8080
      - LOG_LEVEL=info
    restart: unless-stopped
```

## 📋 协议转换规则

### SS协议转换示例
```yaml
# Clash配置
- name: "🇺🇸US_01"
  type: ss
  server: 203.0.113.1
  port: 443
  cipher: chacha20-ietf-poly1305
  password: "example-password-123"
  plugin: obfs
  plugin-opts:
    mode: tls
    host: "example.com"

# 转换结果
ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpleGFtcGxlLXBhc3N3b3JkLTEyM0BVMTo0NDM=?plugin=obfs-local%3Bobfs%3Dtls%3Bobfs-host%3Dexample.com#%F0%9F%87%BA%F0%9F%87%B8US_01
```

### VLESS协议转换示例
```yaml
# Clash配置
- name: "fr-000"
  type: vless
  server: 1.2.3.4
  port: 443
  uuid: "a0b1c2d3-e4f5-6789-abcd-ef0123456789"
  tls: true
  servername: "apple.com"
  client-fingerprint: "chrome"
  network: "grpc"
  grpc-opts:
    grpc-service-name: "UpdateService"

# 转换结果
vless://a0b1c2d3-e4f5-6789-abcd-ef0123456789@1.2.3.4:443?security=tls&type=grpc&serviceName=UpdateService&sni=apple.com&fp=chrome#fr-000
```

## 🛠️ 开发指南

### 添加新协议支持
1. 在 `business/clash_processor.py` 中添加新的 `_convert_xxx` 函数
2. 在 `convert_proxy_to_link` 函数中添加协议类型判断
3. 在 `extract_proxies_from_config` 函数中确保能识别新协议类型
4. 添加相应的测试用例

### 扩展功能建议
- 添加节点连通性测试功能
- 支持二维码生成和扫描
- 添加订阅链接定时更新
- 支持更多配置格式（如Surge、Quantumult X）
- 添加用户认证和权限管理

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📄 许可证

本项目基于 MIT 许可证发布。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 感谢 [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) 提供的协议文档参考
- 感谢所有贡献者和用户的支持

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [https://github.com/qq2758799580/clash-config-parser/issues](https://github.com/qq2758799580/clash-config-parser/issues)
- 项目地址: [https://github.com/qq2758799580/clash-config-parser](https://github.com/qq2758799580/clash-config-parser)

---

**开始使用**：访问 [http://localhost:8080](http://localhost:8080) 或查看 [在线演示](https://github.com/qq2758799580/clash-config-parser#-快速开始) 开始解析您的Clash配置！