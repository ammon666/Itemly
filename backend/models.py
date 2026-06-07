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


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()

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

    # 创建类别表（支持多层级）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    ''')

    # 创建标签表（支持多层级）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')

    # 创建模板表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    ''')

    # 创建模板字段表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_type TEXT DEFAULT 'text',
            field_options TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
        )
    ''')

    # 创建物品表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            remark TEXT,
            images TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    ''')

    # 创建物品标签关联表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS item_tags (
            item_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (item_id, tag_id),
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')

    # 创建物品自定义字段值表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS item_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            field_id INTEGER NOT NULL,
            field_value TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (field_id) REFERENCES template_fields(id) ON DELETE CASCADE
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

    # 创建默认类别（如果不存在）
    cursor.execute('SELECT id FROM categories LIMIT 1')
    if not cursor.fetchone():
        cursor.execute('INSERT INTO categories (name, sort_order) VALUES (?, ?)', ('默认分类', 0))

    conn.commit()
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
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        return dict_from_row(user)

    @staticmethod
    def find_by_id(user_id):
        """根据ID查找用户"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict_from_row(user)

    @staticmethod
    def verify_password(username, password):
        """验证密码"""
        user = UserModel.find_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None

    @staticmethod
    def update_password(user_id, new_password):
        """更新密码"""
        conn = get_db()
        cursor = conn.cursor()
        password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def update_profile(user_id, display_name):
        """更新用户信息"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET display_name = ? WHERE id = ?', (display_name, user_id))
        conn.commit()
        conn.close()
        return True


class CategoryModel:
    """类别模型"""

    @staticmethod
    def get_all():
        """获取所有类别"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories ORDER BY sort_order, name')
        categories = cursor.fetchall()
        conn.close()
        return [dict_from_row(c) for c in categories]

    @staticmethod
    def get_tree():
        """获取类别树形结构"""
        categories = CategoryModel.get_all()
        tree = []
        for cat in categories:
            if cat['parent_id'] is None:
                tree.append({
                    'id': cat['id'],
                    'name': cat['name'],
                    'parent_id': None,
                    'sort_order': cat['sort_order'],
                    'children': []
                })
        # 递归添加子类别
        def add_children(parent):
            for cat in categories:
                if cat['parent_id'] == parent['id']:
                    child = {
                        'id': cat['id'],
                        'name': cat['name'],
                        'parent_id': cat['parent_id'],
                        'sort_order': cat['sort_order'],
                        'children': []
                    }
                    add_children(child)
                    parent['children'].append(child)

        for root in tree:
            add_children(root)
        return tree

    @staticmethod
    def create(name, parent_id=None, sort_order=0):
        """创建类别"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO categories (name, parent_id, sort_order) VALUES (?, ?, ?)',
            (name, parent_id, sort_order)
        )
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return category_id

    @staticmethod
    def update(category_id, name, sort_order=None):
        """更新类别"""
        conn = get_db()
        cursor = conn.cursor()
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
        conn.close()
        return True

    @staticmethod
    def delete(category_id):
        """删除类别"""
        conn = get_db()
        cursor = conn.cursor()
        # 将该类别的物品设置为NULL
        cursor.execute('UPDATE items SET category_id = NULL WHERE category_id = ?', (category_id,))
        # 删除类别
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        conn.close()
        return True


class TagModel:
    """标签模型"""

    @staticmethod
    def get_all():
        """获取所有标签"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tags ORDER BY sort_order, name')
        tags = cursor.fetchall()
        conn.close()
        return [dict_from_row(t) for t in tags]

    @staticmethod
    def get_tree():
        """获取标签树形结构"""
        tags = TagModel.get_all()
        tree = []
        for tag in tags:
            if tag['parent_id'] is None:
                tree.append({
                    'id': tag['id'],
                    'name': tag['name'],
                    'parent_id': None,
                    'sort_order': tag['sort_order'],
                    'children': []
                })
        # 递归添加子标签
        def add_children(parent):
            for tag in tags:
                if tag['parent_id'] == parent['id']:
                    child = {
                        'id': tag['id'],
                        'name': tag['name'],
                        'parent_id': tag['parent_id'],
                        'sort_order': tag['sort_order'],
                        'children': []
                    }
                    add_children(child)
                    parent['children'].append(child)

        for root in tree:
            add_children(root)
        return tree

    @staticmethod
    def create(name, parent_id=None, sort_order=0):
        """创建标签"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO tags (name, parent_id, sort_order) VALUES (?, ?, ?)',
            (name, parent_id, sort_order)
        )
        tag_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tag_id

    @staticmethod
    def update(tag_id, name, sort_order=None):
        """更新标签"""
        conn = get_db()
        cursor = conn.cursor()
        if sort_order is not None:
            cursor.execute(
                'UPDATE tags SET name = ?, sort_order = ? WHERE id = ?',
                (name, sort_order, tag_id)
            )
        else:
            cursor.execute(
                'UPDATE tags SET name = ? WHERE id = ?',
                (name, tag_id)
            )
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete(tag_id):
        """删除标签"""
        conn = get_db()
        cursor = conn.cursor()
        # 删除标签关联
        cursor.execute('DELETE FROM item_tags WHERE tag_id = ?', (tag_id,))
        # 删除标签
        cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
        conn.commit()
        conn.close()
        return True


