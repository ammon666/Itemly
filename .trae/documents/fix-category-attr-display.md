# 修复计划：编辑类别时属性值不显示

## 问题描述
- 添加类别时能正常显示属性值
- 编辑类别时不能显示属性值（只显示顶级属性，不显示子属性/属性值）

## 问题分析

### 数据流差异

| 场景 | 数据来源 | 字段名 |
|------|----------|--------|
| 添加 | `window.categoryNewAttrs` | `tempId`, `name`, `parent_id` |
| 编辑 | `window.categoryCurrentAttrs` (API) + `window.categoryNewAttrs` | 顶级: `attribute_id`, `attribute_name`<br>子属性 (来自 `/attributes/{id}/children`): `id`, `name` |

### 关键代码路径

1. `showCategoryModal(id)` → 判断是添加还是编辑
2. 编辑时调用 `loadCategoryCurrentAttrs(id)` → 异步加载 API 数据
3. `loadCategoryChildrenRecursively()` → 递归加载子属性
4. `renderCategoryCurrentAttrs()` → 渲染属性列表

### 发现的问题

**问题1: `loadCategoryChildrenRecursively` 加载的子属性字段名不统一**

API `/attributes/{id}/children` 返回的子属性字段是 `id`, `name`，不是 `attribute_id`, `attribute_name`。

在 `topLevelFromCurrent` 中：
```javascript
children: (attr.children || []).map(c => ({
    ...c,
    tempId: String(c.id || c.attribute_id),  // 这里是 id，但后续可能混用
    attribute_name: c.attribute_name || c.name,  // c.attribute_name 是 undefined
    ...
}))
```

在 `flattenAllAttrs` 中：
```javascript
const id = attr.attribute_id || attr.tempId;  // attr.attribute_id 是 undefined（因为是子属性）
```

子属性没有 `attribute_id`，只有 `id`，导致 `flattenAllAttrs` 时 id 为 undefined。

**问题2: 异步加载时序问题**

`loadCategoryCurrentAttrs` 是 async 函数，但可能在数据加载完成前就开始渲染。

## 修复方案

### 修复1: 统一 `flattenAllAttrs` 中子属性的 ID 获取

**文件**: `frontend/html/index.html`
**位置**: 第3300行附近

**修改**:
```javascript
// 修改前
const id = attr.attribute_id || attr.tempId;

// 修改后
const id = attr.id || attr.attribute_id || attr.tempId;
```

### 修复2: 统一 `flattenAllAttrs` 中子属性的 Name 获取

**文件**: `frontend/html/index.html`
**位置**: 第3303行附近

**修改**:
```javascript
// 修改前
name: attr.attribute_name || attr.name,

// 修改后（保持不变，已经是兼容的）
name: attr.attribute_name || attr.name,
```

### 修复3: 确保 `topLevelFromCurrent` 子属性映射正确

**文件**: `frontend/html/index.html`
**位置**: 第3257-3262行附近

**修改**:
```javascript
// 确保子属性的 tempId 和 attribute_name 正确映射
children: (attr.children || []).map(c => ({
    tempId: String(c.id || c.attribute_id),
    attribute_name: c.attribute_name || c.name,
    is_required: false,
    ...c  // 保留原始数据
})),
```

### 修复4: 在 `loadCategoryChildrenRecursively` 中转换子属性格式

**文件**: `frontend/html/index.html`
**位置**: 第3215-3229行附近

**修改**: 在加载子属性后，转换字段名为前端统一的格式

```javascript
async function loadCategoryChildrenRecursively(attrs) {
    for (let attr of attrs) {
        const attrId = attr.id || attr.attribute_id;
        if (attrId) {
            const childResult = await api(`/attributes/${attrId}/children`);
            if (childResult.success && childResult.data && childResult.data.length > 0) {
                // 转换子属性格式：id → attribute_id, name → attribute_name
                attr.children = childResult.data.map(c => ({
                    ...c,
                    attribute_id: c.id,
                    attribute_name: c.name,
                    tempId: String(c.id)
                }));
                // 递归获取子属性的子属性
                await loadCategoryChildrenRecursively(attr.children);
            } else {
                attr.children = [];
            }
        }
    }
}
```

## 统一代码逻辑计划

为了确保添加和编辑使用同一套渲染逻辑，需要：

1. **统一数据结构**: `topLevelFromCurrent` 和 `topLevelFromNew` 应该产生相同格式的数据
2. **统一字段名**: 所有属性都使用 `id`, `name`, `parent_id` 作为核心字段
3. **在数据加载时转换**: 在 `loadCategoryChildrenRecursively` 返回后就转换为统一格式

## 验证步骤

1. 添加类别 → 添加属性值 → 保存 → 关闭
2. 再次编辑同一类别 → 确认属性值显示正确
3. 测试添加新的属性值 → 确认显示正常
4. 测试编辑属性值名称 → 确认编辑功能正常
5. 测试删除属性值 → 确认删除功能正常
6. 测试折叠/展开 → 确认状态保持正确

## 清理无用代码

修复完成后，检查并清理：
1. `renderCategoryCurrentAttrs` 中可能存在的重复字段映射逻辑
2. 确认 `AttrHelper.renderAttrNode` 能正确处理所有情况
3. 检查是否有未使用的辅助函数
