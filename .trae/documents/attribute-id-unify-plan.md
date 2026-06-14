# 属性ID字段统一修改计划

## 一、问题分析

### 1.1 当前状态

| 层级 | 后端返回字段 | 前端访问字段 | 问题 |
|------|-------------|-------------|------|
| 顶级属性 | `attribute_id` | `attr.attribute_id` | 与子属性字段不一致 |
| 子属性 | `id` | `attr.id` | 与顶级属性字段不一致 |
| 新建属性 | `tempId`（前端生成） | `attr.tempId` | 需要映射转换 |

### 1.2 影响范围

**后端文件**：
- `backend/models.py` - `get_with_attributes()` 方法

**前端文件**：
- `frontend/html/index.html` - 多个函数涉及属性ID访问

## 二、修改目标

统一使用 `id` 作为属性ID字段名，消除不一致性。

## 三、修改方案

### 3.1 后端修改

**文件**: `backend/models.py`

**位置**: `TemplateModel.get_with_attributes()` 方法（约第465行）

**修改内容**:
- 将 `SELECT id as attribute_id` 修改为 `SELECT id`
- 确保顶级属性和子属性都使用 `id` 字段

### 3.2 前端修改

需要修改以下函数中的属性ID访问：

| 函数名 | 行号 | 修改内容 |
|--------|------|----------|
| `renderAttrTree()` | 1202 | 使用 `attr.id` |
| `renderAttrTree()`（物品选择器） | 2461 | 使用 `attr.id` |
| `saveItem()` | 2627 | 使用 `attr.id` |
| `handleItemAttrSelectDirect()` | 2683 | 使用 `attr.id` 和 `attr.parent_id` |
| `collectAttrs()` | 2870 | 使用 `attr.id` |
| `renderCategoryAttrTree()` | 2940 | 使用 `attr.id` |
| `deleteInlineAttr()` | 3065 | 使用 `attr.id` |
| `loadTemplateAttributes()` | 3175 | 使用 `attr.id` |
| `saveTemplateConfig()` | 3805 | 使用 `attr.id` |
| `renderAttrTreeForFilter()` | 3896 | 使用 `attr.id` |
| `prepareCategoryAttrs()` | 4018 | 使用 `attr.id` |

### 3.3 修改规则

| 当前写法 | 改为 |
|----------|------|
| `attr.attribute_id` | `attr.id` |
| `attr.attribute_name` | `attr.name` |
| `attr.attribute_id || attr.id` | `attr.id` |
| `String(attr.attribute_id)` | `String(attr.id)` |

## 四、实施步骤

### 步骤1：修改后端 models.py

```python
# 修改前（第465行）
SELECT id as attribute_id, name as attribute_name, parent_id

# 修改后
SELECT id, name, parent_id
```

### 步骤2：修改前端 index.html

需要批量替换以下模式：
- `attribute_id` → `id`
- `attribute_name` → `name`

### 步骤3：更新临时ID处理逻辑

确保 `tempId` 的处理逻辑保持不变，仅修改从API返回的数据访问。

### 步骤4：测试验证

1. 启动应用
2. 创建类别并配置属性
3. 添加物品并选择属性
4. 验证属性筛选功能正常

## 五、风险评估

| 风险 | 等级 | 应对措施 |
|------|------|----------|
| API返回字段变更导致前端报错 | 高 | 先修改后端，再同步修改前端 |
| 数据库重建后数据丢失 | 中 | 修改前备份数据库 |
| 临时ID映射逻辑受影响 | 低 | 仅修改API返回字段，不影响前端生成的tempId |

## 六、预期效果

修改完成后，代码将更加清晰：
- 所有属性（顶级和子属性）统一使用 `id` 字段
- 前端代码无需再判断使用哪个字段
- 减少潜在的bug和维护成本