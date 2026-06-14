# 属性配置 ID 关系梳理计划

## 一、任务目标

梳理 Itemly 项目中属性配置相关的 ID 使用情况，整理成一套完整的 ID 关系图，确保前后端对应关系清晰。

## 二、当前状态分析

### 2.1 数据库表结构

项目涉及 6 张表，其中与属性配置相关的有：

1. **categories** - 类别表
   - `id` - 类别主键

2. **templates** - 模板表
   - `id` - 模板主键
   - `category_id` - 关联类别ID

3. **attributes** - 属性表（核心）
   - `id` - 属性主键
   - `name` - 属性名称
   - `parent_id` - 父属性ID（自关联）
   - `category_id` - 所属类别ID
   - `sort_order` - 排序

4. **template_attributes** - 模板属性关联表
   - `id` - 主键
   - `template_id` - 模板ID
   - `attribute_id` - 属性ID
   - `is_required` - 是否必填

5. **items** - 物品表
   - `id` - 物品主键
   - `template_id` - 模板ID

6. **item_attributes** - 物品属性值表
   - `id` - 主键
   - `item_id` - 物品ID
   - `attribute_id` - 属性ID

### 2.2 发现的问题

| 问题 | 位置 | 说明 |
|------|------|------|
| ID字段命名不一致 | 前端 index.html | 顶级属性用 `attribute_id`，子属性用 `id` |
| 临时ID转换逻辑 | 前端 index.html | 新建属性使用 `tempId`，保存时需映射转换 |
| 后端API命名 | routes/attributes.py | URL参数用 `attribute_id`，但内部变量用 `id` |

## 三、ID 关系图

### 3.1 表关系图

```
categories (1) ────── (1) templates
    │                      │
    │ 1:1                   │ 1:N
    │                      │
    ▼                      ▼
templates              template_attributes
                            │
                            │ N:1
                            ▼
                        attributes
                            │
                            │ 1:N (自关联)
                            │
                            ▼
                        attributes (children)
```

### 3.2 ID 字段对照表

| 表名 | 字段 | 类型 | 说明 |
|------|------|------|------|
| categories | id | INTEGER | 类别主键 |
| templates | id | INTEGER | 模板主键 |
| templates | category_id | INTEGER | 关联类别 |
| attributes | id | INTEGER | 属性主键 |
| attributes | parent_id | INTEGER | 父属性（自关联） |
| attributes | category_id | INTEGER | 所属类别 |
| template_attributes | id | INTEGER | 关联主键 |
| template_attributes | template_id | INTEGER | 模板ID |
| template_attributes | attribute_id | INTEGER | 属性ID |
| template_attributes | is_required | INTEGER | 是否必填 |

### 3.3 前后端字段对应

#### 创建类别时

| 阶段 | 字段 | 示例 |
|------|------|------|
| 前端数据结构 | `attributes[].attribute_id` | `{ attribute_id: 5 }` |
| 前端请求体 | `attributes[].attribute_id` | `{ attribute_id: 5 }` |
| 后端接收 | `data.get('attributes')[i]['attribute_id']` | `5` |
| 后端存储 | `template_attributes.attribute_id` | `5` |

#### 物品属性选择时

| 阶段 | 字段 | 示例 |
|------|------|------|
| 后端API返回 | `attributes[].attribute_id` | `{ attribute_id: 5 }` |
| 后端API返回(子属性) | `attributes[].children[].id` | `{ id: 7 }` |
| 前端存储(顶级) | `window.templateCurrentAttrs[].attribute_id` | `5` |
| 前端存储(子属性) | `window.templateCurrentAttrs[].children[].id` | `7` |

## 四、输出文档

将创建一份完整的 ID 关系文档，包含：

1. **ID关系总览图** - 用文字/ASCII图形展示各表关系
2. **数据库表字段详解** - 每个表的主键、外键说明
3. **API接口ID参数对照** - 各接口的输入输出ID字段
4. **前端变量ID字段清单** - 前端JavaScript中的ID字段使用
5. **前后端字段映射表** - 同一数据在前后的字段名差异
6. **ID转换流程图** - 新建属性时tempId→真实ID的转换过程

## 五、实施步骤

1. 在 `.trae/documents/` 目录创建 `attribute-id-relations.md` 文件
2. 按照上述结构整理完整内容
3. 确保每个ID字段都有清晰的来源和用途说明

## 六、假设与决策

- 假设文档以 Markdown 格式输出，便于阅读和维护
- 假设需要同时包含中文和英文字段名，方便理解代码
- 决策：使用表格形式展示对照关系，便于查找
