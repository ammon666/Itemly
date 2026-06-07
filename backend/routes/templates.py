"""
Itemly 模板路由
"""
from flask import Blueprint, request, jsonify, session
from models import TemplateModel

templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')


def check_auth():
    """检查登录状态"""
    if 'user_id' not in session:
        return False
    return True


@templates_bp.route('', methods=['GET'])
def get_templates():
    """获取模板列表"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    with_fields = request.args.get('with_fields', 'false').lower() == 'true'

    if with_fields:
        templates = []
        for t in TemplateModel.get_all():
            templates.append(TemplateModel.get_with_fields(t['id']))
    else:
        templates = TemplateModel.get_all()

    return jsonify({
        'success': True,
        'data': templates
    })


@templates_bp.route('/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """获取模板详情"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    template = TemplateModel.get_with_fields(template_id)
    if not template:
        return jsonify({'success': False, 'message': '模板不存在'}), 404

    return jsonify({
        'success': True,
        'data': template
    })


@templates_bp.route('', methods=['POST'])
def create_template():
    """创建模板"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    fields = data.get('fields', [])

    if not name:
        return jsonify({'success': False, 'message': '模板名称不能为空'}), 400

    if not category_id:
        return jsonify({'success': False, 'message': '模板类别不能为空'}), 400

    template_id = TemplateModel.create(
        name=name,
        category_id=category_id
    )

    # 添加字段
    for i, field in enumerate(fields):
        TemplateModel.add_field(
            template_id=template_id,
            field_name=field.get('field_name', ''),
            field_type=field.get('field_type', 'text'),
            field_options=field.get('field_options'),
            sort_order=i
        )

    return jsonify({
        'success': True,
        'message': '模板创建成功',
        'data': {'id': template_id}
    }), 201


@templates_bp.route('/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """更新模板"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')

    if not name:
        return jsonify({'success': False, 'message': '模板名称不能为空'}), 400

    if not category_id:
        return jsonify({'success': False, 'message': '模板类别不能为空'}), 400

    TemplateModel.update(
        template_id=template_id,
        name=name,
        category_id=category_id
    )

    return jsonify({
        'success': True,
        'message': '模板更新成功'
    })


@templates_bp.route('/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """删除模板"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    TemplateModel.delete(template_id)
    return jsonify({
        'success': True,
        'message': '模板删除成功'
    })


@templates_bp.route('/<int:template_id>/fields', methods=['POST'])
def add_template_field(template_id):
    """添加模板字段"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    field_name = data.get('field_name', '').strip()
    field_type = data.get('field_type', 'text')
    field_options = data.get('field_options')
    sort_order = data.get('sort_order', 0)

    if not field_name:
        return jsonify({'success': False, 'message': '字段名称不能为空'}), 400

    field_id = TemplateModel.add_field(
        template_id=template_id,
        field_name=field_name,
        field_type=field_type,
        field_options=field_options,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '字段添加成功',
        'data': {'id': field_id}
    }), 201


@templates_bp.route('/fields/<int:field_id>', methods=['PUT'])
def update_template_field(field_id):
    """更新模板字段"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    field_name = data.get('field_name', '').strip()
    field_type = data.get('field_type')
    field_options = data.get('field_options')
    sort_order = data.get('sort_order')

    if not field_name:
        return jsonify({'success': False, 'message': '字段名称不能为空'}), 400

    TemplateModel.update_field(
        field_id=field_id,
        field_name=field_name,
        field_type=field_type,
        field_options=field_options,
        sort_order=sort_order
    )

    return jsonify({
        'success': True,
        'message': '字段更新成功'
    })


@templates_bp.route('/fields/<int:field_id>', methods=['DELETE'])
def delete_template_field(field_id):
    """删除模板字段"""
    if not check_auth():
        return jsonify({'success': False, 'message': '未登录'}), 401

    TemplateModel.delete_field(field_id)
    return jsonify({
        'success': True,
        'message': '字段删除成功'
    })
