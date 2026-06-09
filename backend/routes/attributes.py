"""
Itemly 属性路由（替代原来的标签管理）
"""
from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from models import AttributeModel

attributes_bp = Blueprint('attributes', __name__, url_prefix='/api/attributes')


@attributes_bp.route('', methods=['GET'])
@login_required
def get_attributes():
    """获取属性列表（树形结构）"""
    tree = request.args.get('tree', 'true').lower() == 'true'
    flat = request.args.get('flat', 'false').lower() == 'true'

    if flat:
        attributes = AttributeModel.get_flat_tree()
    elif tree:
        attributes = AttributeModel.get_tree()
    else:
        attributes = AttributeModel.get_all()

    return jsonify({
        'success': True,
        'data': attributes
    })


@attributes_bp.route('/<int:attribute_id>', methods=['GET'])
@login_required
def get_attribute(attribute_id):
    """获取属性详情"""
    attribute = AttributeModel.get_by_id(attribute_id)
    if not attribute:
        return jsonify({'success': False, 'message': '属性不存在'}), 404

    # 获取子属性
    attribute['children'] = AttributeModel.get_children(attribute_id)

    return jsonify({
        'success': True,
        'data': attribute
    })


@attributes_bp.route('', methods=['POST'])
@login_required
def create_attribute():
    """创建属性"""
    data = request.get_json()
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '属性名称不能为空'}), 400

    attribute_id = AttributeModel.create(
        name=name,
        parent_id=parent_id if parent_id else None,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '属性创建成功',
        'data': {'id': attribute_id}
    }), 201


@attributes_bp.route('/<int:attribute_id>', methods=['PUT'])
@login_required
def update_attribute(attribute_id):
    """更新属性"""
    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order')

    if not name:
        return jsonify({'success': False, 'message': '属性名称不能为空'}), 400

    AttributeModel.update(
        attribute_id=attribute_id,
        name=name,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '属性更新成功'
    })


@attributes_bp.route('/<int:attribute_id>', methods=['DELETE'])
@login_required
def delete_attribute(attribute_id):
    """删除属性"""
    attribute = AttributeModel.get_by_id(attribute_id)
    if not attribute:
        return jsonify({'success': False, 'message': '属性不存在'}), 404

    AttributeModel.delete(attribute_id)
    return jsonify({
        'success': True,
        'message': '属性删除成功'
    })
