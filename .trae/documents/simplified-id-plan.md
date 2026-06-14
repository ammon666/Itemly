# 简化数据表及ID关系设计

## 设计原则

1. **属性值绑定模板**：属性直接绑定到模板，不在模板间共享
2. **分类与模板一一对应**：一个分类只有一个模板
3. **避免创造新ID**：使用已有ID建立关联
4. **模板隔离**：每个模板的属性值完全独立

## 简化后的表结构

### 1. categories（类别表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 类别唯一标识 |
| `name` | TEXT NOT NULL | 类别名称 |
| `sort_order` | INTEGER DEFAULT 0 | 排序顺序 |

### 2. templates（模板表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 模板唯一标识 |
| `name` | TEXT NOT NULL | 模板名称 |
| `category_id` | INTEGER NOT NULL UNIQUE | 关联 categories.id |

**关系**：`category_id` → `categories.id`（1:1）

### 3. attributes（属性表）- 核心修改

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 属性唯一标识 |
| `name` | TEXT NOT NULL | 属性名称 |
| `parent_id` | INTEGER DEFAULT NULL | 关联 attributes.id（自引用） |
| `template_id` | INTEGER NOT NULL | **关联 templates.id** |
| `sort_order` | INTEGER DEFAULT 0 | 排序顺序 |

**关键变更**：
- ✅ 新增 `template_id`：属性直接绑定到模板
- ❌ 移除 `category_id`：通过模板间接关联分类

**关系**：
- `parent_id` → `attributes.id`（自引用，形成树形结构）
- `template_id` → `templates.id`（属性属于哪个模板）

### 4. items（物品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 物品唯一标识 |
| `name` | TEXT NOT NULL | 物品名称 |
| `template_id` | INTEGER NOT NULL | 关联 templates.id |
| `remark` | TEXT | 备注 |

### 5. item_attributes（物品-属性关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 关联记录ID |
| `item_id` | INTEGER NOT NULL | 关联 items.id |
| `attribute_id` | INTEGER NOT NULL | 关联 attributes.id |

---

## 简化后的ID关系图

```
categories(id) ──1:1── templates(id, category_id)
                              │
                              │ 1:N
                              ▼
                      attributes(id, parent_id, template_id)
                              │
                              │ N:N
                              ▼
                       items(id, template_id)
                              │
                              │
                      item_attributes(item_id, attribute_id)
```

---

## 核心简化点

### 1. 移除 template_attributes 中间表

**原设计**：`templates` ↔ `template_attributes` ↔ `attributes`

**新设计**：`templates` ↔ `attributes`（直接关联）

**优势**：
- 减少一层关联，简化查询
- 属性直接属于模板，无需中间表

### 2. 属性按模板隔离

```javascript
// 获取模板的所有属性
SELECT * FROM attributes WHERE template_id = ? ORDER BY sort_order;

// 获取属性的子属性
SELECT * FROM attributes WHERE parent_id = ? AND template_id = ? ORDER BY sort_order;
```

### 3. 重复性校验范围

```javascript
// 只在当前模板内校验重名
SELECT * FROM attributes 
WHERE name = ? 
  AND parent_id = ? 
  AND template_id = ?;
```

---

## 代码修改计划

### 后端修改

**文件**: `backend/models.py`

#### 修改1：更新 attributes 表结构（第81-91行）

```python
# 修改前
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attributes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_id INTEGER DEFAULT NULL,
        sort_order INTEGER DEFAULT 0,
        category_id INTEGER DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES attributes(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    )
''')

# 修改后
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
```

#### 修改2：更新 AttributeModel.create（第689-703行）

```python
# 修改前
@staticmethod
def create(name, parent_id=None, sort_order=0, category_id=None):
    """创建属性（按 category_id 隔离属性树）"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO attributes (name, parent_id, sort_order, category_id) VALUES (?, ?, ?, ?)',
            (name, parent_id, sort_order, category_id)
        )
        attribute_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return attribute_id

# 修改后
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
```

#### 修改3：更新 find_by_name_and_parent（第655-687行）

```python
# 修改后
@staticmethod
def find_by_name_and_parent(name, parent_id=None, template_id=None):
    """根据名称和父ID查找同级属性（按模板隔离）"""
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
        attr = cursor.fetchone()
        return dict_from_row(attr) if attr else None
    finally:
        conn.close()
```

#### 修改4：更新 get_tree（第592-621行）

```python
# 修改后
@staticmethod
def get_tree(template_id=None):
    """获取属性树形结构（按模板隔离）"""
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
```

#### 修改5：更新 get_all（第574-589行）

```python
# 修改后
@staticmethod
def get_all(template_id=None):
    """获取所有属性（按模板过滤）"""
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
```

#### 修改6：更新 TemplateModel.get_with_attributes（第443-490行）

```python
# 修改后
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
```

### 后端路由修改

**文件**: `backend/routes/attributes.py`

#### 修改 create_attribute（第59-96行）

```python
@attributes_bp.route('', methods=['POST'])
@login_required
def create_attribute():
    """创建属性（按 template_id 隔离属性树）"""
    data = request.get_json()
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    template_id = data.get('template_id')
    sort_order = data.get('sort_order', 0)

    if not name:
        return jsonify({'success': False, 'message': '属性名称不能为空'}), 400

    if not parent_id:
        parent_id = None

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
```

### 前端修改

**文件**: `frontend/html/index.html`

#### 修改1：保存模板配置时使用 template_id

```javascript
// 保存时创建属性
const result = await api('/attributes', { 
    method: 'POST', 
    body: { 
        name: newAttr.name, 
        parent_id: parentRealId, 
        template_id: templateId  // 使用模板ID而非类别ID
    } 
});
```

#### 修改2：移除 template_attributes 相关逻辑

删除 `window.templateCurrentAttrs`、`window.templateNewAttrs` 等变量的复杂处理，直接操作属性树。

---

## 迁移方案

### 1. 数据迁移脚本

```python
def migrate_attributes():
    """迁移现有属性数据到新结构"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # 为 attributes 表添加 template_id 字段
        cursor.execute('ALTER TABLE attributes ADD COLUMN template_id INTEGER')
        
        # 更新现有属性的 template_id
        cursor.execute('''
            UPDATE attributes a
            SET template_id = (
                SELECT t.id 
                FROM templates t 
                WHERE t.category_id = a.category_id
            )
            WHERE a.category_id IS NOT NULL
        ''')
        
        conn.commit()
    finally:
        conn.close()
```

### 2. 删除旧表

```python
def cleanup_old_tables():
    """删除不再需要的表"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS template_attributes')
        conn.commit()
    finally:
        conn.close()
```

---

## 验证步骤

1. 创建新类别 → 自动创建模板
2. 添加属性（顶级）→ 添加子属性（二级）→ 添加孙属性（三级）
3. 编辑类别，删除二级属性
4. 确认剩余属性正确显示
5. 添加新属性并保存
6. 验证物品创建时属性选择正确

---

## 风险评估

| 风险 | 等级 | 说明 |
|------|------|------|
| 数据迁移 | 中 | 需要迁移现有数据到新结构 |
| API兼容性 | 低 | 修改后API参数变化，需要同步更新前端 |
| 功能回归 | 低 | 核心逻辑简化，减少出错点 |

---

## 优先级

**高**：此修改将彻底解决ID混淆问题，简化数据结构