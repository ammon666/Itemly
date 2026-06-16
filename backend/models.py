"""
Itemly 数据库模型。
关键改进：
- 连接管理：请求上下文中优先复用 g.db，避免频繁打开/关闭。
- 所有写操作使用事务保护，避免中间失败导致数据不一致。
- 属性树递归使用 SQLite WITH RECURSIVE CTE，替代 Python 层递归。
- item_attributes 增加 UNIQUE(item_id, attribute_id) 约束，并使用 INSERT OR IGNORE 批量写入。
- 用户输入 keyword 的 SQL LIKE 通配符统一转义，避免被用作通配符注入。
"""
import sqlite3
import os
import logging
from datetime import datetime
from flask import g, has_app_context
from werkzeug.security import generate_password_hash, check_password_hash

from utils.validators import escape_like

DATABASE_PATH = os.environ.get(
    'ITEMLY_DB_PATH',
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'itemly.db')
)

logger = logging.getLogger('itemly.models')


# ============================================================
# 连接管理
# ============================================================

def get_db():
    """获取数据库连接。

    在 Flask 请求上下文中优先使用 g.db（每个请求一个连接，teardown_request 时关闭）；
    非请求上下文（如 init_db、脚本调用）下创建独立连接。
    """
    if has_app_context():
        conn = getattr(g, 'db', None)
        if conn is not None:
            return conn
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def _in_request_context():
    """判断当前是否在请求上下文中。"""
    return has_app_context() and getattr(g, 'db', None) is not None


def get_db_columns(table_name):
    """获取表的所有列名。仅内部使用，表名做白名单校验防止注入。"""
    ALLOWED = {
        'users', 'categories', 'templates', 'attributes', 'items', 'item_attributes'
    }
    if table_name not in ALLOWED:
        raise ValueError('非法表名: %s' % table_name)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info("%s")' % table_name)
        return [row[1] for row in cursor.fetchall()]
    finally:
        if not _in_request_context():
            conn.close()


# ============================================================
# 初始化
# ============================================================

def _migrate_item_attributes_unique(cursor):
    """迁移 item_attributes 表以确保 UNIQUE(item_id, attribute_id) 约束存在。

    SQLite 不能直接 ALTER TABLE ADD UNIQUE，所以需要重建表。
    """
    # 检查当前是否已有唯一约束（sqlite_master 中的 CREATE TABLE 语句）
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='item_attributes'")
    row = cursor.fetchone()
    if row and row[0] and 'UNIQUE(item_id, attribute_id)' in row[0].upper().replace(' ', ''):
        return  # 已有约束，无需迁移
    # 去重并重建
    cursor.execute('SELECT DISTINCT item_id, attribute_id FROM item_attributes')
    rows = cursor.fetchall()
    cursor.execute('DROP TABLE IF EXISTS item_attributes')
    cursor.execute('''
        CREATE TABLE item_attributes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            attribute_id INTEGER NOT NULL,
            UNIQUE(item_id, attribute_id),
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
        )
    ''')
    cursor.executemany(
        'INSERT INTO item_attributes (item_id, attribute_id) VALUES (?, ?)',
        [(r[0], r[1]) for r in rows]
    )


