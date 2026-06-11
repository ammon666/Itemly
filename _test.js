const API_BASE = '/api';
let currentUser = null;
let categories = [];
let attributes = [];
let items = [];
let currentItemId = null;
let currentTemplateId = null;
let currentItemImages = [];
let keepAdding = false;
let selectedItemIds = [];
let searchDebounceTimer = null;
let viewMode = 'card';
let editMode = false;

const homeFilter = { categories: [], attributes: [], keyword: '' };
const itemsFilter = { categories: [], attributes: [], keyword: '' };
let activeFilter = homeFilter;

function stringHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return Math.abs(hash);
}

async function api(endpoint, options = {}) {
    try {
        const config = { headers: { 'Content-Type': 'application/json' }, credentials: 'include', ...options };
        if (config.body && typeof config.body === 'object') config.body = JSON.stringify(config.body);
        const response = await fetch(API_BASE + endpoint, config);
        let data;
        try { data = await response.json(); } catch (e) { return { success: false, message: '服务器返回数据格式错误' }; }
        return data;
    } catch (error) {
        console.error('API请求失败:', endpoint, error);
        return { success: false, message: '网络请求失败，请检查服务器连接' };
    }
}

function showToast(msg, type = 'default') {
    const w = document.getElementById('toastWrap'), el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="t-dot"></span>${msg}`;
    w.appendChild(el);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('show')));
    setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 2500);
}

function showLoading() { document.getElementById('loadingOverlay').style.display = 'flex'; }
function hideLoading() { document.getElementById('loadingOverlay').style.display = 'none'; }

async function checkAuth() {
    try {
        const result = await api('/auth/check');
        if (result.authenticated) {
            currentUser = result.data;
            showApp();
            loadAllData();
            updateNavUser(currentUser);
        } else {
            showLogin();
        }
    } catch (error) {
        console.error('检查登录状态失败:', error);
        showLogin();
    }
}

function showLogin() {
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('appContainer').classList.remove('active');
}

function showApp() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('appContainer').classList.add('active');
}

function updateNavUser(user) {
    if (!user) return;
    const avatarText = document.querySelector('#navAvatar .nav-avatar-text');
    if (avatarText) avatarText.textContent = (user.username || 'A').charAt(0).toUpperCase();
    document.getElementById('navAvatar').title = '点击登出: ' + user.username;
    document.getElementById('navUsername').textContent = user.username;
}

async function login(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    showLoading();
    const result = await api('/auth/login', { method: 'POST', body: { username, password } });
    hideLoading();
    if (result.success) {
        currentUser = result.data;
        showApp();
        loadAllData();
        updateNavUser(currentUser);
        document.getElementById('loginForm').reset();
    } else showToast(result.message, 'error');
}

async function logout() {
    await api('/auth/logout', { method: 'POST' });
    currentUser = null;
    showLogin();
    showToast('已退出登录', 'success');
}

function setViewMode(mode) {
    viewMode = mode;
    document.getElementById('viewCardBtn').classList.toggle('active', mode === 'card');
    document.getElementById('viewListBtn').classList.toggle('active', mode === 'list');
    document.getElementById('homeItemsGrid').style.display = mode === 'card' ? 'grid' : 'none';
    document.getElementById('homeItemsList').style.display = mode === 'list' ? 'flex' : 'none';
    loadItems();
}

function toggleEditMode() {
    editMode = !editMode;
    const main = document.querySelector('.main');
    const btn = document.getElementById('editModeBtn');
    const batchBtn = document.getElementById('batchEditBtn');
    
    if (editMode) {
        main.classList.add('edit-mode');
        btn.innerHTML = '<svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.8"><path d="M6 18L18 6M6 6l12 12"/></svg><span>退出编辑</span>';
        btn.style.background = 'var(--danger)';
        if (viewMode === 'list') {
            batchBtn.style.display = 'inline-flex';
        }
        showToast('已进入编辑模式');
    } else {
        main.classList.remove('edit-mode');
        btn.innerHTML = '<svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg><span>进入编辑</span>';
        btn.style.background = '';
        batchBtn.style.display = 'none';
        selectedItemIds = [];
        updateBatchEditButton();
        loadItems();
        showToast('已退出编辑模式');
    }
}

async function loadAllData() {
    showLoading();
    try {
        await Promise.all([loadCategories(), loadAttributes(), loadItems()]);
    } catch (error) {
        console.error('加载数据失败:', error);
        showToast('部分数据加载失败', 'warning');
    } finally { hideLoading(); }
}

async function loadCategories() {
    try {
        const result = await api('/categories');
        if (result.success) {
            categories = result.data || [];
            renderCategorySelectors();
            renderSidebarCategories();
            renderFilterCategories();
            const catPage = document.getElementById('pageCategories');
            if (catPage && catPage.style.display !== 'none') renderCategoryList();
        } else categories = [];
    } catch (error) { console.error('加载类别失败:', error); categories = []; }
}

async function loadAttributes() {
    try {
        const result = await api('/attributes?flat=true');
        if (result.success) {
            attributes = result.data || [];
            renderAttributeSelectors();
            const attrPage = document.getElementById('pageAttributes');
            if (attrPage && attrPage.style.display !== 'none') renderAttributeTree();
            renderSidebarAttributes();
        } else attributes = [];
    } catch (error) { console.error('加载属性失败:', error); attributes = []; }
}

async function loadItems(filter) {
    const f = filter || activeFilter || homeFilter;
    try {
        const params = new URLSearchParams();
        if (f.categories && f.categories.length) params.append('category_ids', f.categories.join(','));
        if (f.keyword) params.append('keyword', f.keyword);
        if (f.attributes && f.attributes.length) params.append('attribute_ids', f.attributes.join(','));
        const result = await api('/items?' + params.toString());
        if (result.success) {
            items = result.data || [];
            renderItems();
            updateHomeStats();
            const itemsPage = document.getElementById('pageItems');
            if (itemsPage && itemsPage.style.display !== 'none') {
                renderItemsManagement();
                updateItemsStats();
            }
        } else items = [];
    } catch (error) { console.error('加载物品失败:', error); items = []; }
}

function updateHomeStats() {
    const total = items.length;
    const uniqueCats = new Set(items.map(i => i.category_id).filter(Boolean)).size;
    const uniqueAttrs = new Set(items.flatMap(i => (i.attributes || []).map(a => a.attribute_id))).size;
    document.getElementById('homeStatsTotal').textContent = total;
    document.getElementById('homeStatsCategories').textContent = uniqueCats;
    document.getElementById('homeStatsAttributes').textContent = uniqueAttrs;
}

function updateStats(page) {
    const total = items.length;
    const uniqueCats = new Set(items.map(i => i.category_id).filter(Boolean)).size;
    const uniqueAttrs = new Set(items.flatMap(i => (i.attributes || []).map(a => a.attribute_id))).size;
    document.getElementById(`${page}StatsTotal`).textContent = total;
    document.getElementById(`${page}StatsCategories`).textContent = uniqueCats;
    document.getElementById(`${page}StatsAttributes`).textContent = uniqueAttrs;
}

let sortBy = 'name';
let sortOrder = 'asc';

function toggleSort() {
    sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    loadItems();
    showToast(`已按名称${sortOrder === 'asc' ? '升序' : '降序'}排序`);
}

function updateFilterChips() {
    const container = document.getElementById('homeFilterChips');
    if (!container) return;
    const chips = [];
    if (activeFilter.categories.length) {
        activeFilter.categories.forEach(catId => {
            const cat = categories.find(c => c.id === catId);
            if (cat) chips.push(`<div class="chip">${cat.name}<span class="chip-x" onclick="event.stopPropagation();toggleCategoryFilter(${catId})">✕</span></div>`);
        });
    }
    if (activeFilter.attributes.length) {
        activeFilter.attributes.forEach(attrId => {
            const attr = attributes.find(a => a.id === attrId);
            if (attr) chips.push(`<div class="chip">${attr.name}<span class="chip-x" onclick="event.stopPropagation();toggleAttributeFilter(${attrId})">✕</span></div>`);
        });
    }
    if (activeFilter.keyword) {
        chips.push(`<div class="chip">"${activeFilter.keyword}"<span class="chip-x" onclick="event.stopPropagation();removeKeywordFilter()">✕</span></div>`);
    }
    container.innerHTML = chips.join('');
}

function toggleAttributeFilter(attrId) {
    const f = activeFilter;
    const idx = f.attributes.indexOf(attrId);
    if (idx >= 0) f.attributes.splice(idx, 1);
    else f.attributes.push(attrId);
    loadItems(f);
    updateFilterChips();
}

function clearAllFilters() {
    activeFilter.categories = [];
    activeFilter.attributes = [];
    activeFilter.keyword = '';
    renderSidebarCategories();
    renderFilterCategories();
    renderFilterAttributes();
    const searchInput = document.getElementById('navSearchInput');
    if (searchInput) searchInput.value = '';
    loadItems(activeFilter);
    updateFilterChips();
}

function renderSidebarCategories() {
    const container = document.getElementById('sidebarCategories');
    if (!container) return;
    if (categories.length === 0) {
        container.innerHTML = '<div class="tree-row" style="opacity:0.5;cursor:default;">暂无类别</div>';
        return;
    }
    const catColors = ['#6366F1','#22C55E','#F59E0B','#EF4444','#8B5CF6','#EC4899','#14B8A6','#F97316'];
    let html = `<div class="tree-row ${!homeFilter.categories.length ? 'active' : ''}" onclick="clearHomeCategoryFilter()"><span class="tree-dot"></span>全部</div>`;
    html += categories.map(c => {
        const isSelected = homeFilter.categories.includes(c.id);
        const colorIdx = stringHash(c.name) % 8;
        return `<div class="tree-row ${isSelected ? 'active' : ''}" onclick="toggleHomeCategoryFilter(${c.id})"><span class="tree-dot" style="background:${catColors[colorIdx]}"></span>${c.name}</div>`;
    }).join('');
    container.innerHTML = html;
}

function renderSidebarAttributes() {
    // 侧边栏属性树由 filterOffcanvas 中的 tree-selector 负责
    renderFilterAttributes();
}

function renderFilterCategories() {
    const container = document.getElementById('filterCategories');
    if (!container) return;
    if (categories.length === 0) {
        container.innerHTML = '<div class="tree-row" style="opacity:0.5;cursor:default;">暂无类别</div>';
        return;
    }
    const catColors = ['#6366F1','#22C55E','#F59E0B','#EF4444','#8B5CF6','#EC4899','#14B8A6','#F97316'];
    let html = `<div class="tree-row ${!homeFilter.categories.length ? 'selected' : ''}" onclick="clearHomeCategoryFilter()"><span class="tree-dot"></span>全部类别</div>`;
    html += categories.map(c => {
        const isSelected = homeFilter.categories.includes(c.id);
        const colorIdx = stringHash(c.name) % 8;
        return `<div class="tree-row ${isSelected ? 'selected' : ''}" onclick="toggleHomeCategoryFilter(${c.id})"><span class="tree-dot" style="background:${catColors[colorIdx]}"></span>${c.name}</div>`;
    }).join('');
    container.innerHTML = html;
}

function renderFilterAttributes() {
    const container = document.getElementById('filterAttributes');
    if (!container) return;
    const attrTree = buildTree(attributes);
    if (attrTree.length === 0) {
        container.innerHTML = '<div class="tree-row" style="opacity:0.5;cursor:default;"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="var(--muted)" stroke-width="2" style="vertical-align:middle;margin-right:4px;"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>暂无属性</div>';
        return;
    }
    container.innerHTML = renderAttrTreeForFilter(attrTree, 0);
}

function renderAttrTreeForFilter(nodes, level) {
    return nodes.map(n => {
        const isSelected = homeFilter.attributes.includes(n.id);
        const hasChildren = n.children && n.children.length > 0;
        const isExpanded = expandedAttrIds.includes(n.id);
        return `
        <div>
            <div class="tree-row ${isSelected ? 'selected' : ''}" data-row-id="row-${n.id}" style="padding-left:${24 + level * 16}px">
                <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="var(--sub)" stroke-width="2" style="margin-right:6px;flex-shrink:0;cursor:pointer;" onclick="event.stopPropagation();toggleAttrTreeRow(this.parentElement)">${hasChildren ? (isExpanded ? '<path d="M6 9l6 6 6-6"/>' : '<path d="M12 5l-6 6 6 6"/>') : ''}</svg>
                <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="${isSelected ? 'var(--accent)' : 'var(--sub)'}" stroke-width="2" style="margin-right:6px;flex-shrink:0;"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
                <span style="flex:1;">${n.name}</span>
                <input type="checkbox" ${isSelected ? 'checked' : ''} onchange="event.stopPropagation();toggleHomeAttributeFilter(${n.id})" style="width:16px;height:16px;">
            </div>
            ${hasChildren ? `<div class="tree-children" data-parent="row-${n.id}" style="display:${isExpanded ? 'block' : 'none'};">${renderAttrTreeForFilter(n.children, level + 1)}</div>` : ''}
        </div>
        `;
    }).join('');
}

function toggleHomeAttributeFilter(attrId) {
    const idx = homeFilter.attributes.indexOf(attrId);
    if (idx >= 0) homeFilter.attributes.splice(idx, 1);
    else homeFilter.attributes.push(attrId);
    renderFilterAttributes();
    loadItems(homeFilter);
    updateFilterChips();
}

function clearHomeAttributeFilter() {
    homeFilter.attributes = [];
    renderFilterAttributes();
    loadItems(homeFilter);
    updateFilterChips();
}

async function batchUpdateAttrs(action) {
    const selectedAttrIds = Array.from(document.querySelectorAll('#batchAttrSelector .tree-row.selected')).map(el => parseInt(el.dataset.attrId));
    if (selectedAttrIds.length === 0) { showToast('请选择属性', 'error'); return; }
    if (selectedItemIds.length === 0) { showToast('请选择物品', 'error'); return; }
    showLoading();
    const result = await api('/items/batch-attributes', {
        method: 'POST',
        body: { item_ids: selectedItemIds, attribute_ids: selectedAttrIds, action }
    });
    hideLoading();
    if (result.success) {
        showToast(`已${action === 'add' ? '添加' : '移除'}属性`, 'success');
        bootstrap.Modal.getInstance(document.getElementById('batchEditModal')).hide();
        loadItems();
    } else showToast(result.message, 'error');
}

function showBatchEditModal() {
    if (selectedItemIds.length === 0) { showToast('请先选择物品', 'error'); return; }
    document.getElementById('batchEditInfo').textContent = `已选择 ${selectedItemIds.length} 个物品`;
    const container = document.getElementById('batchAttrSelector');
    const attrTree = buildTree(attributes);
    if (attrTree.length === 0) {
        container.innerHTML = '<div class="tree-row" style="opacity:0.5;cursor:default;"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="var(--muted)" stroke-width="2" style="vertical-align:middle;margin-right:4px;"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>暂无属性</div>';
    } else {
        container.innerHTML = attrTree.map(n => `<div class="tree-row" data-attr-id="${n.id}" onclick="this.classList.toggle(&quot;selected&quot;)"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="var(--sub)" stroke-width="2" style="vertical-align:middle;margin-right:4px;"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>${n.name}</div>`).join('');
    }
    new bootstrap.Modal(document.getElementById('batchEditModal')).show();
}

function renderCategorySelectors() {
    document.getElementById('templateSelect').innerHTML = '<option value="">请选择类别</option>' +
        categories.map(c => `<option value="${c.template_id}" data-category-id="${c.id}">${c.name}</option>`).join('');
}

function renderAttributeSelectors() {
    const attrOptions = attributes.map(a => `<option value="${a.id}">${a.display_name}</option>`).join('');
    document.getElementById('attributeParentSelect').innerHTML = '<option value="">无（顶级属性）</option>' + attrOptions;
}

function renderItems() {
    const grid = document.getElementById('homeItemsGrid');
    const list = document.getElementById('homeItemsList');
    const empty = document.getElementById('homeEmptyState');
    if (items.length === 0) { 
        grid.innerHTML = ''; 
        list.innerHTML = ''; 
        if (empty) empty.style.display = 'grid'; 
        return; 
    }
    if (empty) empty.style.display = 'none';
    
    if (viewMode === 'card') {
        grid.innerHTML = items.map((item, i) => {
            const isSelected = editMode && selectedItemIds.includes(item.id);
            const attrTags = (item.attributes && item.attributes.length)
                ? item.attributes.slice(0, 2).map(a => `<span class="tag tag-attr">${a.attribute_name}</span>`).join('')
                : '';
            const moreCount = item.attributes ? item.attributes.length - 2 : 0;
            const showCheckbox = editMode;
            return `
            <div class="card" style="animation-delay:${i * 0.04}s" onclick="showItemDetailModal(${item.id})">
                ${showCheckbox ? `<div style="position:absolute;top:8px;left:8px;z-index:10;">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} style="width:18px;height:18px;border-radius:4px;cursor:pointer;" onchange="event.stopPropagation();toggleItemSelection(${item.id},this)">
                </div>` : ''}
                <div class="card-img" onclick="event.stopPropagation();openLB('/uploads/${item.images}',event)">
                    <img src="/uploads/${item.images}" alt="${item.name}" onerror="handleImgError(this)">
                    ${editMode ? `<div class="card-overlay">
                        <button class="ov-btn" title="编辑" onclick="event.stopPropagation();editItem(${item.id})">
                            <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </button>
                        <button class="ov-btn del" title="删除" onclick="event.stopPropagation();deleteItem(${item.id})">
                            <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
                        </button>
                    </div>` : ''}
                </div>
                <div class="card-body">
                    <div class="card-name">${item.name}</div>
                    <div class="card-note">${item.remark || ''}</div>
                    <div class="card-tags">
                        <span class="tag tag-cat">${item.category_name || '未分类'}</span>
                        ${attrTags}
                        ${moreCount > 0 ? `<span class="tag tag-more">+${moreCount}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
        }).join('');
        list.innerHTML = '';
    } else {
        grid.innerHTML = '';
        updateListView();
    }
    updateFilterChips();
    updateBatchEditButton();
}

function updateListView() {
    if (viewMode !== 'list') return;
    const list = document.getElementById('homeItemsList');
    list.innerHTML = items.map((item, i) => {
        const isSelected = editMode && selectedItemIds.includes(item.id);
        const attrTags = (item.attributes && item.attributes.length)
            ? item.attributes.slice(0, 3).map(a => a.attribute_name).join(', ')
            : '';
        return `
        <div class="list-item ${isSelected ? 'selected' : ''}" onclick="editMode ? void(0) : showItemDetailModal(${item.id})">
            ${editMode ? `<input type="checkbox" class="list-checkbox" ${isSelected ? 'checked' : ''} onchange="toggleItemSelection(${item.id},this)">` : ''}
            <img src="/uploads/${item.images}" alt="${item.name}" class="list-img" onerror="this.src='data:image/svg+xml,%3Csvg width=%2264%22 height=%2264%22 fill=%22none%22 viewBox=%220%200%2024%2024%22 stroke=%22%239CA3AF%22 stroke-width=%221.5%22%3E%3Cpath d=%22M20%207H4a2%202%200%200%200-2%202v10a2%202%200%200%200%202%202h16a2%202%200%200%200%202-2V9a2%202%200%200%200-2-2Z%22/%3E%3Cpath d=%22M16%207V5a2%202%200%200%200-2-2h-4a2%202%200%200%200-2%202v2%22/%3E%3C/svg%3E'">
            <div class="list-info">
                <div class="list-name">${item.name}</div>
                <div class="list-meta">
                    <span>${item.category_name || '未分类'}</span>
                    ${attrTags ? `<span>${attrTags}</span>` : ''}
                </div>
            </div>
            ${editMode ? `<div class="list-actions">
                <button class="ov-btn" title="编辑" onclick="editItem(${item.id})">
                    <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="ov-btn del" title="删除" onclick="deleteItem(${item.id})">
                    <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
                </button>
            </div>` : ''}
        </div>
        `;
    }).join('');
}

function toggleItemSelection(itemId, checkbox) {
    if (checkbox.checked) {
        if (!selectedItemIds.includes(itemId)) selectedItemIds.push(itemId);
    } else {
        const idx = selectedItemIds.indexOf(itemId);
        if (idx >= 0) selectedItemIds.splice(idx, 1);
    }
    updateBatchEditButton();
}

function updateBatchEditButton() {
    const btn = document.getElementById('batchEditBtn');
    if (btn) {
        btn.style.display = selectedItemIds.length > 0 ? 'inline-flex' : 'none';
        btn.innerHTML = `<svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.8"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg><span>批量编辑 (${selectedItemIds.length})</span>`;
    }
}

