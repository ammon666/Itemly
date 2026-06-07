"""
Itemly 类别路由
"""
from flask import Blueprint, request, jsonify, session
from models import CategoryModel

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')


def check_auth():
    """检查登录状态"""
    if 'user_id' not in session:
        return False
    return True


@categories_bp.route('', methods=['GET'])
def get_categories():
    """获取类别列表（树形结构）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    tree = request.args.get('tree', 'true').lower() == 'true'

    if tree:
        categories = CategoryModel.get_tree()
    else:
        categories = CategoryModel.get_all()

    return jsonify({
        'success': True,
        'data': categories
    })


@categories_bp.route('', methods=['POST'])
def create_category():
    """创建类别"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '类别名称不能为空'}), 400

    category_id = CategoryModel.create(
        name=name,
        parent_id=parent_id if parent_id else None,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '类别创建成功',
        'data': {'id': category_id}
    }), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新类别"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order')

    if not name:
        return jsonify({'success': False, 'message': '类别名称不能为空'}), 400

    CategoryModel.update(
        category_id=category_id,
        name=name,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '类别更新成功'
    })


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """删除类别"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    CategoryModel.delete(category_id)
    return jsonify({
        'success': True,
        'message': '类别删除成功'
    })
