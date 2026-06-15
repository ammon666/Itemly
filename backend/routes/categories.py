"""
Itemly 类别路由（合并模板管理）
"""
import logging

from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from models import CategoryModel, TemplateModel, AttributeModel

audit = logging.getLogger('itemly.audit')

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')


@categories_bp.route('', methods=['GET'])
@login_required
def get_categories():
    """获取类别列表（包含模板信息）"""
    categories = CategoryModel.get_all()

    return jsonify({
        'success': True,
        'data': categories
    })


@categories_bp.route('/<int:category_id>', methods=['GET'])
@login_required
def get_category(category_id):
    """获取类别详情（包含模板属性）"""
    category = CategoryModel.get_by_id(category_id)
    if not category:
        return jsonify({'success': False, 'message': '类别不存在'}), 404

    # 获取模板的属性配置
    if category['template_id']:
        template = TemplateModel.get_with_attributes(category['template_id'])
        category['template'] = template

    return jsonify({
        'success': True,
        'data': category
    })


@categories_bp.route('', methods=['POST'])
@login_required
def create_category():
    """创建类别（自动创建模板）"""
    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '类别名称不能为空'}), 400

    # 检查类别名称是否重复
    existing = CategoryModel.find_by_name(name)
    if existing:
        return jsonify({'success': False, 'message': '类别名称已存在'}), 400

    # 创建类别（会自动创建模板）
    category_id = CategoryModel.create(name=name, sort_order=sort_order)

    return jsonify({
        'success': True,
        'message': '类别创建成功',
        'data': {'id': category_id}
    }), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """更新类别"""
    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order')

    if not name:
        return jsonify({'success': False, 'message': '类别名称不能为空'}), 400

    # 检查类别是否存在
    existing_category = CategoryModel.get_by_id(category_id)
    if not existing_category:
        return jsonify({'success': False, 'message': '类别不存在'}), 404

    # 检查类别名称是否与其他类别重复（排除自己）
    existing = CategoryModel.find_by_name(name)
    if existing and int(existing['id']) != int(category_id):
        return jsonify({'success': False, 'message': '类别名称已存在'}), 400

    updated_rows = CategoryModel.update(category_id=category_id, name=name, sort_order=sort_order)
    if updated_rows == 0:
        return jsonify({'success': False, 'message': '类别更新失败，请稍后重试'}), 500

    return jsonify({
        'success': True,
        'message': '类别更新成功'
    })


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """删除类别（物品自动转移到未分类）"""
    category = CategoryModel.get_by_id(category_id)
    if not category:
        return jsonify({'success': False, 'message': '类别不存在'}), 404

    # 检查是否是未分类
    if category['name'] == '未分类':
        return jsonify({'success': False, 'message': '不能删除未分类'}), 400

    CategoryModel.delete(category_id)
    audit.info('CATEGORY_DELETED id=%s user=%s', category_id, session.get('username'))
    return jsonify({
        'success': True,
        'message': '类别删除成功'
    })


# 模板相关操作（通过类别ID访问）
@categories_bp.route('/<int:category_id>/template', methods=['GET'])
@login_required
def get_category_template(category_id):
    """获取类别的模板配置"""
    template = TemplateModel.get_by_category(category_id)
    if not template:
        return jsonify({'success': False, 'message': '模板不存在'}), 404

    template = TemplateModel.get_with_attributes(template['id'])

    return jsonify({
        'success': True,
        'data': template
    })


@categories_bp.route('/<int:category_id>/template', methods=['PUT'])
@login_required
def update_category_template(category_id):
    """更新类别的模板配置"""
    template = TemplateModel.get_by_category(category_id)
    if not template:
        return jsonify({'success': False, 'message': '模板不存在'}), 404

    data = request.get_json()
    name = data.get('name', '').strip()  # 类别名称

    # 更新类别名称（如果提供了）
    if name:
        # 确认类别存在
        existing_category = CategoryModel.get_by_id(category_id)
        if not existing_category:
            return jsonify({'success': False, 'message': '类别不存在'}), 404
        existing = CategoryModel.find_by_name(name)
        if existing and int(existing['id']) != int(category_id):
            return jsonify({'success': False, 'message': '类别名称已存在'}), 400

        updated_rows = CategoryModel.update(category_id=category_id, name=name)
        if updated_rows == 0:
            return jsonify({'success': False, 'message': '类别名称更新失败，请稍后重试'}), 500

    return jsonify({
        'success': True,
        'message': '模板配置更新成功'
    })
