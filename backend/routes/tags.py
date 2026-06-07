"""
Itemly 标签路由
"""
from flask import Blueprint, request, jsonify, session
from models import TagModel

tags_bp = Blueprint('tags', __name__, url_prefix='/api/tags')


def check_auth():
    """检查登录状态"""
    if 'user_id' not in session:
        return False
    return True


@tags_bp.route('', methods=['GET'])
def get_tags():
    """获取标签列表（树形结构）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    tree = request.args.get('tree', 'true').lower() == 'true'

    if tree:
        tags = TagModel.get_tree()
    else:
        tags = TagModel.get_all()

    return jsonify({
        'success': True,
        'data': tags
    })


@tags_bp.route('', methods=['POST'])
def create_tag():
    """创建标签"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '标签名称不能为空'}), 400

    tag_id = TagModel.create(
        name=name,
        parent_id=parent_id if parent_id else None,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '标签创建成功',
        'data': {'id': tag_id}
    }), 201


@tags_bp.route('/<int:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    """更新标签"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order')

    if not name:
        return jsonify({'success': False, 'message': '标签名称不能为空'}), 400

    TagModel.update(
        tag_id=tag_id,
        name=name,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '标签更新成功'
    })


@tags_bp.route('/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """删除标签"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    TagModel.delete(tag_id)
    return jsonify({
        'success': True,
        'message': '标签删除成功'
    })