def init_db(force_recreate=False):
    """初始化数据库。与原函数完全兼容。"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        cursor = conn.cursor()

        if force_recreate:
            cursor.execute('DROP TABLE IF EXISTS item_attributes')
            cursor.execute('DROP TABLE IF EXISTS items')
            cursor.execute('DROP TABLE IF EXISTS attributes')
            cursor.execute('DROP TABLE IF EXISTS templates')
            cursor.execute('DROP TABLE IF EXISTS categories')
            cursor.execute('DROP TABLE IF EXISTS users')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')

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

        # 迁移：确保 item_attributes 有 UNIQUE(item_id, attribute_id) 约束
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_attributes'")
        if cursor.fetchone():
            _migrate_item_attributes_unique(cursor)
        else:
            cursor.execute('''
                CREATE TABLE item_attributes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    attribute_id INTEGER NOT NULL,
                    UNIQUE(item_id, attribute_id),
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
                    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
                )
            ''')

        # 默认管理员
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            temp_pwd = 'admin123'
            password_hash = generate_password_hash(temp_pwd)
            cursor.execute(
                'INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)',
                ('admin', password_hash, '管理员')
            )

        conn.commit()
    finally:
        conn.close()


# ============================================================
# 通用工具
# ============================================================

def dict_from_row(row):
    """将 sqlite Row 转换为字典。"""
    if row is None:
        return None
    return dict(row)


def _close_if_standalone(conn):
    """若当前连接是在非请求上下文中创建的，则关闭它。"""
    if not _in_request_context():
        conn.close()


# ============================================================
# 用户模型
# ============================================================

class UserModel:
    """用户模型。"""

    @staticmethod
    def find_by_username(username):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def find_by_id(user_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def verify_password(username, password):
        user = UserModel.find_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None

    @staticmethod
    def update_password(user_id, new_password):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            password_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return True

    @staticmethod
    def update_username(user_id, username):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return True


# ============================================================
# 类别模型
# ============================================================

class CategoryModel:
    """类别模型。每个类别有且仅有一个模板。"""

    @staticmethod
    def get_all():
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, t.id as template_id, t.name as template_name
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                ORDER BY c.sort_order, c.name
            ''')
            categories = [dict_from_row(r) for r in cursor.fetchall()]

            # 预先读取所有属性，按 template_id 分组
            cursor.execute('SELECT * FROM attributes ORDER BY sort_order, name')
            all_attrs = [dict_from_row(a) for a in cursor.fetchall()]
            attrs_by_template = {}
            for attr in all_attrs:
                attrs_by_template.setdefault(attr['template_id'], []).append(attr)

            # 属性树构建（按模板缓存）
            tree_cache = {}

            def build_attr_tree(attrs):
                children_map = {}
                root_nodes = []
                for a in attrs:
                    children_map.setdefault(a.get('parent_id'), []).append(a)

                def make(node):
                    return {
                        'id': node['id'],
                        'name': node['name'],
                        'parent_id': node.get('parent_id'),
                        'template_id': node['template_id'],
                        'sort_order': node.get('sort_order'),
                        'is_required': False,
                        'children': [make(c) for c in children_map.get(node['id'], [])]
                    }

                for root in children_map.get(None, []):
                    root_nodes.append(make(root))
                return root_nodes

            for cat in categories:
                tid = cat.get('template_id')
                if tid and tid in attrs_by_template:
                    if tid not in tree_cache:
                        tree_cache[tid] = build_attr_tree(attrs_by_template[tid])
                    cat['attributes'] = tree_cache[tid]
                else:
                    cat['attributes'] = []
            return categories
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_by_id(category_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, t.id as template_id, t.name as template_name
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                WHERE c.id = ?
            ''', (category_id,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def find_by_name(name):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM categories WHERE name = ?', (name,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def create(name, sort_order=0):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            cursor.execute(
                'INSERT INTO categories (name, sort_order) VALUES (?, ?)',
                (name, sort_order)
            )
            category_id = cursor.lastrowid
            cursor.execute(
                'INSERT INTO templates (name, category_id) VALUES (?, ?)',
                (name + '模板', category_id)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return category_id

    @staticmethod
    def update(category_id, name, sort_order=None):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM categories WHERE id = ?', (category_id,))
            if not cursor.fetchone():
                return 0
            cursor.execute('BEGIN')
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
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_or_create_uncategorized():
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.id, t.id as template_id
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                WHERE c.name = ?
            ''', ('未分类',))
            row = cursor.fetchone()
            if row:
                return {'id': row['id'], 'template_id': row['template_id']}
            cursor.execute('BEGIN')
            cursor.execute(
                'INSERT INTO categories (name, sort_order) VALUES (?, ?)',
                ('未分类', -1)
            )
            category_id = cursor.lastrowid
            cursor.execute(
                'INSERT INTO templates (name, category_id) VALUES (?, ?)',
                ('未分类模板', category_id)
            )
            conn.commit()
            return {'id': category_id, 'template_id': cursor.lastrowid}
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def delete(category_id):
        """删除类别（物品转移到未分类；整个流程在同一事务中完成）。"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')

            # 确保"未分类"类别存在
            cursor.execute('SELECT id FROM categories WHERE name = ?', ('未分类',))
            uc_row = cursor.fetchone()
            if uc_row:
                uncategorized_id = uc_row['id']
            else:
                cursor.execute(
                    'INSERT INTO categories (name, sort_order) VALUES (?, ?)',
                    ('未分类', -1)
                )
                uncategorized_id = cursor.lastrowid
                cursor.execute(
                    'INSERT INTO templates (name, category_id) VALUES (?, ?)',
                    ('未分类模板', uncategorized_id)
                )

            # 取出目标类别的 template_id
            cursor.execute('SELECT id FROM templates WHERE category_id = ?', (category_id,))
            old_template_rows = cursor.fetchall()
            old_template_ids = [r['id'] for r in old_template_rows]

            # 转移物品到未分类模板
            if old_template_ids:
                # 查询未分类的 template_id
                cursor.execute('SELECT id FROM templates WHERE category_id = ?', (uncategorized_id,))
                uncategorized_template = cursor.fetchone()
                uncategorized_template_id = uncategorized_template['id'] if uncategorized_template else None
                if uncategorized_template_id:
                    placeholders = ','.join('?' * len(old_template_ids))
                    cursor.execute(
                        'UPDATE items SET template_id = ? WHERE template_id IN (%s)' % placeholders,
                        [uncategorized_template_id] + old_template_ids
                    )

            # 删除模板（级联删除属性）与类别
            cursor.execute('DELETE FROM templates WHERE category_id = ?', (category_id,))
            cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)


