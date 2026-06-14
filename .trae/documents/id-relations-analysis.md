# 系统ID和表关系分析

## 数据库表结构总览

### 1. users（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 用户唯一标识 |
| `username` | TEXT UNIQUE NOT NULL | 用户名 |
| `password_hash` | TEXT NOT NULL | 密码哈希 |
| `display_name` | TEXT | 显示名称 |
| `created_at` | TIMESTAMP | 创建时间 |

**ID用途**：用于用户认证和会话管理。

---

### 2. categories（类别表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 类别唯一标识 |
| `name` | TEXT NOT NULL | 类别名称 |
| `sort_order` | INTEGER DEFAULT 0 | 排序顺序 |
| `created_at` | TIMESTAMP | 创建时间 |

**ID用途**：类别管理、侧边栏显示、物品分类。

---

### 3. templates（模板表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 模板唯一标识 |
| `name` | TEXT NOT NULL | 模板名称 |
| `category_id` | INTEGER NOT NULL UNIQUE | **关联 categories.id** |
| `created_at` | TIMESTAMP | 创建时间 |

**外键关系**：`category_id` → `categories.id`（ON DELETE CASCADE）

**ID用途**：每个类别绑定一个模板，模板定义类别包含的属性字段。

---

### 4. attributes（属性表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | **属性唯一标识（核心ID）** |
| `name` | TEXT NOT NULL | 属性名称 |
| `parent_id` | INTEGER DEFAULT NULL | **关联 attributes.id（自引用）** |
| `sort_order` | INTEGER DEFAULT 0 | 排序顺序 |
| `category_id` | INTEGER DEFAULT NULL | **关联 categories.id** |
| `created_at` | TIMESTAMP | 创建时间 |

**外键关系**：
- `parent_id` → `attributes.id`（ON DELETE CASCADE）- 形成树形结构
- `category_id` → `categories.id`（ON DELETE CASCADE）- 按类别隔离属性树

**ID用途**：
- `attributes.id` 是属性的**真实唯一标识**
- `parent_id` 建立属性的父子关系（多级树形结构）
- `category_id` 实现属性树按类别隔离

---

### 5. template_attributes（模板-属性关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | **关联记录唯一标识** |
| `template_id` | INTEGER NOT NULL | **关联 templates.id** |
| `attribute_id` | INTEGER NOT NULL | **关联 attributes.id** |
| `is_required` | INTEGER DEFAULT 0 | 是否必填（0/1） |
| `sort_order` | INTEGER DEFAULT 0 | 排序顺序 |

**外键关系**：
- `template_id` → `templates.id`（ON DELETE CASCADE）
- `attribute_id` → `attributes.id`（ON DELETE CASCADE）

**ID用途**：
- `id` 是关联记录的主键，**不是属性ID**
- `attribute_id` 才是真正的属性ID（关联 `attributes.id`）
- 这个表定义了"某个模板包含哪些顶级属性字段"

---

### 6. items（物品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 物品唯一标识 |
| `name` | TEXT NOT NULL | 物品名称 |
| `template_id` | INTEGER NOT NULL | **关联 templates.id** |
| `remark` | TEXT | 备注 |
| `images` | TEXT | 图片（JSON数组） |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

**外键关系**：`template_id` → `templates.id`（ON DELETE CASCADE）

**ID用途**：物品管理、搜索、展示。

---

### 7. item_attributes（物品-属性关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 关联记录唯一标识 |
| `item_id` | INTEGER NOT NULL | **关联 items.id** |
| `attribute_id` | INTEGER NOT NULL | **关联 attributes.id** |

**外键关系**：
- `item_id` → `items.id`（ON DELETE CASCADE）
- `attribute_id` → `attributes.id`（ON DELETE CASCADE）

**ID用途**：记录物品选择了哪些属性值。

---

## ID混淆问题详解

### 问题根源

**`template_attributes` 表有两个容易混淆的ID：**

| ID字段 | 所属表 | 含义 | 示例值 |
|--------|--------|------|--------|
| `id` | template_attributes | 关联记录的主键 | 25 |
| `attribute_id` | template_attributes | 真正的属性ID | 5 |

**后端 `get_with_attributes` 函数返回的数据结构**：

```javascript
{
    id: 25,                    // template_attributes.id（中间表主键）
    attribute_id: 5,           // attributes.id（真正的属性ID）
    name: "颜色",
    parent_id: null,
    is_required: 1,
    sort_order: 0,
    children: [
        {
            id: 6,             // attributes.id（子属性的真实ID）
            name: "红色",
            parent_id: 5,      // 指向 attributes.id
            children: []
        }
    ]
}
```

### 前端代码中的ID混用问题

**位置1：属性收集逻辑（saveTemplateConfig）**

```javascript
function collectAttrs(attrs, isNew = false) {
    for (const attr of attrs) {
        allAttrs.push({
            id: isNew ? attr.tempId : attr.id,  // ❌ 使用了 attr.id（可能是 template_attributes.id）
            name: attr.name,
            parent_id: attr.parent_id,          // ✅ 正确，是 attributes.id
            isNew: isNew
        });
        // ...
    }
}
```

**问题**：对于已有属性，`attr.id` 是 `template_attributes.id`（如25），但 `attr.parent_id` 是 `attributes.id`（如5），导致ID不匹配。

**位置2：顶级属性验证**

```javascript
const allTopLevelFields = [
    ...window.templateCurrentAttrs.map(a => ({id: a.id, name: a.name})),  // ❌ id = 25
    ...newTopFields.map(a => ({id: a.tempId, name: a.name}))
];
for (const field of allTopLevelFields) {
    const fieldId = field.id;  // fieldId = 25
    const fieldValues = allAttrs.filter(a => String(a.parent_id) === String(fieldId));  // 找 parent_id = 25
    // ❌ 但子属性的 parent_id = 5，所以找不到！
}
```

**位置3：渲染时的buildTree函数**

```javascript
const id = attrIsNew ? attr.tempId : attr.id;  // ❌ 使用了错误的ID
```

### 正确的ID使用方式

| 场景 | 应该使用的ID | 说明 |
|------|-------------|------|
| 顶级属性标识 | `attribute_id` | 从 template_attributes 获取 |
| 子属性标识 | `id` | 从 attributes 获取（已经是 attributes.id） |
| 父子关系匹配 | `attribute_id` ↔ `parent_id` | 两者都是 attributes.id |

---

## 表关系图

```
categories(id) ──1:1── templates(id, category_id)
     │                      │
     │                      │
     │              template_attributes(id, template_id, attribute_id)
     │                              │
     └────────── attributes(id, parent_id, category_id)
                      │
                      │
               item_attributes(item_id, attribute_id)
                      │
               items(id, template_id)
```

---

## 总结

| 表 | 主键ID | 关联的外键 |
|----|--------|-----------|
| users | `id` | - |
| categories | `id` | templates.category_id, attributes.category_id |
| templates | `id` | template_attributes.template_id, items.template_id |
| attributes | `id` | attributes.parent_id, template_attributes.attribute_id, item_attributes.attribute_id |
| template_attributes | `id` | - |
| items | `id` | item_attributes.item_id |
| item_attributes | `id` | - |

**核心问题**：前端代码混淆了 `template_attributes.id` 和 `attributes.id`，导致父子关系匹配失败。