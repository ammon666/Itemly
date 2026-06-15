"""
Itemly 物品路由
"""
import logging

from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from models import ItemModel, TemplateModel, AttributeModel

audit = logging.getLogger('itemly.audit')

items_bp = Blueprint('items', __name__, url_prefix='/api/items')


def get_all_child_ids(attribute_id):
    """获取属性的所有子属性ID"""
    result = []
    children = AttributeModel.get_children(attribute_id)
    for child in children:
        result.append(child['id'])
        result.extend(get_all_child_ids(child['id']))
    return result


@items_bp.route('', methods=['GET'])
@login_required
def get_items():
    """获取物品列表（支持分页）"""
    template_id = request.args.get('template_id', type=int)
    keyword = request.args.get('keyword', '')

    # 支持多个类别ID筛选
    category_ids_str = request.args.get('category_ids', '')
    category_ids = []
    if category_ids_str:
        try:
            category_ids = [int(x) for x in category_ids_str.split(',') if x.strip()]
        except ValueError:
            category_ids = []

    # 支持多个属性ID筛选
    attribute_ids_str = request.args.get('attribute_ids', '')
    attribute_ids = []
    if attribute_ids_str:
        try:
            attribute_ids = [int(x) for x in attribute_ids_str.split(',') if x.strip()]
        except ValueError:
            attribute_ids = []

    # 分页参数
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', type=int)

    # 如果指定了类别ID，先获取模板ID（支持多个类别）
    template_ids = []
    if category_ids:
        for cat_id in category_ids:
            template = TemplateModel.get_by_category(cat_id)
            if template:
                template_ids.append(template['id'])
        if template_ids:
            template_id = None  # 使用多个模板ID

    items = ItemModel.get_all(
        template_id=template_id,
        template_ids=template_ids if template_ids else None,
        keyword=keyword if keyword else None,
        attribute_ids=attribute_ids if attribute_ids else None,
        page=page,
        per_page=per_page
    )

    # 如果使用了分页，返回总数
    response = {'success': True, 'data': items}
    if page and per_page:
        total = ItemModel.count(
            template_id=template_id,
            template_ids=template_ids if template_ids else None,
            keyword=keyword if keyword else None,
            attribute_ids=attribute_ids if attribute_ids else None
        )
        response['total'] = total
        response['page'] = page
        response['per_page'] = per_page

    return jsonify(response)


@items_bp.route('/<int:item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    """获取物品详情"""
    item = ItemModel.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': '物品不存在'}), 404

    return jsonify({
        'success': True,
        'data': item
    })


@items_bp.route('', methods=['POST'])
@login_required
def create_item():
    """创建物品（必须选择模板）"""
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
            attr_id = req_attr['attribute_id']
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


@items_bp.route('/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    """更新物品"""
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
@login_required
def delete_item(item_id):
    """删除物品"""
    item = ItemModel.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': '物品不存在'}), 404

    ItemModel.delete(item_id)
    audit.info('ITEM_DELETED id=%s user=%s', item_id, session.get('username'))
    return jsonify({
        'success': True,
        'message': '物品删除成功'
    })


@items_bp.route('/batch-delete', methods=['POST'])
@login_required
def batch_delete_items():
    """批量删除物品"""
    data = request.get_json()
    item_ids = data.get('item_ids', [])

    if not item_ids:
        return jsonify({'success': False, 'message': '请选择要删除的物品'}), 400

    ItemModel.batch_delete(item_ids)
    audit.info('ITEM_BATCH_DELETED count=%s user=%s', len(item_ids), session.get('username'))
    return jsonify({
        'success': True,
        'message': f'成功删除 {len(item_ids)} 个物品'
    })


@items_bp.route('/batch-attributes', methods=['POST'])
@login_required
def batch_update_attributes():
    """批量为物品添加或移除属性"""
    data = request.get_json()
    item_ids = data.get('item_ids', [])
    attribute_ids = data.get('attribute_ids', [])
    action = data.get('action', 'add')

    if not item_ids or not attribute_ids:
        return jsonify({'success': False, 'message': '请选择物品和属性'}), 400

    if action == 'remove':
        ItemModel.batch_remove_attributes(item_ids, attribute_ids)
        audit.info('ITEM_BATCH_REMOVE_ATTRIBUTES item_count=%s attr_count=%s user=%s', len(item_ids), len(attribute_ids), session.get('username'))
        return jsonify({'success': True, 'message': f'已为 {len(item_ids)} 个物品移除属性'})
    else:
        ItemModel.batch_add_attributes(item_ids, attribute_ids)
        audit.info('ITEM_BATCH_ADD_ATTRIBUTES item_count=%s attr_count=%s user=%s', len(item_ids), len(attribute_ids), session.get('username'))
        return jsonify({'success': True, 'message': f'已为 {len(item_ids)} 个物品添加属性'})
