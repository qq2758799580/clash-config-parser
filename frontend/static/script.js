// Clash配置解析器前端脚本

class ClashParserUI {
    constructor() {
        this.urls = [];
        this.results = null;
        this.apiBase = '/api/clash';
        
        this.initEventListeners();
        this.loadFromLocalStorage();
        this.updateUrlList();
    }

    initEventListeners() {
        document.getElementById('addUrlBtn').addEventListener('click', () => this.addUrl());
        document.getElementById('urlInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addUrl();
        });

        document.getElementById('loadDefaultBtn').addEventListener('click', () => this.loadDefaultUrls());

        document.getElementById('clearAllBtn').addEventListener('click', () => {
            if (confirm('确定要清空所有URL吗？')) {
                this.urls = [];
                this.updateUrlList();
                this.saveToLocalStorage();
            }
        });

        document.getElementById('parseBtn').addEventListener('click', () => this.parseConfigs());
        document.getElementById('copyAllLinksBtn').addEventListener('click', () => this.copyAllLinks());
        document.getElementById('exportAllLinksBtn').addEventListener('click', () => this.exportAllLinks());
    }

    getAllLinks() {
        if (!this.results || !this.results.results) {
            return [];
        }
        return this.results.results.flatMap(r => r.links || []);
    }

    copyAllLinks() {
        const allLinks = this.getAllLinks();
        
        if (allLinks.length === 0) {
            this.showAlert('没有可复制的链接，请先解析配置', 'warning');
            return;
        }

        const textToCopy = allLinks.join('\n');
        this.copyToClipboard(textToCopy);
        this.showAlert(`已复制 ${allLinks.length} 个节点链接到剪贴板`, 'success');
    }

    exportAllLinks() {
        const allLinks = this.getAllLinks();
        
        if (allLinks.length === 0) {
            this.showAlert('没有可导出的链接，请先解析配置', 'warning');
            return;
        }

        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
        const filename = `clash-proxies-${timestamp}.txt`;
        const content = allLinks.join('\n');
        
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        this.showAlert(`已导出 ${allLinks.length} 个节点链接到文件 ${filename}`, 'success');
    }

    addUrl() {
        const urlInput = document.getElementById('urlInput');
        const url = urlInput.value.trim();
        
        if (!url) {
            this.showAlert('请输入有效的URL', 'warning');
            return;
        }

        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            this.showAlert('URL必须以http://或https://开头', 'warning');
            return;
        }

        if (this.urls.includes(url)) {
            this.showAlert('该URL已存在', 'warning');
            return;
        }

        this.urls.push(url);
        urlInput.value = '';
        this.updateUrlList();
        this.saveToLocalStorage();
    }

    loadDefaultUrls() {
        this.showLoading('正在加载默认URL...');
        
        fetch(`${this.apiBase}/default-urls`)
            .then(response => response.json())
            .then(data => {
                this.urls = data.urls;
                this.updateUrlList();
                this.saveToLocalStorage();
                this.showAlert(`已加载 ${data.count} 个默认URL`, 'success');
                this.hideLoading();
            })
            .catch(error => {
                console.error('加载默认URL失败:', error);
                this.showAlert('加载默认URL失败', 'danger');
                this.hideLoading();
            });
    }

    updateUrlList() {
        const urlList = document.getElementById('urlList');
        const template = document.getElementById('urlItemTemplate');
        
        if (this.urls.length === 0) {
            urlList.innerHTML = '<div class="text-center text-muted p-3">暂无URL，请添加或加载默认URL</div>';
            return;
        }

        urlList.innerHTML = '';
        
        this.urls.forEach((url, index) => {
            const clone = template.content.cloneNode(true);
            const urlItem = clone.querySelector('.url-item');
            const urlText = clone.querySelector('.url-text');
            const deleteBtn = clone.querySelector('.delete-url-btn');
            
            urlText.textContent = url;
            urlText.title = url;
            
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteUrl(index);
            });
            
            urlItem.addEventListener('click', () => {
                prompt('完整URL', url);
            });
            
            urlList.appendChild(clone);
        });
    }

    deleteUrl(index) {
        if (confirm('确定要删除这个URL吗？')) {
            this.urls.splice(index, 1);
            this.updateUrlList();
            this.saveToLocalStorage();
        }
    }

    parseConfigs() {
        if (this.urls.length === 0) {
            this.showAlert('请先添加URL', 'warning');
            return;
        }

        const convertLinks = document.getElementById('convertLinksSwitch').checked;
        this.showLoading('正在解析配置，请稍候...');
        
        const requestData = {
            urls: this.urls,
            convert_to_links: convertLinks
        };

        fetch(`${this.apiBase}/parse`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            this.results = data;
            this.displayResults();
            this.hideLoading();
            
            if (data.status === 'success') {
                const summary = data.summary;
                this.showAlert(`解析完成！成功解析 ${summary.successful_urls}/${summary.total_urls} 个URL，共 ${summary.total_proxies} 个节点`, 'success');
            } else {
                this.showAlert('解析失败：' + (data.message || '未知错误'), 'danger');
            }
        })
        .catch(error => {
            console.error('解析失败:', error);
            this.showAlert('解析失败：' + error.message, 'danger');
            this.hideLoading();
        });
    }

    displayResults() {
        if (!this.results || !this.results.results) {
            return;
        }

        const resultsContent = document.getElementById('resultsContent');
        const linksContent = document.getElementById('linksContent');
        const statsContent = document.getElementById('statsContent');
        
        resultsContent.innerHTML = '';
        linksContent.innerHTML = '';
        
        const resultTemplate = document.getElementById('resultItemTemplate');
        const proxyTemplate = document.getElementById('proxyItemTemplate');
        
        const quickActions = document.getElementById('quickActions');
        const linksCount = document.getElementById('linksCount');
        const allLinks = this.results.results.flatMap(r => r.links || []);
        quickActions.style.display = 'block';
        linksCount.textContent = `${allLinks.length} 个节点`;
        
        if (this.results.status === 'success') {
            const summary = this.results.summary;
            statsContent.innerHTML = `
                <div class="row text-center">
                    <div class="col-md-4">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h5 class="card-title">${summary.total_urls}</h5>
                                <p class="card-text">总URL数</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h5 class="card-title">${summary.successful_urls}</h5>
                                <p class="card-text">成功解析</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h5 class="card-title">${summary.total_proxies}</h5>
                                <p class="card-text">总节点数</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        this.results.results.forEach((result, index) => {
            const clone = resultTemplate.content.cloneNode(true);
            const resultItem = clone.querySelector('.result-item');
            const header = clone.querySelector('.result-header');
            const collapseIcon = clone.querySelector('.collapse-icon');
            const title = clone.querySelector('.result-title');
            const badge = clone.querySelector('.result-badge');
            const countBadge = clone.querySelector('.result-count');
            const typeStats = clone.querySelector('.type-stats');
            const errorText = clone.querySelector('.error-text');
            const proxiesList = clone.querySelector('.proxies-list');
            
            const urlObj = new URL(result.url);
            title.textContent = `${index + 1}. ${urlObj.hostname}`;
            title.title = result.url;
            
            if (result.error) {
                badge.className = 'badge bg-danger';
                badge.textContent = '失败';
                errorText.textContent = `错误: ${result.error}`;
                errorText.style.display = 'block';
                collapseIcon.className = 'bi bi-exclamation-triangle text-danger me-2';
            } else {
                badge.className = 'badge bg-success';
                badge.textContent = `${result.proxies?.length || 0} 节点`;
                countBadge.textContent = result.proxies?.length || 0;
                countBadge.style.display = 'inline-block';
            }
            
            if (result.proxy_types && Object.keys(result.proxy_types).length > 0) {
                typeStats.innerHTML = Object.entries(result.proxy_types)
                    .map(([type, count]) => {
                        const color = this.getTypeColor(type);
                        return `<span class="type-count" style="background-color: ${color}">${type}: ${count}</span>`;
                    })
                    .join('');
            }
            
            // 添加折叠功能
            header.addEventListener('click', () => {
                const isCollapsed = proxiesList.style.display === 'none';
                if (isCollapsed) {
                    proxiesList.style.display = 'block';
                    errorText.style.display = 'none';
                    collapseIcon.className = 'bi bi-chevron-down me-2';
                } else {
                    proxiesList.style.display = 'none';
                    if (result.error) {
                        errorText.style.display = 'block';
                    }
                    collapseIcon.className = 'bi bi-chevron-right me-2';
                }
            });
            
            if (result.proxies && result.proxies.length > 0) {
                result.proxies.forEach((proxy, proxyIndex) => {
                    const proxyClone = proxyTemplate.content.cloneNode(true);
                    const proxyCard = proxyClone.querySelector('.proxy-card');
                    const typeBadge = proxyClone.querySelector('.proxy-type-badge');
                    const nameSpan = proxyClone.querySelector('.proxy-name');
                    const addressSpan = proxyClone.querySelector('.proxy-address');
                    const linkText = proxyClone.querySelector('.link-text');
                    const copyBtn = proxyClone.querySelector('.copy-proxy-btn');
                    
                    typeBadge.className = `badge ${this.getTypeBadgeClass(proxy.type)}`;
                    typeBadge.textContent = proxy.type.toUpperCase();
                    nameSpan.textContent = proxy.name;
                    addressSpan.textContent = ` (${proxy.server}:${proxy.port})`;
                    
                    if (result.links && result.links[proxyIndex]) {
                        linkText.textContent = result.links[proxyIndex];
                        linkText.style.display = 'block';
                    }
                    
                    copyBtn.addEventListener('click', () => {
                        let textToCopy = proxy.name;
                        if (result.links && result.links[proxyIndex]) {
                            textToCopy = result.links[proxyIndex];
                        }
                        
                        this.copyToClipboard(textToCopy);
                        this.showAlert('已复制到剪贴板', 'success');
                    });
                    
                    proxyCard.addEventListener('click', (e) => {
                        if (e.target.closest('.copy-btn')) return;
                        this.showProxyDetails(proxy, result.links ? result.links[proxyIndex] : null);
                    });
                    
                    proxiesList.appendChild(proxyClone);
                });
            }
            
            resultsContent.appendChild(clone);
        });
        
        if (this.results.results.some(r => r.links && r.links.length > 0)) {
            const allLinks = this.results.results.flatMap(r => r.links || []);
            linksContent.innerHTML = '';
            
            allLinks.forEach((link, index) => {
                const div = document.createElement('div');
                div.className = 'link-item mb-2';
                div.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="link-text" style="flex: 1;">${link}</div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary copy-link-btn" data-link="${index}">
                                <i class="bi bi-copy"></i>
                            </button>
                        </div>
                    </div>
                `;
                
                div.querySelector('.copy-link-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.copyToClipboard(link);
                    this.showAlert('链接已复制到剪贴板', 'success');
                });
                
                div.addEventListener('click', () => {
                    prompt('节点链接', link);
                });
                
                linksContent.appendChild(div);
            });
        } else {
            linksContent.innerHTML = '<div class="text-center text-muted p-3">未生成节点链接（请勾选"转换为节点链接"）</div>';
        }
    }

    showProxyDetails(proxy, link) {
        let details = `
            <strong>名称:</strong> ${proxy.name}<br>
            <strong>类型:</strong> ${proxy.type}<br>
        `;
        
        // 如果是从原始链接创建的代理，从data中获取更多信息
        const data = proxy.data || {};
        const rawLink = data.raw_link || link || '';
        
        // 尝试从服务器和端口字段获取信息
        const server = proxy.server || data.server || '';
        const port = proxy.port || data.port || 0;
        
        if (server && port) {
            details += `<strong>服务器:</strong> ${server}<br>`;
            details += `<strong>端口:</strong> ${port}<br>`;
        }
        
        // 重要字段 - 检查proxy对象和data对象
        const importantFields = ['password', 'uuid', 'cipher', 'protocol', 'obfs', 'sni', 'network'];
        importantFields.forEach(field => {
            let value = proxy[field] !== undefined ? proxy[field] : (data[field] !== undefined ? data[field] : undefined);
            if (value !== undefined) {
                details += `<strong>${field}:</strong> ${value}<br>`;
            }
        });
        
        // 显示原始链接
        if (rawLink) {
            details += `<br><strong>原始链接:</strong><br><code style="word-break: break-all;">${rawLink}</code><br>`;
            
            // 尝试从SS链接中解析更多信息
            if (rawLink.startsWith('ss://')) {
                try {
                    // 解析SS链接: ss://base64(method:password)@server:port#remark
                    const parts = rawLink.replace('ss://', '').split('@');
                    if (parts.length === 2) {
                        const [b64Auth, addressPart] = parts;
                        const [serverPortPart, remarkPart] = addressPart.split('#');
                        const [server, port] = serverPortPart.split(':');
                        
                        // 尝试解码认证信息
                        try {
                            const decodedAuth = atob(b64Auth.replace(/[^A-Za-z0-9+/=]/g, ''));
                            const [method, password] = decodedAuth.split(':');
                            details += `<strong>加密方法:</strong> ${method}<br>`;
                            details += `<strong>密码:</strong> ${password}<br>`;
                        } catch (e) {
                            // base64解码失败
                        }
                        
                        details += `<strong>解析的服务:</strong> ${server}<br>`;
                        details += `<strong>解析的端口:</strong> ${port}<br>`;
                    }
                } catch (e) {
                    console.log('SS链接解析失败:', e);
                }
            }
        } else if (link) {
            details += `<br><strong>链接:</strong><br><code style="word-break: break-all;">${link}</code>`;
        }
        
        // 显示完整数据（调试用）
        if (Object.keys(data).length > 0) {
            details += `<br><strong>原始数据:</strong><br><code style="word-break: break-all; font-size: 0.8em;">${JSON.stringify(data, null, 2)}</code>`;
        }
        
        alert(`代理详情:\n\n${details.replace(/<br>/g, '\n').replace(/<[^>]+>/g, '')}`);
    }

    getTypeColor(type) {
        const colors = {
            'ss': '#6c757d',
            'ssr': '#fd7e14',
            'vmess': '#20c997',
            'vless': '#0dcaf0',
            'trojan': '#6610f2',
            'hysteria2': '#d63384',
            'http': '#198754',
            'socks5': '#6f42c1',
            'unknown': '#6c757d'
        };
        return colors[type] || '#6c757d';
    }

    getTypeBadgeClass(type) {
        const classes = {
            'ss': 'bg-secondary',
            'ssr': 'bg-warning text-dark',
            'vmess': 'bg-success',
            'vless': 'bg-info text-dark',
            'trojan': 'bg-primary',
            'hysteria2': 'bg-danger',
            'http': 'bg-success',
            'socks5': 'bg-purple',
            'unknown': 'bg-secondary'
        };
        return classes[type] || 'bg-secondary';
    }

    copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
        } catch (err) {
            console.error('复制失败:', err);
        }
        
        document.body.removeChild(textarea);
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }

    showLoading(text) {
        const overlay = document.getElementById('loadingOverlay');
        const loadingText = document.getElementById('loadingText');
        
        loadingText.textContent = text || '正在处理...';
        overlay.style.display = 'flex';
    }

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        overlay.style.display = 'none';
    }

    saveToLocalStorage() {
        try {
            localStorage.setItem('clash_parser_urls', JSON.stringify(this.urls));
        } catch (e) {
            console.warn('无法保存到本地存储:', e);
        }
    }

    loadFromLocalStorage() {
        try {
            const saved = localStorage.getItem('clash_parser_urls');
            if (saved) {
                this.urls = JSON.parse(saved);
                this.updateUrlList();
            }
        } catch (e) {
            console.warn('无法从本地存储加载:', e);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.clashParserUI = new ClashParserUI();
});