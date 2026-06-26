"""
Itemly 认证路由
"""
import secrets
import time
import logging
from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from utils.validators import require_username, require_email
from models import UserModel

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 登录失败计数（按 IP+用户名 维度）。生产环境建议替换为 Redis/数据库持久化。
_login_failure = {}  # key: (ip, username) -> (fail_count, lock_until_ts)
_MAX_FAILURE = 5
_LOCK_SECONDS = 300

# 找回密码：邮箱校验失败计数；key: (ip, username) -> (fail_count, lock_until_ts)
_recover_failure = {}
_RECOVER_MAX_FAILURE = 3
_RECOVER_LOCK_SECONDS = 3600

# 找回密码成功后下发的一次性 token；key: token_str -> {user_id, expire_ts}
_recover_tokens = {}
_RECOVER_TOKEN_TTL = 600

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
        session['user_id'] = int(user['id'])
        session['username'] = user['username']
        session.permanent = True
        init_status = UserModel.check_initialization(user['id']) or {}
        audit.info('LOGIN_SUCCESS user=%s ip=%s', username, ip)
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'id': user['id'],
                'username': user['username'],
                'display_name': user['display_name'],
                'email': user.get('email') or '',
                'password_changed': bool(init_status.get('password_changed')),
                'email_is_set': bool(init_status.get('email_is_set')),
                'need_first_setup': bool(init_status.get('need_first_setup')),
            },
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
            init_status = UserModel.check_initialization(session['user_id']) or {}
            return jsonify({
                'success': True,
                'authenticated': True,
                'data': {
                    'id': user['id'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'email': user.get('email') or '',
                    'password_changed': bool(init_status.get('password_changed')),
                    'email_is_set': bool(init_status.get('email_is_set')),
                    'need_first_setup': bool(init_status.get('need_first_setup')),
                },
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

    if username.lower() == 'admin':
        return jsonify({'success': False, 'message': '用户名不能是 admin'}), 400

    existing = UserModel.find_by_username(username)
    if existing and int(existing['id']) != int(session['user_id']):
        return jsonify({'success': False, 'message': '用户名已被使用'}), 400

    UserModel.update_username(session['user_id'], username)
    session['username'] = username
    session['user_id'] = int(session['user_id'])
    audit.info('USERNAME_CHANGED old=%s new=%s ip=%s', session.get('username'), username, _client_ip())
    return jsonify({'success': True, 'message': '账号信息已更新'})


@auth_bp.route('/first-setup', methods=['POST'])
@login_required
def first_setup():
    """首次登录初始化：要求用户填写新用户名（非 admin）+ 新密码 + 邮箱。"""
    data = request.get_json(silent=True) or {}

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''
    email = (data.get('email') or '').strip()

    if not username or not password or not confirm_password or not email:
        return jsonify({'success': False, 'message': '用户名、密码、邮箱均不能为空'}), 400

    try:
        username = require_username(username)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    if username.lower() == 'admin':
        return jsonify({'success': False, 'message': '新用户名不能是 admin'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少 6 位'}), 400
    if password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400

    try:
        email = require_email(email)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    # 用户名唯一性校验
    existing = UserModel.find_by_username(username)
    if existing and int(existing['id']) != int(session['user_id']):
        return jsonify({'success': False, 'message': '用户名已被使用'}), 400

    UserModel.first_time_setup(session['user_id'], username, password, email)
    session['username'] = username
    session['user_id'] = int(session['user_id'])

    audit.info('FIRST_SETUP user_id=%s new_username=%s ip=%s', session.get('user_id'), username, _client_ip())
    return jsonify({
        'success': True,
        'message': '初始化完成',
        'data': {'username': username},
    })


@auth_bp.route('/password/recover/request', methods=['POST'])
def recover_request():
    """找回密码第一步：校验用户名与存储邮箱是否一致。
    - 连续失败 3 次则锁定 1 小时；
    - 校验通过则下发一个 10 分钟有效的 token，供下一步重置密码使用。
    """
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()

    if not username or not email:
        return jsonify({'success': False, 'message': '用户名和邮箱不能为空'}), 400

    ip = _client_ip()
    key = (ip, username)
    now = time.time()
    fail_count, lock_until = _recover_failure.get(key, (0, 0))
    if lock_until > now:
        remain = int(lock_until - now)
        return jsonify({
            'success': False,
            'message': f'连续输错 3 次，请 {remain} 秒后再尝试',
            'lock_remain_seconds': remain,
        }), 429

    user = UserModel.find_by_username(username)
    if not user:
        # 用户不存在也按"邮箱不一致"处理，避免泄露用户列表
        fail_count += 1
        _recover_failure[key] = (fail_count, now + _RECOVER_LOCK_SECONDS if fail_count >= _RECOVER_MAX_FAILURE else 0)
        remain = int(_recover_failure[key][1] - now) if _recover_failure[key][1] > now else 0
        return jsonify({
            'success': False,
            'message': f'邮箱或用户名不正确，你还可以尝试 {max(_RECOVER_MAX_FAILURE - fail_count, 0)} 次',
            'fail_count': fail_count,
            'lock_remain_seconds': remain,
        }), 422

    stored_email = (user.get('email') or '').strip()
    if not stored_email:
        return jsonify({'success': False, 'message': '该账号尚未设置邮箱，无法找回密码'}), 400

    if stored_email.lower() != email.lower():
        fail_count += 1
        _recover_failure[key] = (fail_count, now + _RECOVER_LOCK_SECONDS if fail_count >= _RECOVER_MAX_FAILURE else 0)
        remain = int(_recover_failure[key][1] - now) if _recover_failure[key][1] > now else 0
        audit.warning('RECOVER_EMAIL_MISMATCH user=%s ip=%s fail_count=%d', username, ip, fail_count)
        return jsonify({
            'success': False,
            'message': f'邮箱或用户名不正确，你还可以尝试 {max(_RECOVER_MAX_FAILURE - fail_count, 0)} 次',
            'fail_count': fail_count,
            'lock_remain_seconds': remain,
        }), 422

    # 邮箱匹配：下发一个一次性 token
    token = secrets.token_urlsafe(32)
    _recover_tokens[token] = {'user_id': user['id'], 'expire_ts': now + _RECOVER_TOKEN_TTL}
    _recover_failure[key] = (0, 0)
    audit.info('RECOVER_REQUEST user=%s ip=%s', username, ip)
    return jsonify({
        'success': True,
        'message': '邮箱已验证，请在 10 分钟内设置新密码',
        'data': {'token': token},
    })


@auth_bp.route('/password/recover/reset', methods=['POST'])
def recover_reset():
    """找回密码第二步：使用 token 重置密码。"""
    data = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not token or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少 6 位'}), 400
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400

    now = time.time()
    info = _recover_tokens.get(token)
    if not info or info.get('expire_ts', 0) < now:
        _recover_tokens.pop(token, None)
        return jsonify({'success': False, 'message': '验证链接已过期或不存在，请重新发起找回密码'}), 410

    user_id = info.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '无效的验证信息'}), 410

    try:
        rows = UserModel.reset_password(user_id, new_password)
        if rows == 0:
            audit.warning('RECOVER_RESET_NO_ROW user_id=%s', user_id)
            return jsonify({'success': False, 'message': '用户不存在'}), 400
        _recover_tokens.pop(token, None)
        audit.info('RECOVER_RESET_OK user_id=%s ip=%s rows=%s', user_id, _client_ip(), rows)
        return jsonify({'success': True, 'message': '密码已重置，请使用新密码登录'})
    except Exception:
        audit.exception('RECOVER_RESET_ERROR user_id=%s', user_id)
        return jsonify({'success': False, 'message': '重置密码失败，请稍后重试'}), 500
