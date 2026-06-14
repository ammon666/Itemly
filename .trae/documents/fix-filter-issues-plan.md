# 筛选功能修复计划

## 需求分析

根据用户需求，需要修复以下筛选问题：

1. **筛选条件按照分类模板显示**：一个分类下面接着模板里的属性，默认全部展开
2. **多选筛选**：顶级属性不能被选中，点击顶级属性触发折叠/展开
3. **数据源唯一性**：筛选条件的分类和属性必须从已有分类模板同步，不额外创建表
4. **样式优化**：去掉属性值后面的复选框，选中时整行高亮并在后面增加对勾
5. **重置按钮状态**：当数据被筛选时，重置按钮显示为黄色

## 代码分析

### 当前架构

**前端文件**: `frontend/html/index.html`
- `renderFilterAttributes()` 函数负责渲染属性筛选（第1638行）
- `renderFilterCategories()` 函数负责渲染类别筛选（第1619行）
- 属性数据存储在 `attributes` 数组中
- 类别数据存储在 `categories` 数组中，每个类别包含 `attributes` 字段

**后端文件**: 
- `backend/routes/items.py`: 物品筛选接口
- `backend/routes/categories.py`: 类别管理接口（包含模板信息）
- `backend/models.py`: 数据库模型

### 当前问题

1. 筛选属性是从 `attributes` 数组直接获取，没有按分类模板组织
2. 属性选择使用复选框，样式不符合要求
3. 重置按钮没有根据筛选状态变化颜色

## 修复方案

### 1. 前端修改：按分类模板组织筛选条件

修改 `renderFilterAttributes()` 函数，改为按分类模板组织属性：

```javascript
function renderFilterAttributes() {
    const container = document.getElementById('filterAttributes');
    if (!container) return;
    
    // 按分类模板组织属性
    let html = '';
    categories.forEach(cat => {
        if (cat.name === '未分类' || !cat.attributes || cat.attributes.length === 0) return;
        
        html += `
            <div class="filter-category-group">
                <div class="filter-category-header">
                    ${cat.name}
                </div>
                <div class="filter-category-attrs">
                    ${renderAttrTreeForFilter(cat.attributes)}
                </div>
            </div>
        `;
    });
    
    if (!html) {
        html = '<p style="color:var(--muted);font-size:12px;text-align:center;">暂无属性</p>';
    }
    container.innerHTML = html;
}
```

### 2. 前端修改：属性选择样式优化

修改 `renderAttrTreeForFilter()` 函数：
- 去掉复选框
- 选中时整行高亮
- 添加对勾图标

```javascript
function renderAttrTreeForFilter(attrTree) {
    function renderNode(nodes, level = 0) {
        if (!nodes || nodes.length === 0) return '';
        
        const indent = level * 20;
        return nodes.map(n => {
            const hasChildren = n.children && n.children.length > 0;
            const isSelected = homeFilter.attributes.includes(n.id);
            const isTopLevel = level === 0;
            const canSelect = !isTopLevel;
            
            return `
                <div style="margin-bottom:2px;">
                    <div style="display:flex;align-items:center;gap:6px;padding:4px 8px;margin-left:${indent}px;background:${isSelected && canSelect ? 'var(--accent-bg)' : 'var(--white)'};border-radius:4px;border:1px solid ${isSelected && canSelect ? 'var(--accent)' : 'var(--border)'};cursor:pointer;" onclick="${hasChildren ? `toggleFilterAttrCollapse('filter_${n.id}')` : ''}${!hasChildren && canSelect ? `toggleHomeAttributeFilter(${n.id})` : ''}">
                        ${hasChildren ? `
                            <span class="collapse-arrow" style="color:var(--sub);display:inline-flex;align-items:center;">
                                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                            </span>
                        ` : '<span style="width:12px;"></span>'}
                        <span style="flex:1;font-size:13px;">
                            ${isTopLevel ? '<strong>' + n.name + '</strong>' : n.name}
                            ${isTopLevel ? '<span style="color:var(--accent);font-size:10px;margin-left:4px;">字段</span>' : ''}
                        </span>
                        ${isSelected && canSelect ? `
                            <svg width="14" height="14" fill="var(--accent)" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"/>
                            </svg>
                        ` : ''}
                    </div>
                    <div class="collapse-content">
                        ${renderNode(n.children, level + 1)}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    return renderNode(attrTree, 0);
}
```

### 3. 前端修改：重置按钮状态

修改 `updateFilterChips()` 函数，添加对重置按钮的状态更新：

```javascript
function updateFilterChips() {
    const container = document.getElementById('homeFilterChips');
    const resetBtn = document.querySelector('.sort-btn[onclick="clearAllFilters()"]');
    
    // 检查是否有筛选条件
    const hasFilters = activeFilter.categories.length > 0 || 
                       activeFilter.attributes.length > 0 || 
                       activeFilter.keyword;
    
    // 更新重置按钮样式
    if (resetBtn) {
        resetBtn.style.background = hasFilters ? '#F59E0B' : '';
        resetBtn.style.color = hasFilters ? '#fff' : '';
        resetBtn.style.borderColor = hasFilters ? '#F59E0B' : '';
    }
    
    // ... 原有逻辑
}
```

### 4. CSS样式补充

需要添加的CSS样式：

```css
/* 筛选分类组 */
.filter-category-group {
    margin-bottom: 12px;
    border: 1px solid var(--border);
    border-radius: 7px;
    overflow: hidden;
}

.filter-category-header {
    padding: 8px 12px;
    background: var(--surface);
    font-weight: 600;
    font-size: 13px;
    color: var(--ink);
    border-bottom: 1px solid var(--border);
}

.filter-category-attrs {
    padding: 6px;
}
```

## 实施步骤

| 序号 | 任务 | 文件 | 状态 |
|:---:|------|------|:---:|
| 1 | 添加CSS样式 | `frontend/html/index.html` | pending |
| 2 | 修改 `renderFilterAttributes()` 按分类组织 | `frontend/html/index.html` | pending |
| 3 | 修改 `renderAttrTreeForFilter()` 优化样式 | `frontend/html/index.html` | pending |
| 4 | 修改 `updateFilterChips()` 更新重置按钮状态 | `frontend/html/index.html` | pending |
| 5 | 测试验证 | - | pending |

## 依赖与风险

**依赖**：
- 前端已有 `categories` 数据包含 `attributes` 字段
- `loadCategories()` 函数已加载完整的类别和属性信息

**风险**：
- 如果某些类别没有模板或属性，需要处理空数据情况
- 需要确保 `homeFilter.attributes` 数组正确同步

## 测试验证

1. 进入首页，打开筛选侧边栏
2. 验证分类模板结构显示正确
3. 验证顶级属性不能选中，点击可折叠/展开
4. 验证二级及以下属性可选中，选中后整行高亮并显示对勾
5. 验证多选功能正常
6. 验证有筛选条件时重置按钮为黄色
7. 验证重置功能正常工作