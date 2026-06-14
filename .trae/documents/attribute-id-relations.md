# Itemly 属性配置 ID 关系文档

> 本文档梳理 Itemly 项目中属性配置相关的 ID 使用情况，确保前后端对应关系清晰。

---

## 一、ID 关系总览图

### 1.1 表关系图

```
┌─────────────────┐       ┌─────────────────┐
│   categories    │       │    templates    │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄──────│ category_id (FK)│
│ name            │  1:1  │ id (PK)         │
│ sort_order      │       │ name            │
└─────────────────┘       └────────┬────────┘
                                   │
                                   │ 1:N
                                   ▼
                          ┌─────────────────┐
                          │template_attributes│
                          ├─────────────────┤
                          │ id (PK)         │
                          │ template_id(FK) │
                          │ attribute_id(FK)│
                          │ is_required     │
                          └────────┬────────┘
                                   │
                                   │ N:1
                                   ▼
┌─────────────────┐       ┌─────────────────┐
│     items       │       │   attributes    │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ template_id(FK) │       │ name            │
│ name            │       │ parent_id (FK)  │◄────┐
│ remark          │       │ category_id(FK) │     │ 1:N
│ images          │       │ sort_order      │     │ (自关联)
└────────┬────────┘       └─────────────────┘     │
         │                                          │
         │ 1:N        ┌─────────────────┐          │
         ▼             │ item_attributes │          │
┌─────────────────┐    ├─────────────────┤    ┌────┴───────────┐
│  attributes     │    │ id (PK)         │    │   attributes   │
│  (子属性)       │    │ item_id (FK)     │    │   (children)  │
│                 │    │ attribute_id(FK) │────┘                │
└─────────────────┘    └─────────────────┘
```

### 1.2 实体关系说明

| 关系 | 说明 |
|------|------|
| categories → templates | 一对一，一个类别对应一个模板 |
| templates → template_attributes | 一对多，一个模板可配置多个属性 |
| attributes → template_attributes | 多对一，一个属性可被多个模板引用 |
| attributes → attributes | 自关联，一对多，顶级属性可包含多个子属性 |
| items → item_attributes | 一对多，一个物品可有多个属性值 |
| attributes → item_attributes | 多对一，一个属性值对应一个属性 |

---

## 二、数据库表字段详解

### 2.1 categories 表（类别表）

| 字段 | 类型 | 主键 | 外键 | 说明 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | - | 类别主键 |
| `name` | TEXT | - | - | 类别名称 |
| `sort_order` | INTEGER | - | - | 排序顺序 |
| `created_at` | TIMESTAMP | - | - | 创建时间 |

### 2.2 templates 表（模板表）

| 字段 | 类型 | 主键 | 外键 | 说明 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | - | 模板主键 |
| `name` | TEXT | - | - | 模板名称 |
| `category_id` | INTEGER | - | ✓ → categories.id | 关联的类别ID，**唯一约束** |
| `created_at` | TIMESTAMP | - | - | 创建时间 |

### 2.3 attributes 表（属性表）

| 字段 | 类型 | 主键 | 外键 | 说明 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | - | 属性主键 |
| `name` | TEXT | - | - | 属性名称 |
| `parent_id` | INTEGER | - | ✓ → attributes.id | 父属性ID，NULL表示顶级属性 |
| `category_id` | INTEGER | - | ✓ → categories.id | 所属类别ID |
| `sort_order` | INTEGER | - | - | 排序顺序 |
| `created_at` | TIMESTAMP | - | - | 创建时间 |

### 2.4 template_attributes 表（模板属性关联表）

| 字段 | 类型 | 主键 | 外键 | 说明 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | - | 关联记录主键 |
| `template_id` | INTEGER | - | ✓ → templates.id | 模板ID |
| `attribute_id` | INTEGER | - | ✓ → attributes.id | 属性ID |
| `is_required` | INTEGER | - | - | 是否必填（0/1） |
| `sort_order` | INTEGER | - | - | 排序顺序 |

### 2.5 items 表（物品表）

| 字段 | 类型 | 主键 | 外键 | 说明 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | - | 物品主键 |
| `name` | TEXT | - | - | 物品名称 |
| `template_id` | INTEGER | - | ✓ → templates.id | 模板ID |
| `remark` | TEXT | - | - | 备注描述 |
| `images` | TEXT | - | - | 图片路径（JSON格式） |
| `created_at` | TIMESTAMP | - | - | 创建时间 |
| `updated_at` | TIMESTAMP | - | - | 更新时间 |

