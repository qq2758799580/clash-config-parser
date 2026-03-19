FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先拷依赖文件以利用缓存
COPY requirements.txt /app/requirements.txt

# 使用清华镜像源加速下载
RUN pip install --upgrade pip --no-cache-dir --index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip install -r /app/requirements.txt --no-cache-dir --index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 再拷贝代码
COPY . /app

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser


EXPOSE 8080

CMD ["python", "run.py"]