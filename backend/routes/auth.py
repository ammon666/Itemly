"""
Itemly 认证路由
"""
from flask import Blueprint, request, jsonify, session
from models import UserModel

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    user = UserModel.verify_password(username, password)
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
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
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})


@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """检查登录状态"""
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
def change_password():
    """修改密码（只需输入两次新密码）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '密码不能为空'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少6位'}), 400

    UserModel.update_password(session['user_id'], new_password)
    return jsonify({'success': True, 'message': '密码修改成功'})


@auth_bp.route('/account', methods=['PUT'])
def update_account():
    """修改用户名和显示名称"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    username = data.get('username', '').strip()
    display_name = data.get('display_name', '').strip()

    if not username:
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400

    if len(username) < 3:
        return jsonify({'success': False, 'message': '用户名至少3位'}), 400

    # 检查用户名是否已被使用
    from models import UserModel
    existing = UserModel.get_by_username(username)
    if existing and existing['id'] != session['user_id']:
        return jsonify({'success': False, 'message': '用户名已被使用'}), 400

    UserModel.update_account(session['user_id'], username, display_name)
    return jsonify({'success': True, 'message': '账号信息已更新'})