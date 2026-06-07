"""
Itemly 统计路由
"""
from flask import Blueprint, jsonify, session
from models import StatsModel

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')


def check_auth():
    """检查登录状态"""
    if 'user_id' not in session:
        return False
    return True


@stats_bp.route('', methods=['GET'])
def get_stats():
    """获取统计数据"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    stats = StatsModel.get_overall()
    return jsonify({
        'success': True,
        'data': stats
    })