# ============================================================
# 模板模型
# ============================================================

class TemplateModel:
    """模板模型。"""

    @staticmethod
    def get_all():
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.name as category_name
                FROM templates t
                INNER JOIN categories c ON t.category_id = c.id
                ORDER BY c.sort_order, c.name
            ''')
            return [dict_from_row(r) for r in cursor.fetchall()]
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_by_id(template_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.name as category_name
                FROM templates t
                INNER JOIN categories c ON t.category_id = c.id
                WHERE t.id = ?
            ''', (template_id,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_by_category(category_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.name as category_name
                FROM templates t
                INNER JOIN categories c ON t.category_id = c.id
                WHERE t.category_id = ?
            ''', (category_id,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_with_attributes(template_id):
        template = TemplateModel.get_by_id(template_id)
        if not template:
            return None
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*
                FROM attributes a
                WHERE a.template_id = ?
                ORDER BY a.sort_order, a.name
            ''', (template_id,))
            all_attrs = [dict_from_row(a) for a in cursor.fetchall()]

            children_map = {}
            for a in all_attrs:
                children_map.setdefault(a.get('parent_id'), []).append(a)

            def make(node):
                return {
                    'id': node['id'],
                    'name': node['name'],
                    'parent_id': node.get('parent_id'),
                    'template_id': node['template_id'],
                    'sort_order': node.get('sort_order'),
                    'is_required': False,
                    'children': [make(c) for c in children_map.get(node['id'], [])]
                }

            template['attributes'] = [make(r) for r in children_map.get(None, [])]
        finally:
            _close_if_standalone(conn)
        return template

    @staticmethod
    def update_name(template_id, name):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            cursor.execute('UPDATE templates SET name = ? WHERE id = ?', (name, template_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return True


# ============================================================
# 属性模型
# ============================================================

class AttributeModel:
    """属性模型（多级树形结构）。"""

    @staticmethod
    def get_all(template_id=None):
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
            return [dict_from_row(r) for r in cursor.fetchall()]
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_tree(template_id=None):
        attributes = AttributeModel.get_all(template_id=template_id)
        tree = []
        children_map = {}
        for a in attributes:
            children_map.setdefault(a.get('parent_id'), []).append(a)

        def make(node):
            return {
                'id': node['id'],
                'name': node['name'],
                'parent_id': node.get('parent_id'),
                'sort_order': node.get('sort_order'),
                'children': [make(c) for c in children_map.get(node['id'], [])]
            }

        for root in children_map.get(None, []):
            tree.append(make(root))
        return tree

    @staticmethod
    def get_flat_tree(template_id=None):
        def flatten(tree, level=0):
            result = []
            for node in tree:
                result.append({
                    'id': node['id'],
                    'name': node['name'],
                    'display_name': '  ' * level + node['name'],
                    'level': level,
                    'parent_id': node['parent_id']
                })
                if node['children']:
                    result.extend(flatten(node['children'], level + 1))
            return result
        return flatten(AttributeModel.get_tree(template_id=template_id))

    @staticmethod
    def get_by_id(attribute_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM attributes WHERE id = ?', (attribute_id,))
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def find_by_name_and_parent(name, parent_id=None, template_id=None):
        conn = get_db()
        try:
            cursor = conn.cursor()
            if template_id is not None:
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
            return dict_from_row(cursor.fetchone())
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def create(name, parent_id=None, template_id=None, sort_order=0):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            cursor.execute(
                'INSERT INTO attributes (name, parent_id, template_id, sort_order) VALUES (?, ?, ?, ?)',
                (name, parent_id, template_id, sort_order)
            )
            attribute_id = cursor.lastrowid
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return attribute_id

    @staticmethod
    def update(attribute_id, name, sort_order=None):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
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
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return True

    @staticmethod
    def delete(attribute_id):
        """删除属性：级联删除所有子孙属性和关联的物品引用。

        使用 SQLite WITH RECURSIVE CTE，一次性完成，性能与一致性都更优。
        """
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')

            # 1) 删除所有关联 item_attributes（包括子孙属性被引用的）
            cursor.execute('''
                WITH RECURSIVE cte(id) AS (
                    SELECT ?
                    UNION ALL
                    SELECT a.id FROM attributes a
                    INNER JOIN cte ON a.parent_id = cte.id
                )
                DELETE FROM item_attributes WHERE attribute_id IN (SELECT id FROM cte)
            ''', (attribute_id,))

            # 2) 删除属性本身及所有子孙
            cursor.execute('''
                WITH RECURSIVE cte(id) AS (
                    SELECT ?
                    UNION ALL
                    SELECT a.id FROM attributes a
                    INNER JOIN cte ON a.parent_id = cte.id
                )
                DELETE FROM attributes WHERE id IN (SELECT id FROM cte)
            ''', (attribute_id,))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_children(attribute_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM attributes WHERE parent_id = ? ORDER BY sort_order, name',
                (attribute_id,)
            )
            return [dict_from_row(r) for r in cursor.fetchall()]
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_referenced_count(attribute_id):
        """获取属性（包括所有子孙属性）被物品引用的数量。"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                WITH RECURSIVE cte(id) AS (
                    SELECT ?
                    UNION ALL
                    SELECT a.id FROM attributes a
                    INNER JOIN cte ON a.parent_id = cte.id
                )
                SELECT COUNT(DISTINCT ia.item_id) as cnt
                FROM item_attributes ia
                WHERE ia.attribute_id IN (SELECT id FROM cte)
            ''', (attribute_id,))
            row = cursor.fetchone()
            return row['cnt'] if row else 0
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def _get_all_child_ids(attribute_id):
        """递归获取属性所有子孙属性 ID（保留原函数签名，供外部调用）。"""
        children = AttributeModel.get_children(attribute_id)
        result = []
        for child in children:
            result.append(child['id'])
            result.extend(AttributeModel._get_all_child_ids(child['id']))
        return result


# ============================================================
# 物品模型
# ============================================================

class ItemModel:
    """物品模型。"""

    @staticmethod
    def get_all(template_id=None, template_ids=None, keyword=None, attribute_ids=None, page=None, per_page=None):
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

            if template_ids:
                placeholders = ','.join('?' * len(template_ids))
                conditions.append('(i.template_id IN (%s) OR i.template_id IS NULL)' % placeholders)
                params.extend(template_ids)
            elif template_id:
                conditions.append('i.template_id = ?')
                params.append(template_id)

            # keyword 做 LIKE 通配符转义
            if keyword:
                escaped = escape_like(keyword)
                like_pat = '%' + escaped + '%'
                conditions.append('(i.name LIKE ? ESCAPE ? OR i.remark LIKE ? ESCAPE ? OR c.name LIKE ? ESCAPE ? OR attr.name LIKE ? ESCAPE ?)')
                params.extend([like_pat, '\\', like_pat, '\\', like_pat, '\\', like_pat, '\\'])

            if attribute_ids:
                placeholders = ','.join('?' * len(attribute_ids))
                conditions.append('ia.attribute_id IN (%s)' % placeholders)
                params.extend(attribute_ids)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY i.created_at DESC'

            if page and per_page:
                offset = (page - 1) * per_page
                query += ' LIMIT ? OFFSET ?'
                params.extend([per_page, offset])

            cursor.execute(query, params)
            items = [dict_from_row(r) for r in cursor.fetchall()]

            for item in items:
                item['attributes'] = ItemModel.get_item_attributes(item['id'])

            return items
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def count(template_id=None, template_ids=None, keyword=None, attribute_ids=None):
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

            if template_ids:
                placeholders = ','.join('?' * len(template_ids))
                conditions.append('i.template_id IN (%s)' % placeholders)
                params.extend(template_ids)
            elif template_id:
                conditions.append('i.template_id = ?')
                params.append(template_id)

            if keyword:
                escaped = escape_like(keyword)
                like_pat = '%' + escaped + '%'
                conditions.append('(i.name LIKE ? ESCAPE ? OR i.remark LIKE ? ESCAPE ?)')
                params.extend([like_pat, '\\', like_pat, '\\'])

            if attribute_ids:
                placeholders = ','.join('?' * len(attribute_ids))
                query += ' INNER JOIN item_attributes ia ON ia.item_id = i.id'
                conditions.append('ia.attribute_id IN (%s)' % placeholders)
                params.extend(attribute_ids)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            cursor.execute(query, params)
            return cursor.fetchone()['count']
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_by_id(item_id):
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
            item = dict_from_row(cursor.fetchone())
            if item:
                item['attributes'] = ItemModel.get_item_attributes(item['id'])
            return item
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def get_item_attributes(item_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ia.attribute_id as id, a.name, a.parent_id
                FROM item_attributes ia
                INNER JOIN attributes a ON ia.attribute_id = a.id
                WHERE ia.item_id = ?
            ''', (item_id,))
            return [dict_from_row(r) for r in cursor.fetchall()]
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def create(name, template_id, remark=None, images=None, attribute_ids=None):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            cursor.execute(
                'INSERT INTO items (name, template_id, remark, images) VALUES (?, ?, ?, ?)',
                (name, template_id, remark, images)
            )
            item_id = cursor.lastrowid
            if attribute_ids:
                cursor.executemany(
                    'INSERT OR IGNORE INTO item_attributes (item_id, attribute_id) VALUES (?, ?)',
                    [(item_id, aid) for aid in attribute_ids]
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)
        return item_id

    @staticmethod
    def update(item_id, name=None, remark=None, images=None, attribute_ids=None):
        """更新物品。属性值使用事务，避免中间失败导致属性丢失。"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')

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
            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(item_id)
                cursor.execute(
                    'UPDATE items SET %s WHERE id = ?' % ', '.join(updates),
                    params
                )

            if attribute_ids is not None:
                cursor.execute('DELETE FROM item_attributes WHERE item_id = ?', (item_id,))
                if attribute_ids:
                    cursor.executemany(
                        'INSERT OR IGNORE INTO item_attributes (item_id, attribute_id) VALUES (?, ?)',
                        [(item_id, aid) for aid in attribute_ids]
                    )

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def delete(item_id):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            cursor.execute('DELETE FROM item_attributes WHERE item_id = ?', (item_id,))
            cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def batch_delete(item_ids):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            placeholders = ','.join('?' * len(item_ids))
            cursor.execute('DELETE FROM item_attributes WHERE item_id IN (%s)' % placeholders, item_ids)
            cursor.execute('DELETE FROM items WHERE id IN (%s)' % placeholders, item_ids)
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def batch_add_attributes(item_ids, attribute_ids):
        """批量为物品添加属性。使用 INSERT OR IGNORE + executemany，避免并发/重复导致失败。"""
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            rows = [(iid, aid) for iid in item_ids for aid in attribute_ids]
            if rows:
                cursor.executemany(
                    'INSERT OR IGNORE INTO item_attributes (item_id, attribute_id) VALUES (?, ?)',
                    rows
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)

    @staticmethod
    def batch_remove_attributes(item_ids, attribute_ids):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            rows = [(iid, aid) for iid in item_ids for aid in attribute_ids]
            if rows:
                cursor.executemany(
                    'DELETE FROM item_attributes WHERE item_id = ? AND attribute_id = ?',
                    rows
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            _close_if_standalone(conn)


# ============================================================
# 统计模型
# ============================================================

class StatsModel:
    """统计模型。"""

    @staticmethod
    def get_overall():
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM items')
            total_items = cursor.fetchone()['count']

            cursor.execute('''
                SELECT c.name, COUNT(i.id) as count
                FROM categories c
                LEFT JOIN templates t ON c.id = t.category_id
                LEFT JOIN items i ON t.id = i.template_id
                GROUP BY c.id
                ORDER BY count DESC
            ''')
            category_stats = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute('SELECT COUNT(*) as count FROM categories')
            total_categories = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM attributes')
            total_attributes = cursor.fetchone()['count']

            return {
                'total_items': total_items,
                'total_categories': total_categories,
                'total_attributes': total_attributes,
                'category_stats': category_stats
            }
        finally:
            _close_if_standalone(conn)
