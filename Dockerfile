# Itemly Dockerfile
# 轻量化物品管理系统

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码
COPY backend/ ./backend/

# 安装Python依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

# 创建上传目录
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 5000

# 环境变量
ENV FLASK_SECRET=itemly-production-secret-key-change-me
ENV FLASK_DEBUG=false
ENV PORT=5000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "backend.app:app"]