### 2.6 item_attributes 表（物品属性值表）

| 字段 | 类型 | 主键 | 外键 | 说明 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | - | 记录主键 |
| `item_id` | INTEGER | - | ✓ → items.id | 物品ID |
| `attribute_id` | INTEGER | - | ✓ → attributes.id | 属性ID（叶子属性） |

---

## 三、API 接口 ID 参数对照

### 3.1 属性相关接口 (routes/attributes.py)

#### GET /api/attributes
获取属性列表

| 类型 | 参数 | 字段 |
|------|------|------|
| Query | tree | 返回树形结构（默认true） |
| Query | flat | 返回扁平结构（默认false） |
| 响应 | data[].id | 属性ID |
| 响应 | data[].parent_id | 父属性ID |
| 响应 | data[].children[].id | 子属性ID |

#### GET /api/attributes/<attribute_id>
获取单个属性详情

| 类型 | 参数 | 字段 |
|------|------|------|
| Path | attribute_id | 属性ID |
| 响应 | data.id | 属性ID |
| 响应 | data.parent_id | 父属性ID |
| 响应 | data.children | 子属性数组 |

#### POST /api/attributes
创建属性

| 类型 | 参数 | 字段 |
|------|------|------|
| Body | name | 属性名称 |
| Body | parent_id | 父属性ID（可选，null表示顶级） |
| Body | category_id | 类别ID（可选） |
| Body | sort_order | 排序顺序 |
| 响应 | data.id | 新创建的属性ID |

#### PUT /api/attributes/<attribute_id>
更新属性

| 类型 | 参数 | 字段 |
|------|------|------|
| Path | attribute_id | 属性ID |
| Body | name | 属性名称 |
| Body | sort_order | 排序顺序 |

#### DELETE /api/attributes/<attribute_id>
删除属性

| 类型 | 参数 | 字段 |
|------|------|------|
| Path | attribute_id | 属性ID |
| 响应 | success | 是否成功 |

### 3.2 类别相关接口 (routes/categories.py)

#### GET /api/categories
获取类别列表

| 类型 | 参数 | 字段 |
|------|------|------|
| 响应 | data[].id | 类别ID |
| 响应 | data[].template_id | 模板ID |
| 响应 | data[].template_name | 模板名称 |

#### POST /api/categories
创建类别

| 类型 | 参数 | 字段 |
|------|------|------|
| Body | name | 类别名称 |
| Body | sort_order | 排序顺序 |
| Body | attributes[].attribute_id | 属性ID |
| Body | attributes[].is_required | 是否必填 |
| 响应 | data.id | 新创建的类别ID |

#### GET /api/categories/<category_id>/template
获取类别的模板配置

| 类型 | 参数 | 字段 |
|------|------|------|
| Path | category_id | 类别ID |
| 响应 | data.id | 模板ID |
| 响应 | data.attributes[].attribute_id | 属性ID |
| 响应 | data.attributes[].children[].id | 子属性ID |

#### PUT /api/categories/<category_id>/template
更新类别模板配置

| 类型 | 参数 | 字段 |
|------|------|------|
| Path | category_id | 类别ID |
| Body | name | 类别名称 |
| Body | template_name | 模板名称 |
| Body | attributes[].attribute_id | 属性ID |
| Body | attributes[].is_required | 是否必填 |

---

## 四、前端变量 ID 字段清单

### 4.1 全局属性数据变量

#### window.templateCurrentAttrs
**来源**: 从 `/api/categories/<id>/template` 加载的已有属性  
**用途**: 模板配置中已关联的属性列表

```javascript
// 结构：
[
  {
    attribute_id: Number,      // 属性ID（来自 attributes 表）
    attribute_name: String,   // 属性名称
    parent_id: Number|null,   // 父属性ID
    is_required: Boolean,
    children: [              // 子属性数组
      {
        id: Number,           // 子属性ID
        name: String,         // 子属性名称
        parent_id: Number     // 父属性ID
      }
    ]
  }
]
```

#### window.templateNewAttrs
**来源**: 用户在模板配置界面新增的属性  
**用途**: 存储新建但尚未保存到后端的属性

