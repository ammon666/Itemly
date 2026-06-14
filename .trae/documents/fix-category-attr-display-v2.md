# 修复计划：类别配置时属性值不显示

## 问题描述
- 添加类别时能正常显示属性值
- 编辑类别时只显示顶级属性，不显示属性值（子属性）

## 问题根源

后端 `get_with_attributes` 已经返回了完整的嵌套属性树（包含 `children`），但前端 `loadCategoryChildrenRecursively` 使用错误的 ID 调用 API 覆盖了 `children` 数组。

### 数据结构分析

后端返回的顶级属性对象：
```javascript
{
    attribute_id: 5,        // ✓ 正确的 attributes.id
    attribute_name: "颜色",
    parent_id: null,
    children: [             // ✓ 已有完整的子属性树
        { attribute_id: 6, attribute_name: "红色", parent_id: 5, children: [] }
    ]
}
```

### 问题代码 (line 3217)

```javascript
const attrId = attr.id || attr.attribute_id;
// attr.id = template_attributes.id (如: 25)
// attr.attribute_id = attributes.id (如: 5)
```

- `attr.id` 是 `template_attributes.id`（模板属性中间表的主键）
- `attr.attribute_id` 才是 `attributes.id`（真正的属性ID）

调用 `/attributes/25/children` 时，查询的是 `parent_id = 25`，但子属性的 `parent_id` 实际是 `5`，所以返回空数组，覆盖了原有的 `children`。

## 修复方案

### 方案A（推荐）：信任后端数据，跳过不必要的API调用

**理由**：后端 `get_with_attributes` 已经递归返回了完整的属性树，前端不需要再次加载。

**修改**：在 `loadCategoryChildrenRecursively` 中，如果属性已经有 `children` 数据（来自后端），则跳过 API 调用。

**文件**: `frontend/html/index.html`
**位置**: 第3215-3235行

```javascript
async function loadCategoryChildrenRecursively(attrs) {
    for (let attr of attrs) {
        const attrId = attr.attribute_id;  // 使用正确的 attributes.id
        if (attrId) {
            // 如果后端已经返回了 children 数据（完整树），直接信任，不再重复加载
            if (attr.children && attr.children.length > 0) {
                // 后端已返回子属性，递归确保子属性的子属性格式正确
                for (let child of attr.children) {
                    if (child.children && child.children.length > 0) {
                        await loadCategoryChildrenRecursively([child]);
                    }
                }
                continue;
            }
            // 只有在没有 children 数据时才调用 API
            const childResult = await api(`/attributes/${attrId}/children`);
            if (childResult.success && childResult.data && childResult.data.length > 0) {
                // 转换子属性格式为前端统一格式
                attr.children = childResult.data.map(c => ({
                    ...c,
                    attribute_id: c.id,
                    attribute_name: c.name,
                    tempId: String(c.id)
                }));
                await loadCategoryChildrenRecursively(attr.children);
            } else {
                attr.children = [];
            }
        }
    }
}
```

### 方案B：直接信任后端数据，不做额外加载

**修改**：删除 `loadCategoryChildrenRecursively` 调用，因为后端已返回完整数据。

**文件**: `frontend/html/index.html`
**位置**: 第3237-3247行 `loadCategoryCurrentAttrs` 函数

```javascript
async function loadCategoryCurrentAttrs(categoryId) {
    const result = await api(`/categories/${categoryId}/template`);

    if (result.success && result.data && result.data.attributes) {
        window.categoryCurrentAttrs = result.data.attributes;
        window.categoryTopLevelOrder = window.categoryCurrentAttrs.map(attr => getCategoryAttrKey(attr));
        // 不再需要 loadCategoryChildrenRecursively，因为后端已返回完整属性树
        // await loadCategoryChildrenRecursively(window.categoryCurrentAttrs);
    }

    renderCategoryCurrentAttrs();
}
```

## 推荐方案

选择**方案A**，因为：
1. 保留了 `loadCategoryChildrenRecursively` 的容错能力
2. 如果后端数据有问题，还能通过 API 补充
3. 风险更小

## 验证步骤

1. 启动后端服务
2. 添加新类别 → 添加属性值（如"颜色"） → 添加属性值选项（如"红色"、"蓝色"） → 保存
3. 关闭模态框
4. 再次编辑同一类别
5. 确认属性值（"红色"、"蓝色"）正确显示在"颜色"下方
6. 测试添加新的属性值
7. 测试编辑属性值名称
8. 测试删除属性值

## 清理

修复完成后，如果验证通过，可以考虑删除 `loadCategoryChildrenRecursively` 函数（如果确认后端总是返回完整数据）。但为了保险起见，可以保留。
