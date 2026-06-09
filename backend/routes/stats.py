"""
Itemly 统计路由
"""
from flask import Blueprint, jsonify
from utils.auth_utils import login_required
from models import StatsModel

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')


@stats_bp.route('', methods=['GET'])
@login_required
def get_stats():
    """获取统计数据"""
    stats = StatsModel.get_overall()
    return jsonify({
        'success': True,
        'data': stats
    })