```javascript
// 结构：
[
  {
    tempId: String,           // 临时ID，格式: 'new_' + Date.now()
    name: String,             // 属性名称
    parent_id: Number|null,   // 父属性ID（null表示顶级）
    is_required: Boolean
  }
]
```

#### window.categoryCurrentAttrs
**来源**: 类别编辑时从API加载的属性  
**用途**: 类别关联的已有属性列表（与 templateCurrentAttrs 结构相同）

#### window.categoryNewAttrs
**来源**: 类别编辑时用户新增的属性  
**用途**: 类别配置中新建但未保存的属性

### 4.2 物品属性相关变量

#### inlineSelectedAttrs
**来源**: 行内添加物品时选择的属性  
**用途**: 存储用户为当前物品选择的属性

```javascript
// 结构：
[
  {
    tempId: String,           // 临时ID 或 id 二选一
    id: Number,               // 属性ID
    name: String,
    parent_id: Number|null,
    parent_name: String
  }
]
```

#### selectedAttrValues
**来源**: 物品编辑时选择的属性值  
**用途**: 以父属性ID为key存储选中的子属性ID

```javascript
// 结构: { [parentId]: attribute_id }
// 示例: { '12': 15, '8': 22 }
// 含义: 父属性ID=12 下选择了属性ID=15，父属性ID=8 下选择了属性ID=22
```

### 4.3 ID 转换映射表

#### attrIdMap
**用途**: 新建属性时，tempId 到真实 attribute_id 的映射

```javascript
// 结构: { [tempId]: realId }
// 示例: { 'new_1712345678': 15 }
```

---

## 五、前后端字段映射表

### 5.1 创建类别/模板属性配置

| 阶段 | 变量/字段 | 字段名 | 示例值 |
|------|-----------|--------|--------|
| 前端收集 | attr.attribute_id | 已有属性的ID | `5` |
| 前端收集 | attr.tempId | 新建属性的临时ID | `'new_1712345678'` |
| 前端请求体 | attributes[].attribute_id | 属性ID（统一使用此字段名） | `{ attribute_id: 5 }` |
| 后端接收 | data.get('attributes')[i]['attribute_id'] | 属性ID | `5` |
| 后端存储 | template_attributes.attribute_id | 关联的属性ID | `5` |

### 5.2 获取模板属性列表

| 阶段 | 变量/字段 | 字段名 | 示例值 |
|------|-----------|--------|--------|
| 后端返回 | attributes[].id | 顶级属性ID（模型层） | `5` |
| 后端返回 | attributes[].attribute_id | API返回时统一用此字段 | `5` |
| 前端接收 | result.data.attributes[].attribute_id | 顶级属性ID | `5` |
| 后端返回 | attributes[].children[].id | 子属性ID | `7` |
| 前端接收 | result.data.attributes[].children[].id | 子属性ID | `7` |

### 5.3 物品属性选择

| 阶段 | 变量/字段 | 字段名 | 示例值 |
|------|-----------|--------|--------|
| 前端渲染 | renderAttrTree() 中 attr.id | 树节点ID | `'5'` |
| 用户点击 | handleItemAttrSelectDirect(attrKey, parentId, attrId) | attrId为属性ID | `'7'` |
| 前端存储 | selectedAttrValues[parentId] = numAttrId | 选中的属性ID | `{ '5': 7 }` |
| 保存物品 | attribute_ids: Object.values(selectedAttrValues) | 属性ID数组 | `[7, 15]` |

### 5.4 创建新属性

| 阶段 | 变量/字段 | 字段名 | 示例值 |
|------|-----------|--------|--------|
| 前端生成 | tempId = 'new_' + Date.now() | 临时ID | `'new_1712345678'` |
| 前端请求体 | { name, parent_id, category_id } | 创建属性参数 | `{ name: '颜色', parent_id: 5 }` |
| 后端返回 | data.id | 新属性ID | `16` |
| 前端更新 | attrIdMap['new_1712345678'] = 16 | 建立映射 | `{ 'new_...': 16 }` |

---

## 六、ID 转换流程图

### 6.1 新建属性时的 ID 转换

