"""
Itemly 物品路由
"""
from flask import Blueprint, request, jsonify, session
from models import ItemModel, CategoryModel, TagModel

items_bp = Blueprint('items', __name__, url_prefix='/api/items')


def check_auth():
    """检查登录状态"""
    if 'user_id' not in session:
        return False
    return True


@items_bp.route('', methods=['GET'])
def get_items():
    """获取物品列表"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    category_id = request.args.get('category_id', type=int)
    tag_id = request.args.get('tag_id', type=int)
    keyword = request.args.get('keyword', '')

    items = ItemModel.get_all(
        category_id=category_id,
        tag_id=tag_id,
        keyword=keyword if keyword else None
    )

    return jsonify({
        'success': True,
        'data': items
    })


@items_bp.route('/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """获取物品详情"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    item = ItemModel.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': '物品不存在'}), 404

    return jsonify({
        'success': True,
        'data': item
    })


@items_bp.route('', methods=['POST'])
def create_item():
    """创建物品"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    remark = data.get('remark', '')
    images = data.get('images', '')
    tag_ids = data.get('tag_ids', [])
    field_values = data.get('field_values', {})

    if not name:
        return jsonify({'success': False, 'message': '物品名称不能为空'}), 400

    if not category_id:
        return jsonify({'success': False, 'message': '物品类别不能为空'}), 400

    if not images:
        return jsonify({'success': False, 'message': '物品图片不能为空'}), 400

    item_id = ItemModel.create(
        name=name,
        category_id=category_id if category_id else None,
        remark=remark,
        images=images,
        tag_ids=tag_ids if tag_ids else None,
        field_values=field_values if field_values else None
    )

    return jsonify({
        'success': True,
        'message': '物品创建成功',
        'data': {'id': item_id}
    }), 201


@items_bp.route('/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """更新物品"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name')
    category_id = data.get('category_id')
    remark = data.get('remark')
    images = data.get('images')
    tag_ids = data.get('tag_ids')
    field_values = data.get('field_values')

    item = ItemModel.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': '物品不存在'}), 404

    ItemModel.update(
        item_id=item_id,
        name=name.strip() if name else None,
        category_id=category_id,
        remark=remark,
        images=images,
        tag_ids=tag_ids,
        field_values=field_values
    )

    return jsonify({
        'success': True,
        'message': '物品更新成功'
    })


@items_bp.route('/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """删除物品"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    item = ItemModel.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': '物品不存在'}), 404

    ItemModel.delete(item_id)
    return jsonify({
        'success': True,
        'message': '物品删除成功'
    })


@items_bp.route('/batch-delete', methods=['POST'])
def batch_delete_items():
    """批量删除物品"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    item_ids = data.get('item_ids', [])

    if not item_ids:
        return jsonify({'success': False, 'message': '请选择要删除的物品'}), 400

    ItemModel.batch_delete(item_ids)
    return jsonify({
        'success': True,
        'message': f'成功删除 {len(item_ids)} 个物品'
    })


@items_bp.route('/batch-update', methods=['POST'])
def batch_update_items():
    """批量更新物品类别"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    item_ids = data.get('item_ids', [])
    category_id = data.get('category_id')

    if not item_ids:
        return jsonify({'success': False, 'message': '请选择要更新的物品'}), 400

    ItemModel.batch_update(category_id, item_ids)
    return jsonify({
        'success': True,
        'message': f'成功更新 {len(item_ids)} 个物品'
    })
