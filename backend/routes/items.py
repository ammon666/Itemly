"""
Itemly 物品路由
"""
from flask import Blueprint, request, jsonify, session
from models import ItemModel, TemplateModel, AttributeModel

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

    template_id = request.args.get('template_id', type=int)
    category_id = request.args.get('category_id', type=int)
    keyword = request.args.get('keyword', '')

    # 如果指定了类别ID，先获取模板ID
    if category_id and not template_id:
        template = TemplateModel.get_by_category(category_id)
        if template:
            template_id = template['id']

    items = ItemModel.get_all(
        template_id=template_id,
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
    """创建物品（必须选择模板）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    template_id = data.get('template_id')
    remark = data.get('remark', '')
    images = data.get('images', '')
    attribute_ids = data.get('attribute_ids', [])

    if not name:
        return jsonify({'success': False, 'message': '物品名称不能为空'}), 400

    if not template_id:
        return jsonify({'success': False, 'message': '必须选择模板'}), 400

    if not images:
        return jsonify({'success': False, 'message': '物品图片不能为空'}), 400

    # 验证必填属性
    template = TemplateModel.get_with_attributes(template_id)
    if template and template['attributes']:
        required_attrs = [a for a in template['attributes'] if a['is_required']]
        for req_attr in required_attrs:
            # 检查是否选择了该属性或其子属性
            attr_id = req_attr['attribute_id']
            # 获取该属性的所有子属性ID
            all_child_ids = get_all_child_ids(attr_id)
            valid_ids = [attr_id] + all_child_ids
            if not any(aid in valid_ids for aid in attribute_ids):
                return jsonify({
                    'success': False,
                    'message': f'必填属性"{req_attr["attribute_name"]}"未填写'
                }), 400

    item_id = ItemModel.create(
        name=name,
        template_id=template_id,
        remark=remark,
        images=images,
        attribute_ids=attribute_ids if attribute_ids else None
    )

    return jsonify({
        'success': True,
        'message': '物品创建成功',
        'data': {'id': item_id}
    }), 201


def get_all_child_ids(attribute_id):
    """获取属性的所有子属性ID"""
    result = []
    children = AttributeModel.get_children(attribute_id)
    for child in children:
        result.append(child['id'])
        result.extend(get_all_child_ids(child['id']))
    return result


@items_bp.route('/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """更新物品"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name')
    remark = data.get('remark')
    images = data.get('images')
    attribute_ids = data.get('attribute_ids')

    item = ItemModel.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': '物品不存在'}), 404

    # 验证必填属性
    if attribute_ids is not None and item['template_id']:
        template = TemplateModel.get_with_attributes(item['template_id'])
        if template and template['attributes']:
            required_attrs = [a for a in template['attributes'] if a['is_required']]
            for req_attr in required_attrs:
                attr_id = req_attr['attribute_id']
                all_child_ids = get_all_child_ids(attr_id)
                valid_ids = [attr_id] + all_child_ids
                if not any(aid in valid_ids for aid in attribute_ids):
                    return jsonify({
                        'success': False,
                        'message': f'必填属性"{req_attr["attribute_name"]}"未填写'
                    }), 400

    ItemModel.update(
        item_id=item_id,
        name=name.strip() if name else None,
        remark=remark,
        images=images,
        attribute_ids=attribute_ids
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