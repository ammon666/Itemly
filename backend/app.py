"""
Itemly Flask应用入口
轻量化物品管理系统
"""
import os
from flask import Flask, send_from_directory, jsonify, request, session
from flask_cors import CORS
from models import init_db
from routes import auth_bp, items_bp, categories_bp, attributes_bp, stats_bp
from utils.auth_utils import login_required

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# 上传文件夹路径
UPLOAD_FOLDER = os.path.join(PROJECT_DIR, 'uploads')


def create_app():
    """创建Flask应用"""
    # 前端文件所在目录
    frontend_dir = os.path.join(PROJECT_DIR, 'frontend')
    html_dir = os.path.join(frontend_dir, 'html')

    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')

    # 配置
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'itemly-secret-key-change-in-production')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    # Session 配置 - 允许在非 HTTPS 环境下使用（开发环境）
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # 启用CORS
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
            # 返回index.html作为SPA的入口
            return send_from_directory(html_dir, 'index.html')
        # 尝试在frontend目录中查找静态文件
        file_path = os.path.join(frontend_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(frontend_dir, path)
        # 默认返回index.html
        return send_from_directory(html_dir, 'index.html')

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
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)