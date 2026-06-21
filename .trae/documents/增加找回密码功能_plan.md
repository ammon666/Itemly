# 计划：增加"找回密码 + 首次登录强制改密码/补全邮箱"功能

- 状态: 待执行
- 负责人: Trae
- 范围: 后端（models/routes/validators）+ 前端（index.html）
- 数据库影响: 有，需对 `users` 表做列迁移（添加 email、password_changed、initialized 列）
- 破坏现有登录行为: 是。首次登录 admin 账号后会被强制"修改用户名+密码+补充邮箱"，完成初始化后才能正常使用。

---

## 一、需求复盘（与原文对齐）

1. 首次登录（默认管理员 `admin` 账号，密码 `admin123`）：必须修改用户名+密码，同时补充邮箱地址，完成后才能进入应用。
2. 邮箱地址做简单校验（格式校验）。
3. 未登录时，登录页提供"忘记密码"按钮。
4. 点击忘记密码：输入邮箱，仅验证它与首次登录时保存的邮箱是否一致。
5. 邮箱一致则允许修改密码。
6. 连续输错 3 次，锁定 1 小时，期间不允许再尝试找回密码。

---

## 二、后端改动

### 2.1 数据库模型（`backend/models.py`）

- 目标表：`users`
- 需要新增列（都设置为 NOT NULL DEFAULT ...，兼容已有数据）：
  - `email TEXT DEFAULT ''`
  - `password_changed INTEGER DEFAULT 0`
  - `initialized INTEGER DEFAULT 0`
- 迁移策略：新增 `_migrate_users_columns(cursor)`，用 `PRAGMA table_info(users)` 判断是否已有列，缺失的用 `ALTER TABLE users ADD COLUMN ...` 补上。在 `init_db()` 里调用迁移方法。

- `UserModel` 新增/修改方法：
  1. `find_by_email(email)`：按邮箱查找（大小写不敏感比较，但存储原始值）。返回 dict / None。
  2. `update_email(user_id, email)`：更新邮箱（事务提交）。
  3. `first_time_setup(user_id, username, password, email)`：原子地更新用户名、生成新密码哈希、写入邮箱，同时把 `password_changed=1`、`initialized=1`。要求 username 不能是 "admin"。
  4. `check_initialization(user_id)`：返回 `{password_changed, initialized, email_is_set}` 等状态。

- 初始化管理员创建保持与现有逻辑一致，但 `password_changed`、`initialized` 默认是 0（让它进入首次登录引导流程）。

### 2.2 参数校验（`backend/utils/validators.py`）

- 新增 `require_email(value)`：使用标准 email 正则（`^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`）；失败时抛 `ValueError('邮箱格式不正确')`。

### 2.3 认证路由（`backend/routes/auth.py`）

1. `POST /api/auth/login`（调整）：登录成功后，在 `data` 中加入 `password_changed`、`email_is_set`、`need_first_setup`。

2. `POST /api/auth/first-setup`（新增）：
   - Body：`{ username, password, confirm_password, email }`
   - 必须已登录（使用 `@login_required`）。
   - 校验用户名/密码/邮箱格式，且 `username.lower() != 'admin'`。
   - 调用 `UserModel.first_time_setup`。

3. `POST /api/auth/password/recover/request`（新增）：
   - Body：`{ username, email }`
   - 不登录即可调用。
   - 内存 dict `_recover_failure[(ip, username)] = (fail_count, lock_until_ts)`。连续 3 次输错邮箱则锁定 1 小时。
   - 验证通过后生成一个 10 分钟有效的 token，返回给前端。

4. `POST /api/auth/password/recover/reset`（新增）：
   - Body：`{ token, new_password, confirm_password }`
   - 校验 token 存在且未过期。
   - 更新用户 password_hash，作废该 token。

5. `GET /api/auth/check`：同步返回 `need_first_setup` 字段。

### 2.4 应用入口（`backend/app.py`）