class TemplateModel:
    """模板模型"""

    @staticmethod
    def get_all():
        """获取所有模板"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, c.name as category_name
            FROM templates t
            LEFT JOIN categories c ON t.category_id = c.id
            ORDER BY t.name
        ''')
        templates = cursor.fetchall()
        conn.close()
        return [dict_from_row(t) for t in templates]

    @staticmethod
    def get_by_id(template_id):
        """根据ID获取模板"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, c.name as category_name
            FROM templates t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.id = ?
        ''', (template_id,))
        template = cursor.fetchone()
        conn.close()
        return dict_from_row(template)

    @staticmethod
    def get_with_fields(template_id):
        """获取模板及其字段"""
        template = TemplateModel.get_by_id(template_id)
        if not template:
            return None
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM template_fields
            WHERE template_id = ?
            ORDER BY sort_order
        ''', (template_id,))
        fields = cursor.fetchall()
        conn.close()
        template['fields'] = [dict_from_row(f) for f in fields]
        return template

    @staticmethod
    def create(name, category_id=None):
        """创建模板"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO templates (name, category_id) VALUES (?, ?)',
            (name, category_id)
        )
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template_id

    @staticmethod
    def update(template_id, name, category_id=None):
        """更新模板"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE templates SET name = ?, category_id = ? WHERE id = ?',
            (name, category_id, template_id)
        )
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete(template_id):
        """删除模板"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM template_fields WHERE template_id = ?', (template_id,))
        cursor.execute('DELETE FROM templates WHERE id = ?', (template_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def add_field(template_id, field_name, field_type='text', field_options=None, sort_order=0):
        """添加模板字段"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO template_fields (template_id, field_name, field_type, field_options, sort_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (template_id, field_name, field_type, field_options, sort_order))
        field_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return field_id

    @staticmethod
    def update_field(field_id, field_name, field_type=None, field_options=None, sort_order=None):
        """更新模板字段"""
        conn = get_db()
        cursor = conn.cursor()
        if field_type is not None:
            cursor.execute('''
                UPDATE template_fields
                SET field_name = ?, field_type = ?, field_options = ?, sort_order = ?
                WHERE id = ?
            ''', (field_name, field_type, field_options, sort_order, field_id))
        else:
            cursor.execute('''
                UPDATE template_fields SET field_name = ? WHERE id = ?
            ''', (field_name, field_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete_field(field_id):
        """删除模板字段"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM item_fields WHERE field_id = ?', (field_id,))
        cursor.execute('DELETE FROM template_fields WHERE id = ?', (field_id,))
        conn.commit()
        conn.close()
        return True


class ItemModel:
    """物品模型"""

    @staticmethod
    def get_all(category_id=None, tag_id=None, keyword=None):
        """获取所有物品（支持筛选）"""
        conn = get_db()
        cursor = conn.cursor()

        query = '''
            SELECT DISTINCT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
        '''
        conditions = []
        params = []

        if tag_id:
            query += ' INNER JOIN item_tags it ON i.id = it.item_id'
            conditions.append('it.tag_id = ?')
            params.append(tag_id)

        if category_id:
            conditions.append('i.category_id = ?')
            params.append(category_id)

        if keyword:
            conditions.append('(i.name LIKE ? OR i.remark LIKE ?)')
            params.append(f'%{keyword}%')
            params.append(f'%{keyword}%')

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY i.created_at DESC'

        cursor.execute(query, params)
        items = cursor.fetchall()
        conn.close()

        result = []
        for item in items:
            item_dict = dict_from_row(item)
            # 获取标签
            item_dict['tags'] = ItemModel.get_item_tags(item_dict['id'])
            result.append(item_dict)

        return result

    @staticmethod
    def get_by_id(item_id):
        """根据ID获取物品"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.id = ?
        ''', (item_id,))
        item = cursor.fetchone()
        conn.close()

        if item:
            item_dict = dict_from_row(item)
            item_dict['tags'] = ItemModel.get_item_tags(item_dict['id'])
            item_dict['fields'] = ItemModel.get_item_fields(item_dict['id'])
            return item_dict
        return None

    @staticmethod
    def get_item_tags(item_id):
        """获取物品的标签"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.* FROM tags t
            INNER JOIN item_tags it ON t.id = it.tag_id
            WHERE it.item_id = ?
        ''', (item_id,))
        tags = cursor.fetchall()
        conn.close()
        return [dict_from_row(t) for t in tags]

    @staticmethod
    def get_item_fields(item_id):
        """获取物品的自定义字段值"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tf.id, tf.field_name, tf.field_type, tf.field_options, if.field_value
            FROM template_fields tf
            LEFT JOIN item_fields if ON tf.id = if.field_id AND if.item_id = ?
            WHERE tf.template_id IN (
                SELECT template_id FROM template_fields WHERE id IN (
                    SELECT field_id FROM item_fields WHERE item_id = ?
                )
            )
        ''', (item_id, item_id))
        fields = cursor.fetchall()
        conn.close()
        return [dict_from_row(f) for f in fields]

    @staticmethod
    def create(name, category_id=None, remark=None, images=None, tag_ids=None, field_values=None):
        """创建物品"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO items (name, category_id, remark, images) VALUES (?, ?, ?, ?)',
            (name, category_id, remark, images)
        )
        item_id = cursor.lastrowid

        # 添加标签关联
        if tag_ids:
            for tag_id in tag_ids:
                cursor.execute(
                    'INSERT INTO item_tags (item_id, tag_id) VALUES (?, ?)',
                    (item_id, tag_id)
                )

        # 添加自定义字段值
        if field_values:
            for field_id, field_value in field_values.items():
                cursor.execute(
                    'INSERT INTO item_fields (item_id, field_id, field_value) VALUES (?, ?, ?)',
                    (item_id, field_id, field_value)
                )

        conn.commit()
        conn.close()
        return item_id

    @staticmethod
    def update(item_id, name=None, category_id=None, remark=None, images=None, tag_ids=None, field_values=None):
        """更新物品"""
        conn = get_db()
        cursor = conn.cursor()

        updates = []
        params = []

        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if category_id is not None:
            updates.append('category_id = ?')
            params.append(category_id)
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

        # 更新标签关联
        if tag_ids is not None:
            cursor.execute('DELETE FROM item_tags WHERE item_id = ?', (item_id,))
            for tag_id in tag_ids:
                cursor.execute(
                    'INSERT INTO item_tags (item_id, tag_id) VALUES (?, ?)',
                    (item_id, tag_id)
                )

        # 更新自定义字段值
        if field_values:
            for field_id, field_value in field_values.items():
                cursor.execute(
                    'SELECT id FROM item_fields WHERE item_id = ? AND field_id = ?',
                    (item_id, field_id)
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        'UPDATE item_fields SET field_value = ? WHERE id = ?',
                        (field_value, existing['id'])
                    )
                else:
                    cursor.execute(
                        'INSERT INTO item_fields (item_id, field_id, field_value) VALUES (?, ?, ?)',
                        (item_id, field_id, field_value)
                    )

        conn.commit()
        conn.close()
        return True

    @staticmethod
    def delete(item_id):
        """删除物品"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM item_tags WHERE item_id = ?', (item_id,))
        cursor.execute('DELETE FROM item_fields WHERE item_id = ?', (item_id,))
        cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def batch_delete(item_ids):
        """批量删除物品"""
        conn = get_db()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(item_ids))
        cursor.execute(f'DELETE FROM item_tags WHERE item_id IN ({placeholders})', item_ids)
        cursor.execute(f'DELETE FROM item_fields WHERE item_id IN ({placeholders})', item_ids)
        cursor.execute(f'DELETE FROM items WHERE id IN ({placeholders})', item_ids)
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def batch_update(category_id, item_ids):
        """批量更新物品类别"""
        conn = get_db()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(item_ids))
        cursor.execute(
            f'UPDATE items SET category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})',
            [category_id] + item_ids
        )
        conn.commit()
        conn.close()
        return True


class StatsModel:
    """统计模型"""

    @staticmethod
    def get_overall():
        """获取总体统计"""
        conn = get_db()
        cursor = conn.cursor()

        # 物品总数
        cursor.execute('SELECT COUNT(*) as count FROM items')
        total_items = cursor.fetchone()['count']

        # 类别统计
        cursor.execute('''
            SELECT c.name, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN items i ON c.id = i.category_id
            GROUP BY c.id
            HAVING count > 0 OR 1=1
            ORDER BY count DESC
        ''')
        category_stats = [dict_from_row(c) for c in cursor.fetchall()]

        # 标签统计
        cursor.execute('''
            SELECT t.name, COUNT(it.item_id) as count
            FROM tags t
            LEFT JOIN item_tags it ON t.id = it.tag_id
            GROUP BY t.id
            HAVING count > 0 OR 1=1
            ORDER BY count DESC
        ''')
        tag_stats = [dict_from_row(t) for t in cursor.fetchall()]

        # 类别数量
        cursor.execute('SELECT COUNT(*) as count FROM categories')
        total_categories = cursor.fetchone()['count']

        # 标签数量
        cursor.execute('SELECT COUNT(*) as count FROM tags')
        total_tags = cursor.fetchone()['count']

        conn.close()

        return {
            'total_items': total_items,
            'total_categories': total_categories,
            'total_tags': total_tags,
            'category_stats': category_stats,
            'tag_stats': tag_stats
        }
