"""
认证工具函数
"""
from functools import wraps
from flask import jsonify, session


def login_required(f):
    """登录认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated_function