function renderItemsManagement() {
    const grid = document.getElementById('itemsManagementGrid');
    const empty = document.getElementById('itemsEmptyState');
    if (items.length === 0) { grid.innerHTML = ''; if (empty) empty.style.display = 'grid'; return; }
    if (empty) empty.style.display = 'none';
    grid.innerHTML = items.map((item, i) => {
        const attrTags = (item.attributes && item.attributes.length)
            ? item.attributes.slice(0, 2).map(a => `<span class="tag tag-attr">${a.attribute_name}</span>`).join('')
            : '';
        const moreCount = item.attributes ? item.attributes.length - 2 : 0;
        return `
        <div class="card" style="animation-delay:${i * 0.04}s" onclick="showItemDetailModal(${item.id})">
            <div class="card-img" onclick="event.stopPropagation();openLB('/uploads/${item.images}',event)">
                <img src="/uploads/${item.images}" alt="${item.name}" onerror="handleImgError(this)">
            </div>
            <div class="card-body">
                <div class="card-name">${item.name}</div>
                <div class="card-note">${item.remark || ''}</div>
                <div class="card-tags">
                    <span class="tag tag-cat">${item.category_name || '未分类'}</span>
                    ${attrTags}
                    ${moreCount > 0 ? `<span class="tag tag-more">+${moreCount}</span>` : ''}
                </div>
            </div>
        </div>
        `;
    }).join('');
    updateFilterChips();
}

