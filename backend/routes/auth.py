"""
Itemly 认证路由
"""
import time
import logging
from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from utils.validators import require_username
from models import UserModel

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 登录失败计数（按 IP+用户名 维度）。生产环境建议替换为 Redis/数据库持久化。
_login_failure = {}  # key: (ip, username) -> (fail_count, lock_until_ts)
_MAX_FAILURE = 5
_LOCK_SECONDS = 300

audit = logging.getLogger('itemly.audit')


def _client_ip():
    return (request.headers.get('X-Forwarded-For') or request.remote_addr or 'unknown').split(',')[0].strip()


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录。失败次数超过阈值后临时锁定，防止暴力破解。"""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    ip = _client_ip()
    key = (ip, username)
    now = time.time()
    fail_count, lock_until = _login_failure.get(key, (0, 0))
    if lock_until > now:
        remain = int(lock_until - now)
        return jsonify({
            'success': False,
            'message': f'登录失败次数过多，请 {remain} 秒后重试'
        }), 429

    user = UserModel.verify_password(username, password)
    if user:
        _login_failure[key] = (0, 0)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.permanent = True
        audit.info('LOGIN_SUCCESS user=%s ip=%s', username, ip)
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'id': user['id'],
                'username': user['username'],
                'display_name': user['display_name']
            }
        })
    else:
        fail_count += 1
        lock_until = now + _LOCK_SECONDS if fail_count >= _MAX_FAILURE else 0
        _login_failure[key] = (fail_count, lock_until)
        audit.warning('LOGIN_FAILURE user=%s ip=%s fail_count=%d', username, ip, fail_count)
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出。"""
    username = session.get('username')
    session.clear()
    if username:
        audit.info('LOGOUT user=%s ip=%s', username, _client_ip())
    return jsonify({'success': True, 'message': '已退出登录'})


@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """检查登录状态。"""
    if 'user_id' in session:
        user = UserModel.find_by_id(session['user_id'])
        if user:
            return jsonify({
                'success': True,
                'authenticated': True,
                'data': {
                    'id': user['id'],
                    'username': user['username'],
                    'display_name': user['display_name']
                }
            })
    return jsonify({'success': True, 'authenticated': False})


@auth_bp.route('/password', methods=['PUT'])
@login_required
def change_password():
    """修改密码。保持原有接口契约（仅需两次新密码），增加最小长度与审计日志。"""
    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '密码不能为空'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少 6 位'}), 400

    UserModel.update_password(session['user_id'], new_password)
    audit.info('PASSWORD_CHANGED user=%s ip=%s', session.get('username'), _client_ip())
    return jsonify({'success': True, 'message': '密码修改成功'})


@auth_bp.route('/account', methods=['PUT'])
@login_required
def update_account():
    """修改用户名（长度 3-32，仅允许字母、数字、下划线、中划线、中文）。"""
    data = request.get_json(silent=True) or {}
    try:
        username = require_username(data.get('username'))
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    existing = UserModel.find_by_username(username)
    if existing and existing['id'] != session['user_id']:
        return jsonify({'success': False, 'message': '用户名已被使用'}), 400

    UserModel.update_username(session['user_id'], username)
    session['username'] = username
    audit.info('USERNAME_CHANGED old=%s new=%s ip=%s', session.get('username'), username, _client_ip())
    return jsonify({'success': True, 'message': '账号信息已更新'})
