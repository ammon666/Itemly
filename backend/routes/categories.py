"""
Itemly 类别路由（合并模板管理）
"""
from flask import Blueprint, request, jsonify, session
from models import CategoryModel, TemplateModel

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')


def check_auth():
    """检查登录状态"""
    if 'user_id' not in session:
        return False
    return True


@categories_bp.route('', methods=['GET'])
def get_categories():
    """获取类别列表（包含模板信息）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    with_template = request.args.get('with_template', 'true').lower() == 'true'

    if with_template:
        categories = CategoryModel.get_all()
    else:
        categories = CategoryModel.get_all()

    return jsonify({
        'success': True,
        'data': categories
    })


@categories_bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """获取类别详情（包含模板属性）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

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
def create_category():
    """创建类别（自动创建模板）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '类别名称不能为空'}), 400

    category_id = CategoryModel.create(name=name, sort_order=sort_order)

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

    CategoryModel.update(category_id=category_id, name=name, sort_order=sort_order)

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


# 模板相关操作（通过类别ID访问）
@categories_bp.route('/<int:category_id>/template', methods=['GET'])
def get_category_template(category_id):
    """获取类别的模板配置"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    template = TemplateModel.get_by_category(category_id)
    if not template:
        return jsonify({'success': False, 'message': '模板不存在'}), 404

    template = TemplateModel.get_with_attributes(template['id'])

    return jsonify({
        'success': True,
        'data': template
    })


@categories_bp.route('/<int:category_id>/template', methods=['PUT'])
def update_category_template(category_id):
    """更新类别的模板（属性配置）"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

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