```
┌─────────────────────────────────────────────────────────────┐
│                     用户操作流程                              │
└─────────────────────────────────────────────────────────────┘

用户输入属性名
        │
        ▼
┌─────────────────┐
│ 前端生成 tempId │
│ tempId =        │
│ 'new_' + Date.now() │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ 存入对应的新属性数组:                             │
│ • templateNewAttrs                              │
│ • categoryNewAttrs                              │
│ • inlineSelectedAttrs                           │
│ 结构: { tempId: 'new_xxx', name: '颜色', ... }  │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ 调用 API 创建属性                               │
│ POST /api/attributes                            │
│ Body: { name, parent_id, category_id }         │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ 后端返回: { success: true, data: { id: 16 } }   │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ 前端更新映射表:                                  │
│ attrIdMap['new_xxx'] = 16                       │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ 保存模板/类别配置时:                             │
│ • 已有属性: { attribute_id: realId }           │
│ • 新建属性: { attribute_id: attrIdMap[tempId] } │
└─────────────────────────────────────────────────┘
```

### 6.2 子属性创建时的父ID处理

```
┌─────────────────────────────────────────────────────────────┐
│                     创建子属性流程                            │
└─────────────────────────────────────────────────────────────┘

用户选择父属性，添加子属性
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 获取父属性ID: parentRealId                        │
│ 判断父属性是否为新属性:                           │
│   if (parentRealId 是数字)                        │
│     → 父属性是已有属性，parentRealId = 数字ID     │
│   else (是 tempId 格式)                           │
│     → 父属性是新属性，从 attrIdMap 获取真实ID    │
│     → parentRealId = attrIdMap[parentRealId]     │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ 创建子属性请求:                                   │
│ POST /api/attributes                            │
│ Body: {                                         │
│   name: '子属性名',                              │
│   parent_id: parentRealId,  // 真实ID          │
│   category_id: categoryId                        │
│ }                                               │
└─────────────────────────────────────────────────┘
```

---

## 七、关键发现与建议

### 7.1 发现的不一致问题

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| 顶级属性用 `attribute_id`，子属性用 `id` | 前端 index.html 第1179行 | 访问属性ID时需要区分 | 统一使用 `id` 字段 |
| API返回字段名与前端存储不一致 | models.py vs index.html | 容易混淆 | 统一后端API返回字段名 |

### 7.2 字段命名规范建议

| 场景 | 建议字段名 | 说明 |
|------|-----------|------|
| 属性主键 | `id` | 统一使用 `id` |
| 父属性引用 | `parent_id` | 保持一致 |
| 模板属性关联.属性ID | `attribute_id` | 关联表中使用全名 |
| 物品属性值.属性ID | `attribute_id` | 关联表中使用全名 |
| 临时ID | `temp_id` | 替代 `tempId`，更规范 |

### 7.3 前端变量命名规范

| 变量 | 建议重命名 | 说明 |
|------|-----------|------|
| templateCurrentAttrs | templateAttrs | 简化命名 |
| templateNewAttrs | templateNewAttrIds | 明确是ID列表 |
| categoryCurrentAttrs | categoryAttrs | 简化命名 |
| categoryNewAttrs | categoryNewAttrIds | 明确是ID列表 |
| inlineSelectedAttrs | inlineSelectedAttrIds | 明确是ID列表 |
| attrIdMap | tempToRealIdMap | 更清晰的语义 |

---

## 八、快速参考

### 8.1 ID 类型速查

| ID类型 | 格式 | 示例 | 来源 |
|--------|------|------|------|
| 类别ID | 数字 | `5` | categories.id |
| 模板ID | 数字 | `3` | templates.id |
| 属性ID | 数字 | `12` | attributes.id |
| 临时ID | 字符串 | `'new_1712345678'` | 前端生成 |
| 模板属性关联ID | 数字 | `45` | template_attributes.id |
| 物品属性值ID | 数字 | `78` | item_attributes.id |

### 8.2 常用 API 路径

| 功能 | 方法 | 路径 | 关键ID参数 |
|------|------|------|------------|
| 获取属性树 | GET | `/api/attributes?tree=true` | - |
| 创建属性 | POST | `/api/attributes` | parent_id, category_id |
| 获取模板配置 | GET | `/api/categories/<category_id>/template` | category_id |
| 更新模板配置 | PUT | `/api/categories/<category_id>/template` | category_id |
| 获取物品属性值 | GET | `/api/items/<item_id>/attributes` | item_id |

---

*文档版本: v1.0 | 生成日期: 2026-06-14*
