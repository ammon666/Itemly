"""
Itemly 类别路由（合并模板管理）
"""
from flask import Blueprint, request, jsonify, session
from utils.auth_utils import login_required
from models import CategoryModel, TemplateModel

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
    """创建类别（自动创建模板和属性配置）"""
    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order', 0)
    attributes = data.get('attributes', [])

    if not name:
        return jsonify({'success': False, 'message': '类别名称不能为空'}), 400

    # 创建类别
    category_id = CategoryModel.create(name=name, sort_order=sort_order)
    
    # 获取自动创建的模板ID
    category = CategoryModel.get_by_id(category_id)
    if category and category['template_id']:
        # 添加属性配置
        for i, attr in enumerate(attributes):
            TemplateModel.add_attribute(
                template_id=category['template_id'],
                attribute_id=attr['attribute_id'],
                is_required=attr.get('is_required', False),
                sort_order=i
            )

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

    CategoryModel.update(category_id=category_id, name=name, sort_order=sort_order)

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
    """更新类别的模板（属性配置）"""
    template = TemplateModel.get_by_category(category_id)
    if not template:
        return jsonify({'success': False, 'message': '模板不存在'}), 404

    data = request.get_json()
    template_name = data.get('template_name', '').strip()
    attributes = data.get('attributes', [])

    # 更新模板名称
    if template_name:
        TemplateModel.update_name(template['id'], template_name)

    # 清空原有属性配置
    TemplateModel.clear_attributes(template['id'])

    # 添加新的属性配置
    for i, attr in enumerate(attributes):
        TemplateModel.add_attribute(
            template_id=template['id'],
            attribute_id=attr['attribute_id'],
            is_required=attr.get('is_required', False),
            sort_order=i
        )

    return jsonify({
        'success': True,
        'message': '模板配置更新成功'
    })
