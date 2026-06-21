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

# 默认环境变量（均可在 docker run -e 或 docker-compose 中覆盖）
ENV FLASK_DEBUG=false
ENV PORT=9009
ENV ITEMLY_DB_PATH=/data/itemly.db
ENV ITEMLY_UPLOAD_DIR=/data/uploads
# 生产环境默认 Session Cookie 行为：SameSite=Lax，Secure 关（仅当显式启用时开启），
# 以便兼容 HTTP 反代或内网部署；HTTPS 部署时请在运行时设置
# SESSION_COOKIE_SECURE=true。
ENV SESSION_COOKIE_SECURE=false
ENV SESSION_COOKIE_SAMESITE=Lax
# 反向代理信任深度（Nginx 等一层反代默认即可）
ENV PROXY_FIX_X_FOR=1
ENV PROXY_FIX_X_PROTO=1
ENV PROXY_FIX_X_HOST=1

# 启动命令：
#  - --forwarded-allow-ips="*" 让 gunicorn 信任 ProxyFix 需要的 X-Forwarded-* 头；
#  - 生产环境请将 FLASK_SECRET 通过运行时注入（见 docker-compose.yml 或 docker run -e）。
CMD ["gunicorn", "--bind", "0.0.0.0:9009", "--workers", "2", "--forwarded-allow-ips=*", "backend.app:app"]
