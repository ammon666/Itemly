"""
Itemly 数据库模型
轻量化物品管理系统
"""
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'itemly.db')


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_columns(table_name):
    """获取表的所有列名"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return columns
    finally:
        conn.close()


def init_db(force_recreate=False):
    """初始化数据库"""
    conn = get_db()
    try:
        cursor = conn.cursor()

        if force_recreate:
            # 删除现有表（按外键依赖顺序删除）
            cursor.execute('DROP TABLE IF EXISTS item_attributes')
            cursor.execute('DROP TABLE IF EXISTS items')
            cursor.execute('DROP TABLE IF EXISTS attributes')
            cursor.execute('DROP TABLE IF EXISTS templates')
            cursor.execute('DROP TABLE IF EXISTS categories')
            cursor.execute('DROP TABLE IF EXISTS users')

        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建类别表（单层级，每个类别必须有模板）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建模板表（每个类别必须有一个模板）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')

        # 创建属性表（多级树形结构；template_id 用于按模板隔离属性树）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                template_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES attributes(id) ON DELETE CASCADE,
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
            )
        ''')



        # 创建物品表（必须选择模板）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                template_id INTEGER NOT NULL,
                remark TEXT,
                images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
            )
        ''')

        # 创建物品属性值表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS item_attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                attribute_id INTEGER NOT NULL,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
            )
        ''')

        # 创建默认管理员用户（如果不存在）
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            password_hash = generate_password_hash('admin123')
            cursor.execute(
                'INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)',
                ('admin', password_hash, '管理员')
            )

        conn.commit()
    finally:
        conn.close()


def dict_from_row(row):
    """将sqlite Row转换为字典"""
    if row is None:
        return None
    return dict(row)


class UserModel:
    """用户模型"""

    @staticmethod
    def find_by_username(username):
        """根据用户名查找用户"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            return dict_from_row(user)
        finally:
            conn.close()

    @staticmethod
    def find_by_id(user_id):
        """根据ID查找用户"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            return dict_from_row(user)
        finally:
            conn.close()

    @staticmethod
    def verify_password(username, password):
        """验证密码"""
        user = UserModel.find_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None

    @staticmethod
    def update_password(user_id, new_password):
        """更新密码（直接设置新密码）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            password_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def update_username(user_id, username):
        """更新用户名"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
            conn.commit()
        finally:
            conn.close()
        return True


class CategoryModel:
    """类别模型（单层级，每个类别必须有模板）"""

    @staticmethod
    def get_all():
        """获取所有类别（包含属性信息）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, t.id as template_id, t.name as template_name
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                ORDER BY c.sort_order, c.name
            ''')
            categories = cursor.fetchall()
            result = []
            
            # 预先获取所有属性，按模板分组
            cursor.execute('SELECT * FROM attributes ORDER BY sort_order, name')
            all_attrs = cursor.fetchall()
            attrs_by_template = {}
            for attr in all_attrs:
                attr_dict = dict_from_row(attr)
                template_id = attr_dict['template_id']
                if template_id not in attrs_by_template:
                    attrs_by_template[template_id] = []
                attrs_by_template[template_id].append(attr_dict)
            
            # 构建树形结构的辅助函数
            def build_attr_tree(attrs):
                tree = []
                for attr in attrs:
                    if attr['parent_id'] is None:
                        tree.append({
                            'id': attr['id'],
                            'name': attr['name'],
                            'parent_id': None,
                            'template_id': attr['template_id'],
                            'sort_order': attr['sort_order'],
                            'is_required': False,
                            'children': []
                        })
                
                def add_children(parent):
                    for attr in attrs:
                        if attr['parent_id'] == parent['id']:
                            child = {
                                'id': attr['id'],
                                'name': attr['name'],
                                'parent_id': attr['parent_id'],
                                'template_id': attr['template_id'],
                                'sort_order': attr['sort_order'],
                                'is_required': False,
                                'children': []
                            }
                            add_children(child)
                            parent['children'].append(child)
                
                for root in tree:
                    add_children(root)
                return tree
            
            for cat in categories:
                cat_dict = dict_from_row(cat)
                # 获取模板的属性
                template_id = cat_dict.get('template_id')
                if template_id and template_id in attrs_by_template:
                    cat_dict['attributes'] = build_attr_tree(attrs_by_template[template_id])
                else:
                    cat_dict['attributes'] = []
                result.append(cat_dict)
            return result
        finally:
            conn.close()

    @staticmethod
    def get_by_id(category_id):
        """根据ID获取类别"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, t.id as template_id, t.name as template_name
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                WHERE c.id = ?
            ''', (category_id,))
            category = cursor.fetchone()
            return dict_from_row(category)
        finally:
            conn.close()

    @staticmethod
    def find_by_name(name):
        """根据名称查找类别"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM categories WHERE name = ?', (name,))
            category = cursor.fetchone()
            return dict_from_row(category) if category else None
        finally:
            conn.close()

    @staticmethod
    def create(name, sort_order=0):
        """创建类别（同时创建模板）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            # 创建类别
            cursor.execute(
                'INSERT INTO categories (name, sort_order) VALUES (?, ?)',
                (name, sort_order)
            )
            category_id = cursor.lastrowid
            # 自动创建模板
            cursor.execute(
                'INSERT INTO templates (name, category_id) VALUES (?, ?)',
                (name + '模板', category_id)
            )
            conn.commit()
        finally:
            conn.close()
        return category_id

    @staticmethod
    def update(category_id, name, sort_order=None):
        """更新类别。返回实际更新的行数，若类别不存在返回 0。"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            # 先确认类别存在
            cursor.execute('SELECT id FROM categories WHERE id = ?', (category_id,))
            if not cursor.fetchone():
                return 0
            if sort_order is not None:
                cursor.execute(
                    'UPDATE categories SET name = ?, sort_order = ? WHERE id = ?',
                    (name, sort_order, category_id)
                )
            else:
                cursor.execute(
                    'UPDATE categories SET name = ? WHERE id = ?',
                    (name, category_id)
                )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    @staticmethod
    def get_or_create_uncategorized():
        """获取或创建"未分类"类别"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            # 查找未分类（通过JOIN获取template_id）
            cursor.execute('''
                SELECT c.id, t.id as template_id
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                WHERE c.name = '未分类'
            ''')
            row = cursor.fetchone()
            if row:
                return {'id': row['id'], 'template_id': row['template_id']}
            
            # 创建未分类类别
            cursor.execute('INSERT INTO categories (name, sort_order) VALUES (?, ?)', ('未分类', -1))
            category_id = cursor.lastrowid
            # 创建模板
            cursor.execute('INSERT INTO templates (name, category_id) VALUES (?, ?)', ('未分类模板', category_id))
            template_id = cursor.lastrowid
            conn.commit()
            return {'id': category_id, 'template_id': template_id}
        finally:
            conn.close()

    @staticmethod
    def delete(category_id):
        """删除类别（物品转移到未分类，利用级联删除属性）"""
        # 首先获取或创建未分类
        uncategorized = CategoryModel.get_or_create_uncategorized()
        
        conn = get_db()
        try:
            cursor = conn.cursor()
            
            # 将物品转移到未分类
            cursor.execute('UPDATE items SET template_id = ? WHERE template_id IN (SELECT id FROM templates WHERE category_id = ?)', 
                          (uncategorized['template_id'], category_id))
            
            # 删除模板（会级联删除属性）
            cursor.execute('DELETE FROM templates WHERE category_id = ?', (category_id,))
            # 删除类别
            cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
            conn.commit()
        finally:
            conn.close()
        return True


