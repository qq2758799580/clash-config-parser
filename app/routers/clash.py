import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from business.clash_processor import (
    fetch_and_parse_clash_config,
    convert_proxies_to_links,
    ClashConfigAnalysis
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ParseRequest(BaseModel):
    """解析Clash配置请求"""
    urls: List[HttpUrl]
    convert_to_links: bool = True


@router.post("/parse")
async def parse_clash_config(request: ParseRequest):
    """
    解析Clash配置文件
    
    从提供的URL列表下载Clash配置文件，提取proxies节点信息，
    并可选转换为节点链接格式。
    """
    try:
        url_list = [str(url) for url in request.urls]
        
        logger.info("开始解析Clash配置 URL数量=%d", len(url_list))
        
        # 获取并解析配置
        results = []
        for url in url_list:
            try:
                analysis = fetch_and_parse_clash_config(url)
                results.append(analysis)
            except Exception as e:
                logger.warning("解析URL失败: %s, 错误: %s", url, str(e))
                results.append({
                    "url": url,
                    "error": str(e),
                    "proxies": [],
                    "proxy_types": {}
                })
        
        # 如果需要转换链接
        if request.convert_to_links:
            for result in results:
                if isinstance(result, ClashConfigAnalysis) and result.proxies:
                    result.links = convert_proxies_to_links(result.proxies)
        
        # 汇总统计
        total_proxies = sum(
            len(r.proxies) if isinstance(r, ClashConfigAnalysis) else 0 
            for r in results
        )
        successful_urls = len([r for r in results if isinstance(r, ClashConfigAnalysis) and not getattr(r, 'error', None)])
        
        return {
            "status": "success",
            "summary": {
                "total_urls": len(url_list),
                "successful_urls": successful_urls,
                "total_proxies": total_proxies,
            },
            "results": [r.model_dump() if hasattr(r, 'model_dump') else r for r in results]
        }
        
    except Exception as e:
        logger.exception("解析Clash配置失败")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.get("/default-urls")
async def get_default_urls():
    """获取默认Clash配置URL列表"""
    default_urls = [
        
    ]
    
    return {
        "urls": default_urls,
        "count": len(default_urls)
    }