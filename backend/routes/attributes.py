"""
Itemly 属性管理路由（替换原来的标签管理）
"""
import logging

from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from models import AttributeModel

audit = logging.getLogger('itemly.audit')

attributes_bp = Blueprint('attributes', __name__, url_prefix='/api/attributes')


@attributes_bp.route('', methods=['GET'])
@login_required
def get_attributes():
    """获取属性列表（树形结构）"""
    tree = request.args.get('tree', 'true').lower() == 'true'
    flat = request.args.get('flat', 'false').lower() == 'true'
    template_id = request.args.get('template_id')

    if template_id:
        template_id = int(template_id)
    
    if flat:
        attributes = AttributeModel.get_flat_tree(template_id=template_id)
    elif tree:
        attributes = AttributeModel.get_tree(template_id=template_id)
    else:
        attributes = AttributeModel.get_all(template_id=template_id)

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


@attributes_bp.route('/<int:attribute_id>/children', methods=['GET'])
@login_required
def get_attribute_children(attribute_id):
    """获取属性的子属性列表"""
    children = AttributeModel.get_children(attribute_id)
    return jsonify({
        'success': True,
        'data': children
    })


@attributes_bp.route('', methods=['POST'])
@login_required
def create_attribute():
    """创建属性（按 template_id 隔离属性树）"""
    data = request.get_json()
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    template_id = data.get('template_id')
    category_id = data.get('category_id')
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '属性名称不能为空'}), 400

    if not parent_id:
        parent_id = None

    # 如果提供了 category_id，自动获取对应的 template_id
    if category_id and not template_id:
        from models import TemplateModel
        template = TemplateModel.get_by_category(category_id)
        if template:
            template_id = template['id']
        else:
            return jsonify({'success': False, 'message': '无法找到对应的模板'}), 400

    if not template_id:
        return jsonify({'success': False, 'message': '必须指定模板ID'}), 400

    # 检查同级是否有同名属性（只在同一模板下检查）
    existing = AttributeModel.find_by_name_and_parent(name, parent_id, template_id)
    if existing:
        return jsonify({'success': False, 'message': '当前模板下已有同名属性'}), 400

    attribute_id = AttributeModel.create(
        name=name,
        parent_id=parent_id,
        template_id=template_id,
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

    # 获取当前属性信息（包括它的 parent_id、template_id）
    current_attr = AttributeModel.get_by_id(attribute_id)
    if not current_attr:
        return jsonify({'success': False, 'message': '属性不存在'}), 404

    # 检查同级是否有同名属性（排除自身，并在同一模板下检查）
    existing = AttributeModel.find_by_name_and_parent(
        name,
        current_attr.get('parent_id'),
        current_attr.get('template_id')
    )
    if existing and int(existing['id']) != int(attribute_id):
        return jsonify({'success': False, 'message': '当前模板下已有同名属性'}), 400

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

    # 检查被引用数量
    ref_count = AttributeModel.get_referenced_count(attribute_id)

    # 如果有引用，返回引用数量让前端确认
    if ref_count > 0:
        return jsonify({
            'success': False,
            'message': f'该属性被{ref_count}个物品引用，请确认删除'
        }), 400

    # 无引用，直接删除
    AttributeModel.delete(attribute_id)
    audit.info('ATTRIBUTE_DELETED id=%s user=%s', attribute_id, session.get('username'))
    return jsonify({
        'success': True,
        'message': '属性删除成功'
    })


@attributes_bp.route('/<int:attribute_id>/force-delete', methods=['DELETE'])
@login_required
def force_delete_attribute(attribute_id):
    """强制删除属性（忽略引用检查）"""
    attribute = AttributeModel.get_by_id(attribute_id)
    if not attribute:
        return jsonify({'success': False, 'message': '属性不存在'}), 404

    AttributeModel.delete(attribute_id)
    audit.info('ATTRIBUTE_FORCE_DELETED id=%s user=%s', attribute_id, session.get('username'))
    return jsonify({
        'success': True,
        'message': '属性删除成功'
    })


@attributes_bp.route('/<int:attribute_id>/check-reference', methods=['GET'])
@login_required
def check_attribute_reference(attribute_id):
    """检查属性被物品引用的情况"""
    attribute = AttributeModel.get_by_id(attribute_id)
    if not attribute:
        return jsonify({'success': False, 'message': '属性不存在'}), 404

    ref_count = AttributeModel.get_referenced_count(attribute_id)
    return jsonify({
        'success': True,
        'data': {
            'attribute_id': attribute_id,
            'attribute_name': attribute['name'],
            'referenced_count': ref_count
        }
    })