class TemplateModel:
    """模板模型"""

    @staticmethod
    def get_all():
        """获取所有模板"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.name as category_name
                FROM templates t
                INNER JOIN categories c ON t.category_id = c.id
                ORDER BY c.sort_order, c.name
            ''')
            templates = cursor.fetchall()
            return [dict_from_row(t) for t in templates]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(template_id):
        """根据ID获取模板"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.name as category_name
                FROM templates t
                INNER JOIN categories c ON t.category_id = c.id
                WHERE t.id = ?
            ''', (template_id,))
            template = cursor.fetchone()
            return dict_from_row(template)
        finally:
            conn.close()

    @staticmethod
    def get_by_category(category_id):
        """根据类别ID获取模板"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.name as category_name
                FROM templates t
                INNER JOIN categories c ON t.category_id = c.id
                WHERE t.category_id = ?
            ''', (category_id,))
            template = cursor.fetchone()
            return dict_from_row(template)
        finally:
            conn.close()

    @staticmethod
    def get_with_attributes(template_id):
        """获取模板及其属性字段（包含完整的属性树）"""
        template = TemplateModel.get_by_id(template_id)
        if not template:
            return None
        
        # 直接从 attributes 表获取该模板的所有属性
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*
                FROM attributes a
                WHERE a.template_id = ?
                ORDER BY a.sort_order, a.name
            ''', (template_id,))
            all_attrs = cursor.fetchall()
            attr_list = [dict_from_row(a) for a in all_attrs]
            
            # 构建树形结构
            tree = []
            for attr in attr_list:
                if attr['parent_id'] is None:
                    tree.append({
                        'id': attr['id'],
                        'name': attr['name'],
                        'parent_id': None,
                        'template_id': attr['template_id'],
                        'sort_order': attr['sort_order'],
                        'is_required': False,
                        'children': []
                    })
            
            def add_children(parent):
                for attr in attr_list:
                    if attr['parent_id'] == parent['id']:
                        child = {
                            'id': attr['id'],
                            'name': attr['name'],
                            'parent_id': attr['parent_id'],
                            'template_id': attr['template_id'],
                            'sort_order': attr['sort_order'],
                            'is_required': False,
                            'children': []
                        }
                        add_children(child)
                        parent['children'].append(child)
            
            for root in tree:
                add_children(root)
            
            template['attributes'] = tree
        finally:
            conn.close()
        return template

    @staticmethod
    def update_name(template_id, name):
        """更新模板名称"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE templates SET name = ? WHERE id = ?', (name, template_id))
            conn.commit()
        finally:
            conn.close()
        return True


class AttributeModel:
    """属性模型（多级树形结构）"""

    @staticmethod
    def get_all(template_id=None):
        """获取所有属性（可选：按模板过滤）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            if template_id is not None:
                cursor.execute(
                    'SELECT * FROM attributes WHERE template_id = ? ORDER BY sort_order, name',
                    (template_id,)
                )
            else:
                cursor.execute('SELECT * FROM attributes ORDER BY sort_order, name')
            attributes = cursor.fetchall()
            return [dict_from_row(a) for a in attributes]
        finally:
            conn.close()

    @staticmethod
    def get_tree(template_id=None):
        """获取属性树形结构（可选：按模板过滤）"""
        attributes = AttributeModel.get_all(template_id=template_id)
        tree = []
        for attr in attributes:
            if attr['parent_id'] is None:
                tree.append({
                    'id': attr['id'],
                    'name': attr['name'],
                    'parent_id': None,
                    'sort_order': attr['sort_order'],
                    'children': []
                })
        # 递归添加子属性
        def add_children(parent):
            for attr in attributes:
                if attr['parent_id'] == parent['id']:
                    child = {
                        'id': attr['id'],
                        'name': attr['name'],
                        'parent_id': attr['parent_id'],
                        'sort_order': attr['sort_order'],
                        'children': []
                    }
                    add_children(child)
                    parent['children'].append(child)

        for root in tree:
            add_children(root)
        return tree

    @staticmethod
    def get_flat_tree(template_id=None):
        """获取扁平化的属性树（带层级信息）"""
        def flatten(tree, level=0, prefix=''):
            result = []
            for node in tree:
                indent = ' ' * level  # 使用全角空格缩进
                result.append({
                    'id': node['id'],
                    'name': node['name'],
                    'display_name': indent + node['name'],
                    'level': level,
                    'parent_id': node['parent_id']
                })
                if node['children']:
                    result.extend(flatten(node['children'], level + 1, prefix + indent))
            return result
        return flatten(AttributeModel.get_tree(template_id=template_id))

    @staticmethod
    def get_by_id(attribute_id):
        """根据ID获取属性"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM attributes WHERE id = ?', (attribute_id,))
            attr = cursor.fetchone()
            return dict_from_row(attr)
        finally:
            conn.close()

    @staticmethod
    def find_by_name_and_parent(name, parent_id=None, template_id=None):
        """根据名称和父ID查找同级属性（按模板隔离）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            if template_id is not None:
                # 限定在同一模板内做重名校验
                if parent_id is None:
                    cursor.execute(
                        'SELECT * FROM attributes WHERE name = ? AND parent_id IS NULL AND template_id = ?',
                        (name, template_id)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM attributes WHERE name = ? AND parent_id = ? AND template_id = ?',
                        (name, parent_id, template_id)
                    )
            else:
                # 没有 template_id 时，查找所有属性
                if parent_id is None:
                    cursor.execute(
                        'SELECT * FROM attributes WHERE name = ? AND parent_id IS NULL',
                        (name,)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM attributes WHERE name = ? AND parent_id = ?',
                        (name, parent_id)
                    )
            attr = cursor.fetchone()
            return dict_from_row(attr) if attr else None
        finally:
            conn.close()

    @staticmethod
    def create(name, parent_id=None, template_id=None, sort_order=0):
        """创建属性（按 template_id 隔离属性树）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO attributes (name, parent_id, template_id, sort_order) VALUES (?, ?, ?, ?)',
                (name, parent_id, template_id, sort_order)
            )
            attribute_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
        return attribute_id

    @staticmethod
    def update(attribute_id, name, sort_order=None):
        """更新属性"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            if sort_order is not None:
                cursor.execute(
                    'UPDATE attributes SET name = ?, sort_order = ? WHERE id = ?',
                    (name, sort_order, attribute_id)
                )
            else:
                cursor.execute(
                    'UPDATE attributes SET name = ? WHERE id = ?',
                    (name, attribute_id)
                )
            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def delete(attribute_id):
        """删除属性（级联删除所有子属性）"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            
            # 递归查找所有子属性ID
            def find_all_children(parent_id):
                cursor.execute('SELECT id FROM attributes WHERE parent_id = ?', (parent_id,))
                children = cursor.fetchall()
                child_ids = [row['id'] for row in children]
                all_ids = list(child_ids)
                for child_id in child_ids:
                    all_ids.extend(find_all_children(child_id))
                return all_ids
            
            # 获取所有要删除的属性ID（包括自身和所有子属性）
            ids_to_delete = [attribute_id] + find_all_children(attribute_id)
            
            # 删除物品中的关联
            for attr_id in ids_to_delete:
                cursor.execute('DELETE FROM item_attributes WHERE attribute_id = ?', (attr_id,))
            
            # 删除属性（包括所有子属性）
            for attr_id in ids_to_delete:
                cursor.execute('DELETE FROM attributes WHERE id = ?', (attr_id,))
            
            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def get_children(attribute_id):
        """获取属性的子属性"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM attributes WHERE parent_id = ? ORDER BY sort_order, name', (attribute_id,))
            children = cursor.fetchall()
            return [dict_from_row(c) for c in children]
        finally:
            conn.close()

    @staticmethod
    def get_referenced_count(attribute_id):
        """获取属性被物品引用的数量"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            # 获取该属性及其所有子属性的ID列表
            attr_ids = [attribute_id]
            attr_ids.extend(AttributeModel._get_all_child_ids(attribute_id))
            placeholders = ','.join('?' * len(attr_ids))
            
            cursor.execute(f'''
                SELECT COUNT(DISTINCT item_id) as count 
                FROM item_attributes 
                WHERE attribute_id IN ({placeholders})
            ''', attr_ids)
            result = cursor.fetchone()
            return result['count'] if result else 0
        finally:
            conn.close()

    @staticmethod
    def _get_all_child_ids(attribute_id):
        """递归获取属性所有子属性ID"""
        children = AttributeModel.get_children(attribute_id)
        result = []
        for child in children:
            result.append(child['id'])
            result.extend(AttributeModel._get_all_child_ids(child['id']))
        return result


class ItemModel:
    """物品模型"""

    @staticmethod
    def get_all(template_id=None, template_ids=None, keyword=None, attribute_ids=None, page=None, per_page=None):
        """获取所有物品（支持筛选和分页）"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            query = '''
                SELECT DISTINCT i.*, t.name as template_name, c.name as category_name, c.id as category_id
                FROM items i
                LEFT JOIN templates t ON i.template_id = t.id
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN item_attributes ia ON ia.item_id = i.id
                LEFT JOIN attributes attr ON ia.attribute_id = attr.id
            '''
            conditions = []
            params = []

            if template_ids and template_ids:
                placeholders = ','.join('?' * len(template_ids))
                conditions.append(f'(i.template_id IN ({placeholders}) OR i.template_id IS NULL)')
                params.extend(template_ids)
            elif template_id:
                conditions.append('i.template_id = ?')
                params.append(template_id)

            if keyword:
                conditions.append('(i.name LIKE ? OR i.remark LIKE ? OR c.name LIKE ? OR attr.name LIKE ?)')
                params.append(f'%{keyword}%')
                params.append(f'%{keyword}%')
                params.append(f'%{keyword}%')
                params.append(f'%{keyword}%')

            if attribute_ids:
                placeholders = ','.join('?' * len(attribute_ids))
                conditions.append(f'ia.attribute_id IN ({placeholders})')
                params.extend(attribute_ids)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY i.created_at DESC'

            # 分页处理
            if page and per_page:
                offset = (page - 1) * per_page
                query += ' LIMIT ? OFFSET ?'
                params.extend([per_page, offset])

            cursor.execute(query, params)
            items = cursor.fetchall()

            result = []
            for item in items:
                item_dict = dict_from_row(item)
                item_dict['attributes'] = ItemModel.get_item_attributes(item_dict['id'])
                result.append(item_dict)

            return result
        finally:
            conn.close()

    @staticmethod
    def count(template_id=None, template_ids=None, keyword=None, attribute_ids=None):
        """获取物品总数（支持筛选条件）"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            query = '''
                SELECT COUNT(DISTINCT i.id) as count
                FROM items i
                INNER JOIN templates t ON i.template_id = t.id
                INNER JOIN categories c ON t.category_id = c.id
            '''
            conditions = []
            params = []

            if template_ids and template_ids:
                placeholders = ','.join('?' * len(template_ids))
                conditions.append(f'i.template_id IN ({placeholders})')
                params.extend(template_ids)
            elif template_id:
                conditions.append('i.template_id = ?')
                params.append(template_id)

            if keyword:
                conditions.append('(i.name LIKE ? OR i.remark LIKE ?)')
                params.append(f'%{keyword}%')
                params.append(f'%{keyword}%')

            if attribute_ids:
                placeholders = ','.join('?' * len(attribute_ids))
                query += f' INNER JOIN item_attributes ia ON ia.item_id = i.id'
                conditions.append(f'ia.attribute_id IN ({placeholders})')
                params.extend(attribute_ids)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            cursor.execute(query, params)
            return cursor.fetchone()['count']
        finally:
            conn.close()

    @staticmethod
    def get_by_id(item_id):
        """根据ID获取物品"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, t.name as template_name, c.name as category_name, c.id as category_id
                FROM items i
                INNER JOIN templates t ON i.template_id = t.id
                INNER JOIN categories c ON t.category_id = c.id
                WHERE i.id = ?
            ''', (item_id,))
            item = cursor.fetchone()

            if item:
                item_dict = dict_from_row(item)
                item_dict['attributes'] = ItemModel.get_item_attributes(item_dict['id'])
                return item_dict
            return None
        finally:
            conn.close()

    @staticmethod
    def get_item_attributes(item_id):
        """获取物品的属性值"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ia.attribute_id as id, a.name, a.parent_id
                FROM item_attributes ia
                INNER JOIN attributes a ON ia.attribute_id = a.id
                WHERE ia.item_id = ?
            ''', (item_id,))
            attrs = cursor.fetchall()
            return [dict_from_row(a) for a in attrs]
        finally:
            conn.close()

    @staticmethod
    def create(name, template_id, remark=None, images=None, attribute_ids=None):
        """创建物品"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO items (name, template_id, remark, images) VALUES (?, ?, ?, ?)',
                (name, template_id, remark, images)
            )
            item_id = cursor.lastrowid

            # 添加属性值
            if attribute_ids:
                for attr_id in attribute_ids:
                    cursor.execute(
                        'INSERT INTO item_attributes (item_id, attribute_id) VALUES (?, ?)',
                        (item_id, attr_id)
                    )

            conn.commit()
        finally:
            conn.close()
        return item_id

    @staticmethod
    def update(item_id, name=None, remark=None, images=None, attribute_ids=None):
        """更新物品"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            updates = []
            params = []

            if name is not None:
                updates.append('name = ?')
                params.append(name)
            if remark is not None:
                updates.append('remark = ?')
                params.append(remark)
            if images is not None:
                updates.append('images = ?')
                params.append(images)

            updates.append('updated_at = CURRENT_TIMESTAMP')

            if updates:
                params.append(item_id)
                cursor.execute(
                    f'UPDATE items SET {", ".join(updates)} WHERE id = ?',
                    params
                )

            # 更新属性值
            if attribute_ids is not None:
                cursor.execute('DELETE FROM item_attributes WHERE item_id = ?', (item_id,))
                for attr_id in attribute_ids:
                    cursor.execute(
                        'INSERT INTO item_attributes (item_id, attribute_id) VALUES (?, ?)',
                        (item_id, attr_id)
                    )

            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def delete(item_id):
        """删除物品"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM item_attributes WHERE item_id = ?', (item_id,))
            cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def batch_delete(item_ids):
        """批量删除物品"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(item_ids))
            cursor.execute(f'DELETE FROM item_attributes WHERE item_id IN ({placeholders})', item_ids)
            cursor.execute(f'DELETE FROM items WHERE id IN ({placeholders})', item_ids)
            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def batch_add_attributes(item_ids, attribute_ids):
        """为多个物品批量添加属性"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            for item_id in item_ids:
                for attr_id in attribute_ids:
                    cursor.execute('SELECT id FROM item_attributes WHERE item_id = ? AND attribute_id = ?', (item_id, attr_id))
                    if not cursor.fetchone():
                        cursor.execute('INSERT INTO item_attributes (item_id, attribute_id) VALUES (?, ?)', (item_id, attr_id))
            conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def batch_remove_attributes(item_ids, attribute_ids):
        """为多个物品批量移除属性"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            for item_id in item_ids:
                for attr_id in attribute_ids:
                    cursor.execute('DELETE FROM item_attributes WHERE item_id = ? AND attribute_id = ?', (item_id, attr_id))
            conn.commit()
        finally:
            conn.close()
        return True


class StatsModel:
    """统计模型"""

    @staticmethod
    def get_overall():
        """获取总体统计"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            # 物品总数
            cursor.execute('SELECT COUNT(*) as count FROM items')
            total_items = cursor.fetchone()['count']

            # 类别统计
            cursor.execute('''
                SELECT c.name, COUNT(i.id) as count
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                LEFT JOIN items i ON t.id = i.template_id
                GROUP BY c.id
                ORDER BY count DESC
            ''')
            category_stats = [dict_from_row(c) for c in cursor.fetchall()]

            # 类别数量
            cursor.execute('SELECT COUNT(*) as count FROM categories')
            total_categories = cursor.fetchone()['count']

            # 属性数量
            cursor.execute('SELECT COUNT(*) as count FROM attributes')
            total_attributes = cursor.fetchone()['count']

            return {
                'total_items': total_items,
                'total_categories': total_categories,
                'total_attributes': total_attributes,
                'category_stats': category_stats
            }
        finally:
            conn.close()