- 无新增代码，路由会自动生效。

---

## 三、前端改动（`frontend/html/index.html`）

### 3.1 UI 改动

1. 登录页 `#loginPage` 的表单底部增加一个"忘记密码"链接。
2. 新增模态框 `#forgotPasswordModal`：
   - 步骤 1：输入用户名+邮箱；
   - 步骤 2：输入新密码+确认；
   - 显示锁定/失败次数/剩余秒数。
3. 新增模态框 `#firstSetupModal`：首次登录成功后若 `need_first_setup=true`，自动弹出，`data-bs-backdrop="static"`。
4. 设置页增加"当前邮箱"只读展示。

### 3.2 JS 改动

- `login(e)`：成功后若 `result.data.need_first_setup` 为 true，则显示 `#firstSetupModal`。
- `checkAuth()`：同样处理 `need_first_setup`。
- 新增 `showForgotPassword()`：打开 `#forgotPasswordModal`。
- 新增 `forgotPasswordModal` 步骤 1、步骤 2 的提交处理函数，调用对应后端接口。
- 新增 `firstSetupModal` 提交处理，提交成功后进入应用。

---

## 四、接口契约（摘要）

| 路由 | 说明 |
|---|---|
| `POST /api/auth/login` | 返回 `need_first_setup / password_changed / email_is_set` |
| `POST /api/auth/first-setup` | 已登录用户完成初始化（用户名/密码/邮箱） |
| `POST /api/auth/password/recover/request` | 校验用户名与邮箱匹配，匹配成功下发 token，连续失败 3 次锁定 1 小时 |
| `POST /api/auth/password/recover/reset` | 使用 token 重置密码 |
| `GET /api/auth/check` | 返回登录态与 `need_first_setup` 标记 |

---

## 五、文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `backend/models.py` | 修改 | 新增 users 表列迁移；新增 `find_by_email / update_email / first_time_setup / check_initialization` |
| `backend/utils/validators.py` | 修改 | 新增 `require_email` 正则校验 |
| `backend/routes/auth.py` | 修改 | 新增 3 个路由；login 响应加入 `need_first_setup`；引入内存锁定+token dict |
| `frontend/html/index.html` | 修改 | 登录页加"忘记密码"链接；新增两个模态框；新增处理找回密码/初始化的 JS |

---

## 六、潜在风险与处理

1. 进程内内存存储的限制：锁定计数和 token 只存在 Python 进程内存中；多 worker/重启会不同步。当前需求足够简单，先采用内存实现，后续可替换为 SQLite 表或 Redis。
2. SQLite ALTER TABLE 限制：本次新增的三列都是普通列，无 UNIQUE 约束，不需要重建表。
3. 邮箱大小写问题：采用"不区分大小写比较、按原始值存储"。
4. 暴力破解：登录已有 5 次失败锁定机制；找回密码单独使用更严格的 3 次+1 小时锁定策略。

---

## 七、验证清单（自测项）

- [ ] 启动后端后，`users` 表自动新增 `email`、`password_changed`、`initialized` 三列。
- [ ] 使用 admin/admin123 登录后，前端自动弹出"首次登录初始化"模态框。
- [ ] 初始化时填用户名=admin 会被服务端拒绝；弱密码/邮箱格式错误也被拒绝。
- [ ] 初始化成功后，下一次登录不再弹框。
- [ ] 未登录状态下点"忘记密码"：可以弹出模态框并输入用户名+邮箱。
- [ ] 输入错误邮箱累计 3 次，被服务端锁定 1 小时，前端展示剩余秒数。
- [ ] 输入正确邮箱后可获取 token，然后设置新密码，随后用新密码可登录。
- [ ] token 超过 10 分钟后使用会被服务端拒绝。
- [ ] 原有设置页的 `/auth/password`、`/auth/account` 修改用户名/密码功能正常。
- [ ] 页面整体样式与原主题色、圆角、间距保持一致。
