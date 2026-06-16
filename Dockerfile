# Itemly Dockerfile
# 轻量化物品管理系统

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端与前端代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# 安装Python依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

# 数据目录（持久化：数据库 + 上传图片）
RUN mkdir -p /data/uploads

# 暴露端口
EXPOSE 9009

# 环境变量（FLASK_SECRET 为敏感信息，请通过 docker run -e 或 docker-compose 运行时注入）
ENV FLASK_DEBUG=false
ENV PORT=9009
ENV ITEMLY_DB_PATH=/data/itemly.db
ENV ITEMLY_UPLOAD_DIR=/data/uploads

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:9009", "--workers", "2", "backend.app:app"]
