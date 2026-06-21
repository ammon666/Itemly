"""
Itemly Flask应用入口
轻量化物品管理系统
"""
import os
import sys
import logging
from datetime import timedelta

# 保证 gunicorn（以包方式导入 backend.app）也能找到同级模块 models/routes/utils
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from flask import Flask, send_from_directory, jsonify, request, session, g
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from models import init_db
from routes import auth_bp, items_bp, categories_bp, attributes_bp, stats_bp
from utils.auth_utils import login_required

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# 上传文件夹路径
UPLOAD_FOLDER = os.environ.get(
    'ITEMLY_UPLOAD_DIR',
    os.path.join(PROJECT_DIR, 'uploads')
)

# 全局日志与审计日志
_logging_configured = False


def _setup_logging():
    """配置应用日志。避免被多次调用时重复添加 handler。"""
    global _logging_configured
    if _logging_configured:
        return
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    audit = logging.getLogger('itemly.audit')
    audit.setLevel(logging.INFO)
    _logging_configured = True


def create_app():
    """创建Flask应用"""
    _setup_logging()

    # 前端文件所在目录
    frontend_dir = os.path.join(PROJECT_DIR, 'frontend')
    html_dir = os.path.join(frontend_dir, 'html')

    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')

    # 每个请求内共享一个 sqlite 连接；请求结束后自动关闭
    @app.before_request
    def _open_db():
        from models import DATABASE_PATH
        import sqlite3
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        g.db = conn

    @app.teardown_request
    def _close_db(exc=None):
        conn = getattr(g, 'db', None)
        if conn is not None:
            try:
                if exc is not None:
                    conn.rollback()
                else:
                    # 由具体业务代码提交，这里仅关闭
                    pass
            finally:
                conn.close()
                g.db = None

    # 配置
    # SECRET_KEY：生产环境必须通过 FLASK_SECRET 环境变量注入；
    # 未设置时自动生成临时密钥并记录警告（重启或多 worker 部署会导致已有会话失效）。
    _secret = os.environ.get('FLASK_SECRET')
    if not _secret:
        import secrets
        _secret = secrets.token_hex(32)
        logging.getLogger('itemly.audit').warning(
            'FLASK_SECRET 未设置，本次启动使用自动生成的临时密钥；'
            '重启或多 worker 部署会导致已有会话失效，请在生产环境中显式设置 FLASK_SECRET。'
        )
    app.config['SECRET_KEY'] = _secret
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

    # Session Cookie：
    #   - SECURE / SAMESITE 通过环境变量显式可控，避免仅依据 FLASK_ENV 的隐式判断
    #     造成"请先登录"等难以排查的问题（HTTP 访问时浏览器不回传 Secure cookie）。
    #   - 默认值：SECURE=false（兼容 HTTP 反向代理/局域网部署）；
    #     SAMESITE=Lax，兼顾安全性与可用性（Strict 会导致跨站点导航/部分反向代
    #     理场景下丢失 session）。HTTPS 部署时请显式设置 SESSION_COOKIE_SECURE=true。
    _secure_env = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower()
    if _secure_env in ('1', 'true', 'yes', 'on'):
        app.config['SESSION_COOKIE_SECURE'] = True
    elif _secure_env in ('0', 'false', 'no', 'off', 'auto'):
        app.config['SESSION_COOKIE_SECURE'] = False
    else:
        app.config['SESSION_COOKIE_SECURE'] = False
    _samesite = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    if str(_samesite).lower() not in ('strict', 'lax', 'none'):
        _samesite = 'Lax'
    app.config['SESSION_COOKIE_SAMESITE'] = _samesite
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_NAME'] = os.environ.get(
        'SESSION_COOKIE_NAME', 'itemly_session'
    )
    app.config['SESSION_COOKIE_PATH'] = '/'

    # 允许反向代理通过 X-Forwarded-* 头传递真实协议/客户端 IP/主机名。
    # 这对 Nginx 反向代理、Docker 部署后通过外网域名访问尤其关键，否则 Flask
    # 可能误判请求协议或来源 IP，影响 session 与审计日志。
    def _int_env(name, default):
        try:
            return int(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=_int_env('PROXY_FIX_X_FOR', 1),
        x_proto=_int_env('PROXY_FIX_X_PROTO', 1),
        x_host=_int_env('PROXY_FIX_X_HOST', 1),
        x_port=_int_env('PROXY_FIX_X_PORT', 0),
        x_prefix=_int_env('PROXY_FIX_X_PREFIX', 0),
    )

    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # 启用 CORS：同源部署下默认无需，但保留对携带凭据跨域的兼容能力。
    # 使用显式的 origins 列表比 "*" 更安全，避免浏览器拒绝携带 cookie 的跨域请求。
    _cors_origins = os.environ.get('CORS_ORIGINS', '')
    if _cors_origins:
        _origins = [o.strip() for o in _cors_origins.split(',') if o.strip()]
        CORS(app, supports_credentials=True, origins=_origins)
    else:
        CORS(app, supports_credentials=True)

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(attributes_bp)
    app.register_blueprint(stats_bp)

    # 初始化数据库
    init_db()

    # 提供上传文件的访问
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    # 提供前端静态文件
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path == '' or path == 'index.html':
            index_path = os.path.join(html_dir, 'index.html')
            if not os.path.exists(index_path):
                return (
                    '<html><head><meta charset="utf-8"><title>Itemly</title></head>'
                    '<body style="font-family:sans-serif;padding:40px;text-align:center;">'
                    '<h2>前端页面未部署</h2>'
                    '<p>请在 Dockerfile 中添加 <code>COPY frontend/ ./frontend/</code> 后重新构建镜像。</p>'
                    '</body></html>'
                ), 500
            return send_from_directory(html_dir, 'index.html')
        # 尝试在frontend目录中查找静态文件
        file_path = os.path.join(frontend_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(frontend_dir, path)
        # 默认返回index.html
        index_path = os.path.join(html_dir, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(html_dir, 'index.html')
        # 前端页面未部署
        return (
            '<html><head><meta charset="utf-8"><title>Itemly</title></head>'
            '<body style="font-family:sans-serif;padding:40px;text-align:center;">'
            '<h2>前端页面未部署</h2>'
            '<p>请在 Dockerfile 中添加 <code>COPY frontend/ ./frontend/</code> 后重新构建镜像。</p>'
            '</body></html>'
        ), 500

    # 上传图片API
    @app.route('/api/upload', methods=['POST'])
    @login_required
    def upload_image():
        from utils.file_utils import save_base64_image

        data = request.get_json()
        image_data = data.get('image')

        if not image_data:
            return jsonify({'success': False, 'message': '没有图片数据'}), 400

        filename = save_base64_image(image_data, UPLOAD_FOLDER)
        if filename:
            return jsonify({
                'success': True,
                'data': {'filename': filename}
            })
        else:
            return jsonify({'success': False, 'message': '图片保存失败'}), 500

    # 删除图片API
    @app.route('/api/upload/<filename>', methods=['DELETE'])
    @login_required
    def delete_image(filename):
        from utils.file_utils import delete_image

        if delete_image(filename, UPLOAD_FOLDER):
            return jsonify({'success': True, 'message': '图片删除成功'})
        else:
            return jsonify({'success': False, 'message': '图片删除失败'}), 500

    # 全局错误处理
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'success': False, 'message': '请求参数错误'}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'message': '请求的资源不存在'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'success': False, 'message': '请求方法不允许'}), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'未处理异常: {str(error)}')
        return jsonify({'success': False, 'message': '服务器处理请求时发生错误'}), 500

    return app


# 创建应用实例
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9009))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)