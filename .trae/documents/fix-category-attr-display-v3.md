# 修复计划：类别配置中属性值不显示

## 问题描述
- 编辑类别时，只显示顶级属性，不显示属性值（子属性）
- 新添加的属性值也不显示

## 根本原因

在 `topLevelFromNew` 中构建顶级属性时，没有显式设置 `id` 字段：

```javascript
const topLevelFromNew = window.categoryNewAttrs.filter(a => !a.parent_id).map(attr => ({
    tempId: attr.tempId,
    attribute_name: attr.name,
    is_required: attr.is_required,
    children: [],
    _children: ...
    // 缺少 id: attr.tempId
}));
```

然后在 `flattenAllAttrs` 中：
```javascript
const id = attr.id || attr.attribute_id || attr.tempId;
```

如果 `attr.id` 是 `undefined`，会回退到 `attr.attribute_id` 或 `attr.tempId`。但关键问题在于 `getCategoryAttrKey` 的优先级是 `tempId || attribute_id || id`，如果 `tempId` 本身有问题，可能返回意外值。

## 修复方案

### 修复1: 在 `topLevelFromNew` 中显式设置 `id` 字段

**文件**: `frontend/html/index.html`
**位置**: 第3279-3289行

**修改内容**：
```javascript
const topLevelFromNew = window.categoryNewAttrs.filter(a => !a.parent_id).map(attr => ({
    id: attr.tempId,  // 显式设置 id
    tempId: attr.tempId,
    attribute_name: attr.name,
    is_required: attr.is_required,
    children: [],
    _children: collectNewChildren(attr.tempId)
}));
```

### 修复2: 修复孙属性收集逻辑

**问题**：`collectNewChildren` 只收集直接子属性，不递归处理孙属性。

**修改内容**：让 `collectNewChildren` 递归处理孙属性：

```javascript
// 递归收集某个属性的所有新子属性
function collectNewChildren(parentTempId) {
    const directChildren = window.categoryNewAttrs
        .filter(c => String(c.parent_id) === String(parentTempId));
    return directChildren.map(c => ({
        ...c,
        id: c.tempId,
        tempId: c.tempId,
        attribute_name: c.name,
        _children: collectNewChildren(c.tempId)  // 递归收集孙属性
    }));
}
```

### 修复3: 统一 `flattenAllAttrs` 中 `_children` 的处理

**问题**：当前 `_children` 处理不递归，导致孙属性丢失。

**修改内容**：
```javascript
function flattenAllAttrs(attrList, parentId = null) {
    if (!attrList) return [];
    let result = [];
    for (const attr of attrList) {
        const id = attr.id || attr.attribute_id || attr.tempId;
        result.push({
            id: id,
            name: attr.attribute_name || attr.name,
            parent_id: parentId,
            is_required: attr.is_required
        });
        // 处理已有属性的子属性（children）
        if (attr.children && attr.children.length > 0) {
            result = result.concat(flattenAllAttrs(attr.children, id));
        }
        // 处理新添加的子属性（_children）- 递归调用
        if (attr._children && attr._children.length > 0) {
            result = result.concat(flattenAllAttrs(attr._children, id));
        }
    }
    return result;
}
```

## 验证步骤

1. 启动后端服务
2. 添加新类别
3. 添加顶级属性"颜色"
4. 添加子属性"红色" → 确认"红色"显示在"颜色"下方
5. 添加孙属性（如支持多层级）"深红" → 确认"深红"显示在"红色"下方
6. 关闭模态框
7. 编辑该类别
8. 确认所有属性值正确显示

## 清理

1. 删除 `.trae/documents` 目录下的所有修复文档（v1, v2, v3）
2. 保留 `ARCHITECTURE-PLAN.md`