function renderCategoryList() {
    const list = document.getElementById('categoryList');
    if (categories.length === 0) {
        list.innerHTML = `<div class="empty"><div class="empty-icon"><svg width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path d="M4 6h16M4 12h16M4 18h7"/></svg></div><div class="empty-title">暂无类别</div></div>`;
        return;
    }
    list.innerHTML = categories.map(c => {
        const hasTemplate = c.template_id && c.template_name;
        return `
        <div class="admin-card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
                <div style="font-weight:600;font-size:14px;display:flex;align-items:center;gap:6px;">
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="var(--accent)" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h7"/></svg>
                    ${c.name}
                </div>
                <div style="display:flex;gap:6px;">
                    ${hasTemplate ? `<button class="btn-primary" style="height:28px;font-size:11px;" onclick="showAddItemModalForCategory(${c.id},${c.template_id || 'null'})">+ 添加物品</button>` : ''}
                    <button class="btn-primary" style="height:28px;font-size:11px;background:var(--surface);color:var(--sub);" onclick="showTemplateConfigModal(${c.id})">配置</button>
                    <button class="btn btn-outline-danger" style="height:28px;font-size:11px;" onclick="deleteCategory(${c.id})">删除</button>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

let expandedAttrIds = [];

function renderAttributeTree() {
    const tree = document.getElementById('attributeTree');
    const attrTree = buildTree(attributes);
    if (attrTree.length === 0) { tree.innerHTML = '<div style="color:var(--muted);font-size:12px;text-align:center;padding:20px;display:flex;align-items:center;justify-content:center;gap:6px;"><svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>暂无属性</div>'; return; }
    tree.innerHTML = renderTreeNodes(attrTree, 'handleAttributeAction', 0);
    expandedAttrIds.forEach(id => {
        const row = document.querySelector(`[data-row-id="row-${id}"]`);
        if (row) {
            const children = row.parentElement.querySelector(':scope > .tree-children');
            if (children) children.style.display = 'block';
        }
    });
}

function toggleAttrTreeRow(el) {
    const rowId = el.getAttribute('data-row-id');
    const itemId = rowId ? parseInt(rowId.replace('row-', '')) : null;
    const children = el.parentElement.querySelector(':scope > .tree-children');
    if (!children) return;
    const isExpanded = children.style.display !== 'none';
    children.style.display = isExpanded ? 'none' : 'block';
    if (itemId) {
        const idx = expandedAttrIds.indexOf(itemId);
        if (isExpanded) { if (idx >= 0) expandedAttrIds.splice(idx, 1); }
        else { if (idx < 0) expandedAttrIds.push(itemId); }
    }
}

function buildTree(flatList) {
    const map = {};
    const roots = [];
    flatList.forEach(a => { map[a.id] = { ...a, children: [] }; });
    flatList.forEach(a => { if (a.parent_id && map[a.parent_id]) map[a.parent_id].children.push(map[a.id]); else roots.push(map[a.id]); });
    return roots;
}

function renderTreeNodes(nodes, actionHandler, level = 0, rootIndex = 0) {
    return nodes.map((n, idx) => {
        const rootIdx = level === 0 ? idx : rootIndex;
        const altClass = level === 0 && rootIdx % 2 === 1 ? ' style="background:var(--surface)"' : '';
        return `
        <div>
            <div class="tree-row" onclick="toggleAttrTreeRow(this)" data-row-id="row-${n.id}"${altClass} style="cursor:pointer;padding-left:${24 + level * 16}px">
                <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="var(--sub)" stroke-width="2" style="margin-right:6px;flex-shrink:0;">${n.children.length ? (expandedAttrIds.includes(n.id) ? '<path d="M6 9l6 6 6-6"/>' : '<path d="M12 5l-6 6 6 6"/>') : ''}</svg>
                <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="var(--accent)" stroke-width="2" style="margin-right:6px;flex-shrink:0;"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
                <span style="font-weight:${level === 0 ? 600 : 400}">${n.name}</span>
                <div style="margin-left:auto;display:flex;gap:4px;">
                    <button class="btn-xs" onclick="event.stopPropagation();${actionHandler}(${n.id},'edit')"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                    <button class="btn-xs" onclick="event.stopPropagation();${actionHandler}(${n.id},'add')"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></button>
                    <button class="btn-xs btn-danger" onclick="event.stopPropagation();${actionHandler}(${n.id},'delete')"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg></button>
                </div>
            </div>
            ${n.children.length ? `<div class="tree-children" data-parent="row-${n.id}" style="display:${expandedAttrIds.includes(n.id) ? 'block' : 'none'};">${renderTreeNodes(n.children, actionHandler, level + 1, rootIdx)}</div>` : ''}
        </div>
        `;
    }).join('');
}

function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    document.querySelectorAll('.sb-item').forEach(m => m.classList.remove('active'));
    const pageEl = document.getElementById('page' + page.charAt(0).toUpperCase() + page.slice(1));
    if (pageEl) pageEl.style.display = 'block';
    const menuItem = document.querySelector(`.sb-item[data-page="${page}"]`);
    if (menuItem) menuItem.classList.add('active');
    const fabBtn = document.getElementById('fabButton');
    if (fabBtn) fabBtn.style.display = page === 'home' ? 'flex' : 'none';
    if (page !== 'home') {
        homeFilter.categories = []; homeFilter.attributes = []; homeFilter.keyword = '';
        const homeSearch = document.getElementById('navSearchInput');
        if (homeSearch) homeSearch.value = '';
    }
    activeFilter = homeFilter;
    if (page === 'categories') renderCategoryList();
    else if (page === 'attributes') renderAttributeTree();
    else if (page === 'home') { renderCategorySelectors(); loadItems(homeFilter); updateFilterChips(); }
    else if (page === 'settings') {
        if (currentUser) document.getElementById('settingsUsername').value = currentUser.username || '';
    }
    closeSidebar();
}

function showAddItemModal() {
    currentItemId = null; currentItemImages = []; currentTemplateId = null; keepAdding = false;
    document.getElementById('itemModalTitle').textContent = '添加物品';
    document.getElementById('itemForm').reset();
    document.getElementById('imageUploadZone').innerHTML = `<svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="var(--muted)" stroke-width="1.5"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2 1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg><p style="color:var(--muted);font-size:12px;margin-top:8px;">点击上传图片</p>`;
    document.getElementById('imageUploadZone').classList.remove('has-image');
    document.getElementById('templateSelect').value = '';
    document.getElementById('attributeSelector').innerHTML = '<p style="color:var(--muted);font-size:12px;text-align:center;padding:20px;">请先选择类别模板</p>';
    document.getElementById('saveAndContinueBtn').style.display = 'inline-flex';
    new bootstrap.Modal(document.getElementById('itemModal')).show();
}

function showAddItemModalForCategory(categoryId, templateId) {
    currentItemId = null; currentItemImages = []; currentTemplateId = templateId; keepAdding = false;
    document.getElementById('itemModalTitle').textContent = '添加物品';
    document.getElementById('itemForm').reset();
    document.getElementById('imageUploadZone').innerHTML = `<svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="var(--muted)" stroke-width="1.5"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2 1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg><p style="color:var(--muted);font-size:12px;margin-top:8px;">点击上传图片</p>`;
    document.getElementById('imageUploadZone').classList.remove('has-image');
    document.getElementById('templateSelect').value = templateId;
    loadTemplateAttributes();
    document.getElementById('saveAndContinueBtn').style.display = 'inline-flex';
    new bootstrap.Modal(document.getElementById('itemModal')).show();
}

async function loadTemplateAttributes() {
    const templateId = document.getElementById('templateSelect').value;
    if (!templateId) { document.getElementById('attributeSelector').innerHTML = '<p style="color:var(--muted);font-size:12px;text-align:center;padding:20px;">请先选择类别模板</p>'; return; }
    currentTemplateId = templateId;
    showLoading();
    const categoryOption = document.getElementById('templateSelect').selectedOptions[0];
    const categoryId = categoryOption.dataset.categoryId;
    const result = await api(`/categories/${categoryId}/template`);
    hideLoading();
    if (result.success && result.data.attributes) {
        const attrs = result.data.attributes;
        const container = document.getElementById('attributeSelector');
        const grouped = {};
        attrs.forEach(a => {
            const groupName = a.category_name || '未分类';
            if (!grouped[groupName]) grouped[groupName] = [];
            grouped[groupName].push(a);
        });
        container.innerHTML = Object.entries(grouped).map(([catName, items]) => `
            <div class="attr-group">
                <div class="attr-group-header">${catName}</div>
                <div class="attr-group-items show">
                    ${items.map(a => `<div class="attr-item" data-attr-id="${a.id}" onclick="toggleAttrSelection(this,${a.id})">${a.name || a.attribute_name || '未命名'}${a.is_required ? ' <span style="color:var(--danger)">*</span>' : ''}</div>`).join('')}
                </div>
            </div>
        `).join('');
    }
}

let selectedAttrIds = [];
function toggleAttrSelection(el, attrId) {
    el.classList.toggle('selected');
    const idx = selectedAttrIds.indexOf(attrId);
    if (idx >= 0) selectedAttrIds.splice(idx, 1);
    else selectedAttrIds.push(attrId);
}

async function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    try {
        const options = { maxSizeMB: 1, maxWidthOrHeight: 1200 };
        const compressedFile = await imageCompression(file, options);
        const formData = new FormData();
        formData.append('file', compressedFile);
        showLoading();
        const result = await api('/upload', { method: 'POST', body: formData });
        hideLoading();
        if (result.success) {
            currentItemImages = [result.filename];
            const zone = document.getElementById('imageUploadZone');
            zone.innerHTML = `<img src="/uploads/${result.filename}" alt="预览">`;
            zone.classList.add('has-image');
        } else showToast(result.message || '上传失败', 'error');
    } catch (error) { hideLoading(); console.error('图片处理失败:', error); showToast('图片处理失败', 'error'); }
}

async function saveItem() {
    const name = document.querySelector('#itemForm input[name="name"]').value.trim();
    const remark = document.querySelector('#itemForm textarea[name="remark"]').value.trim();
    if (!name) { showToast('请输入物品名称', 'error'); return false; }
    if (!currentItemImages.length) { showToast('请上传图片', 'error'); return false; }
    const templateId = document.getElementById('templateSelect').value;
    if (!templateId) { showToast('请选择类别', 'error'); return false; }
    showLoading();
    const body = { name, remark, template_id: templateId, images: currentItemImages[0], attribute_ids: selectedAttrIds };
    let result;
    if (currentItemId) result = await api(`/items/${currentItemId}`, { method: 'PUT', body });
    else result = await api('/items', { method: 'POST', body });
    hideLoading();
    if (result.success) {
        showToast(currentItemId ? '物品已更新' : '物品已添加', 'success');
        bootstrap.Modal.getInstance(document.getElementById('itemModal')).hide();
        loadItems();
    } else showToast(result.message, 'error');
    return result.success;
}

async function saveItemAndContinue() {
    keepAdding = true;
    if (await saveItem()) {
        selectedAttrIds = [];
        currentItemImages = [];
        document.getElementById('itemForm').reset();
        document.getElementById('imageUploadZone').innerHTML = `<svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="var(--muted)" stroke-width="1.5"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2 1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg><p style="color:var(--muted);font-size:12px;margin-top:8px;">点击上传图片</p>`;
        document.getElementById('imageUploadZone').classList.remove('has-image');
        selectedAttrIds = [];
        loadTemplateAttributes();
    }
    keepAdding = false;
}

function editItem(itemId) {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    currentItemId = itemId;
    currentItemImages = item.images ? [item.images] : [];
    currentTemplateId = item.template_id;
    selectedAttrIds = (item.attributes || []).map(a => a.attribute_id);
    document.getElementById('itemModalTitle').textContent = '编辑物品';
    document.querySelector('#itemForm input[name="name"]').value = item.name;
    document.querySelector('#itemForm textarea[name="remark"]').value = item.remark || '';
    document.getElementById('templateSelect').value = item.template_id || '';
    if (item.images) {
        const zone = document.getElementById('imageUploadZone');
        zone.innerHTML = `<img src="/uploads/${item.images}" alt="预览">`;
        zone.classList.add('has-image');
    }
    loadTemplateAttributes();
    document.getElementById('saveAndContinueBtn').style.display = 'none';
    new bootstrap.Modal(document.getElementById('itemModal')).show();
}

async function deleteItem(itemId) {
    if (!confirm('确定要删除这个物品吗？')) return;
    showLoading();
    const result = await api(`/items/${itemId}`, { method: 'DELETE' });
    hideLoading();
    if (result.success) { showToast('物品已删除', 'success'); loadItems(); }
    else showToast(result.message, 'error');
}

function showItemDetailModal(itemId) {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    currentItemId = itemId;
    document.getElementById('itemDetailTitle').textContent = item.name;
    document.getElementById('itemDetailBody').innerHTML = `
        <img src="/uploads/${item.images}" class="img-fluid rounded mb-3" style="max-height:250px;object-fit:cover;cursor:zoom-in;" onclick="openLB('/uploads/${item.images}',event)" onerror="this.style.display='none'">
        <p style="margin-bottom:8px;"><strong style="color:var(--ink);">类别：</strong><span style="color:var(--sub);">${item.category_name || '未分类'}</span></p>
        ${item.attributes && item.attributes.length ? `<p style="margin-bottom:8px;"><strong style="color:var(--ink);">属性：</strong><span style="color:var(--sub);">${item.attributes.map(a => a.attribute_name).join(', ')}</span></p>` : ''}
        ${item.remark ? `<p style="margin-bottom:8px;"><strong style="color:var(--ink);">备注：</strong><span style="color:var(--sub);">${item.remark}</span></p>` : ''}
        <p style="color:var(--muted);font-size:11.5px;margin-top:12px;">创建时间：${new Date(item.created_at).toLocaleString()}</p>
    `;
    new bootstrap.Modal(document.getElementById('itemDetailModal')).show();
}

function editCurrentItem() {
    bootstrap.Modal.getInstance(document.getElementById('itemDetailModal')).hide();
    editItem(currentItemId);
}

async function deleteCurrentItem() {
    if (!confirm('确定要删除这个物品吗？')) return;
    showLoading();
    const result = await api(`/items/${currentItemId}`, { method: 'DELETE' });
    hideLoading();
    if (result.success) {
        showToast('物品已删除', 'success');
        bootstrap.Modal.getInstance(document.getElementById('itemDetailModal')).hide();
        loadItems();
    } else showToast(result.message, 'error');
}

function handleImgError(img) {
    img.parentElement.innerHTML = '<div class="card-img-ph"><svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2Z"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg></div>';
}

function openLB(src, e) {
    if (e) e.stopPropagation();
    document.getElementById('lbImg').src = src;
    document.getElementById('lightbox').classList.add('open');
    document.body.style.overflow = 'hidden';
}
function closeLB(e) {
    if (e) e.stopPropagation();
    document.getElementById('lightbox').classList.remove('open');
    document.body.style.overflow = '';
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLB(); });

function showCategoryModal(id = null, name = '') {
    document.getElementById('categoryForm').reset();
    document.getElementById('categoryModalTitle').textContent = id ? '编辑类别' : '添加类别';
    if (id) document.querySelector('#categoryForm input[name="id"]').value = id;
    if (name) document.querySelector('#categoryForm input[name="name"]').value = name;
    new bootstrap.Modal(document.getElementById('categoryModal')).show();
}

function showTemplateConfigModal(categoryId) {
    const cat = categories.find(c => c.id === categoryId);
    if (!cat) return;
    document.getElementById('templateCategoryId').value = categoryId;
    document.getElementById('templateCategoryName').value = cat.name;
    loadTemplateConfigAttributes(categoryId);
    new bootstrap.Modal(document.getElementById('templateModal')).show();
}

async function loadTemplateConfigAttributes(categoryId) {
    showLoading();
    const result = await api(`/categories/${categoryId}/template`);
    hideLoading();
    if (result.success) {
        const container = document.getElementById('templateAttributeSelector');
        const existing = result.data.attributes || [];
        const grouped = {};
        attributes.forEach(a => {
            if (!grouped[a.category_name]) grouped[a.category_name] = [];
            grouped[a.category_name].push(a);
        });
        container.innerHTML = Object.entries(grouped).map(([catName, attrs]) => {
            const selectedInTemplate = existing.filter(e => e.attribute_id === attrs[0]?.attribute_id);
            const isInTemplate = selectedInTemplate.length > 0;
            const isRequired = selectedInTemplate[0]?.is_required || false;
            return `
            <div class="attr-group">
                <div class="attr-group-header">${catName}</div>
                <div class="attr-group-items show">
                    ${attrs.map(a => {
                        const isSel = existing.some(e => e.attribute_id === a.id);
                        const req = existing.find(e => e.attribute_id === a.id)?.is_required || false;
                        return `<div class="attr-item ${isSel ? 'selected' : ''}" data-attr-id="${a.id}">
                            <input type="checkbox" ${isSel ? 'checked' : ''} style="margin-right:6px;" onchange="this.parentElement.classList.toggle(&quot;selected&quot;,this.checked)">
                            ${a.name}
                            <input type="checkbox" ${req ? 'checked' : ''} style="margin-left:8px;" onchange="this.checked = this.checked">必填
                        </div>`;
                    }).join('')}
                </div>
            </div>`;
        }).join('');
    }
}

async function saveTemplateConfig() {
    const categoryId = document.getElementById('templateCategoryId').value;
    const name = document.getElementById('templateCategoryName').value.trim();
    if (!name) { showToast('请输入类别名称', 'error'); return; }
    const attrItems = document.querySelectorAll('#templateAttributeSelector .attr-item.selected');
    const attributes_config = Array.from(attrItems).map(el => ({
        attribute_id: parseInt(el.dataset.attrId),
        is_required: el.querySelector('input[type="checkbox"]:last-of-type')?.checked || false
    }));
    showLoading();
    const result = await api(`/categories/${categoryId}/template`, {
        method: 'PUT',
        body: { name, attributes: attributes_config }
    });
    hideLoading();
    if (result.success) {
        showToast('配置已保存', 'success');
        bootstrap.Modal.getInstance(document.getElementById('templateModal')).hide();
        loadCategories();
    } else showToast(result.message, 'error');
}

function showAttributeModal(id = null, parentId = null, name = '') {
    document.getElementById('attributeForm').reset();
    document.getElementById('attributeModalTitle').textContent = id ? '编辑属性' : '添加属性';
    if (id) document.querySelector('#attributeForm input[name="id"]').value = id;
    if (parentId) document.getElementById('attributeParentSelect').value = parentId;
    if (name) document.querySelector('#attributeForm input[name="name"]').value = name;
    new bootstrap.Modal(document.getElementById('attributeModal')).show();
}

function handleAttributeAction(id, action) {
    const attr = attributes.find(a => a.id === id);
    if (action === 'edit') showAttributeModal(id, attr?.parent_id, attr?.name);
    else if (action === 'add') showAttributeModal(null, id, '');
    else if (action === 'delete') {
        if (!confirm('确定要删除这个属性吗？')) return;
        api(`/attributes/${id}`, { method: 'DELETE' }).then(r => {
            if (r.success) { showToast('属性已删除', 'success'); loadAttributes(); }
            else showToast(r.message, 'error');
        });
    }
}

async function deleteCategory(id) {
    if (!confirm('确定要删除这个类别吗？')) return;
    showLoading();
    const result = await api(`/categories/${id}`, { method: 'DELETE' });
    hideLoading();
    if (result.success) { showToast('类别已删除', 'success'); loadCategories(); }
    else showToast(result.message, 'error');
}

function toggleHomeCategoryFilter(catId) {
    const idx = homeFilter.categories.indexOf(catId);
    if (idx >= 0) homeFilter.categories.splice(idx, 1);
    else homeFilter.categories.push(catId);
    renderSidebarCategories();
    renderFilterCategories();
    loadItems(homeFilter);
    updateFilterChips();
}

function clearHomeCategoryFilter() {
    homeFilter.categories = [];
    renderSidebarCategories();
    renderFilterCategories();
    loadItems(homeFilter);
    updateFilterChips();
}

function toggleItemsCategoryFilter(catId) {
    const idx = itemsFilter.categories.indexOf(catId);
    if (idx >= 0) itemsFilter.categories.splice(idx, 1);
    else itemsFilter.categories.push(catId);
    loadItems(itemsFilter);
    updateFilterChips();
}

function toggleCategoryFilter(catId) {
    const f = activeFilter;
    const idx = f.categories.indexOf(catId);
    if (idx >= 0) f.categories.splice(idx, 1);
    else f.categories.push(catId);
    if (f === homeFilter) renderSidebarCategories();
    loadItems(f);
    updateFilterChips();
}

function removeKeywordFilter() {
    activeFilter.keyword = '';
    const searchInput = document.getElementById('navSearchInput');
    if (searchInput) searchInput.value = '';
    loadItems(activeFilter);
    updateFilterChips();
}

function onSearchInput(value) {
    activeFilter.keyword = value.trim();
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        loadItems(activeFilter);
        updateFilterChips();
    }, 300);
}

document.getElementById('navSearchInput')?.addEventListener('input', function() { onSearchInput(this.value); });

document.getElementById('menuToggle').addEventListener('click', () => {
    const sb = document.getElementById('sidebar'), ov = document.getElementById('sbOverlay');
    const o = sb.classList.toggle('open');
    if (o) { ov.style.opacity = '1'; ov.style.pointerEvents = 'auto'; }
    else { ov.style.opacity = '0'; ov.style.pointerEvents = 'none'; }
});
function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    const ov = document.getElementById('sbOverlay');
    if (ov) { ov.style.opacity = '0'; ov.style.pointerEvents = 'none'; }
}

// 表单提交处理
document.getElementById('loginForm').addEventListener('submit', login);
document.getElementById('itemForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    await saveItem();
    if (!keepAdding) {
        bootstrap.Modal.getInstance(document.getElementById('itemModal')).hide();
    }
});
document.getElementById('categoryForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.querySelector('#categoryForm input[name="id"]').value;
    const name = document.querySelector('#categoryForm input[name="name"]').value.trim();
    showLoading();
    const result = id
        ? await api(`/categories/${id}`, { method: 'PUT', body: { name } })
        : await api('/categories', { method: 'POST', body: { name } });
    hideLoading();
    if (result.success) {
        showToast(id ? '类别已更新' : '类别已添加', 'success');
        bootstrap.Modal.getInstance(document.getElementById('categoryModal')).hide();
        loadCategories();
    } else showToast(result.message, 'error');
});
document.getElementById('attributeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.querySelector('#attributeForm input[name="id"]').value;
    const parentId = document.getElementById('attributeParentSelect').value;
    const name = document.querySelector('#attributeForm input[name="name"]').value.trim();
    showLoading();
    const result = id
        ? await api(`/attributes/${id}`, { method: 'PUT', body: { name, parent_id: parentId || null } })
        : await api('/attributes', { method: 'POST', body: { name, parent_id: parentId || null } });
    hideLoading();
    if (result.success) {
        showToast(id ? '属性已更新' : '属性已添加', 'success');
        bootstrap.Modal.getInstance(document.getElementById('attributeModal')).hide();
        loadAttributes();
    } else showToast(result.message, 'error');
});
document.getElementById('accountForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('settingsUsername').value.trim();
    showLoading();
    const result = await api('/auth/account', { method: 'PUT', body: { username } });
    hideLoading();
    if (result.success) {
        showToast('账号信息已更新', 'success');
        currentUser.username = username;
        updateNavUser(currentUser);
    } else showToast(result.message, 'error');
});
document.getElementById('passwordForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const newPassword = document.querySelector('#passwordForm input[name="new_password"]').value;
    const confirmPassword = document.querySelector('#passwordForm input[name="confirm_password"]').value;
    if (newPassword !== confirmPassword) { showToast('两次密码输入不一致', 'error'); return; }
    showLoading();
    const result = await api('/auth/password', { method: 'PUT', body: { new_password: newPassword, confirm_password: confirmPassword } });
    hideLoading();
    if (result.success) {
        showToast('密码已修改', 'success');
        document.getElementById('passwordForm').reset();
    } else showToast(result.message, 'error');
});

checkAuth();