# Itemly

轻量化物品管理系统

一个简洁、高效的个人物品管理解决方案。

本程序均使用 AI 生成。

## 功能特性

- **物品管理**：查看、编辑、删除、批量操作
- **多层级类别管理**：支持树形结构的分类体系
- **多层级属性管理**：支持树形结构的属性体系，可在添加类别时直接配置
- **智能模板配置**：添加类别时直接定义属性，顶级属性自动设为必填项
- **智能筛选**：支持按分类、属性、关键词筛选物品
- **模糊搜索**：支持搜索物品名称、类别名称、属性值
- **图片上传**：前端自动压缩，不损失清晰度
- **图片放大**：点击图片可放大查看，支持点击关闭
- **统计面板**：实时查看物品数量统计
- **响应式设计**：完美适配桌面和移动设备
- **Docker 部署**：开箱即用

## 技术栈

- **前端**：Bootstrap 5 + 原生 JavaScript + browser-image-compression
- **后端**：Python Flask
- **数据库**：SQLite
- **部署**：Docker + Docker Compose

## 快速开始

### 方式一：Docker 部署（推荐，无需克隆整个项目）

镜像托管在 GitHub Container Registry（ghcr.io），通过 `IMAGE_TAG` 环境变量指定要拉取的标签：

```bash
# Linux / macOS
IMAGE_TAG=latest docker compose up -d

# Windows PowerShell
$env:IMAGE_TAG = "latest"; docker compose up -d
```

> **支持的镜像标签**：
> - `latest`：默认分支（main）最新构建（main 分支推送后才会生成），**docker-compose.yml 留空时默认使用**
> - `sha-xxxxxxx`：具体提交对应的镜像（如 `sha-e57f3bc`，始终可用，用于固定到特定版本）
> - `v*`：发布标签（如 `v1.0.0`）
>
> **支持的平台架构**：`linux/amd64`、`linux/arm64`（兼容常见 x86_64 主机与 ARM 类 NAS）

启动后访问：

```
http://localhost:9009
```

如果想从零开始拉取并启动：

```bash
# 1. 拉取镜像（也可跳过，docker compose 会自动拉取）
docker pull ghcr.io/ammon666/itemly:latest

# 2. 只需要一个 docker-compose.yml，内容见仓库根目录
docker compose up -d
```

> ⚠️ **构建自己的镜像时**：Dockerfile 会同时复制 `backend/` 和 `frontend/` 两个目录，请务必保持仓库结构完整，否则前端页面会变成「前端页面未部署」提示页。

### 方式二：克隆项目后部署

```bash
# 克隆项目
git clone https://github.com/ammon666/itemly.git
cd itemly

# 启动容器（通过 IMAGE_TAG 指定镜像标签，留空默认 latest）
IMAGE_TAG=latest docker compose up -d

# 访问系统
open http://localhost:9009
```

### 方式三：本地开发

```bash
# 克隆项目
git clone https://github.com/ammon666/itemly.git
cd itemly

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
cd backend
pip install -r requirements.txt

# 启动服务
python app.py

# 访问系统
open http://localhost:9009
```

## 默认账号

- 用户名：`admin`
- 密码：`admin123`

**首次登录后请立即修改密码！**

## 项目结构

```
Itemly/
├── backend/              # 后端代码
│   ├── app.py            # Flask 应用入口
│   ├── models.py         # 数据库模型
│   ├── routes/           # API 路由
│   │   ├── auth.py       # 认证相关
│   │   ├── items.py      # 物品管理
│   │   ├── categories.py # 类别管理
│   │   ├── attributes.py # 属性管理
│   │   └── stats.py      # 统计
│   └── utils/            # 工具函数
│       ├── auth_utils.py # 认证工具
│       └── file_utils.py # 文件工具
├── frontend/             # 前端代码
│   └── html/             # HTML 页面
│       └── index.html    # 单页应用
├── uploads/              # 上传文件目录
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile            # Docker 镜像配置
└── README.md             # 项目说明
```

## API 接口

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/logout | 用户登出 |
| GET | /api/auth/check | 检查登录状态 |
| PUT | /api/auth/password | 修改密码 |
| PUT | /api/auth/account | 修改用户名 |

### 物品

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/items | 获取物品列表（支持筛选和分页） |
| GET | /api/items/:id | 获取物品详情 |
| POST | /api/items | 创建物品 |
| PUT | /api/items/:id | 更新物品 |
| DELETE | /api/items/:id | 删除物品 |
| POST | /api/items/batch-delete | 批量删除 |
| POST | /api/items/batch-update-attributes | 批量更新属性 |

### 类别

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/categories | 获取类别列表 |
| POST | /api/categories | 创建类别（支持同时配置属性） |
| PUT | /api/categories/:id | 更新类别 |
| DELETE | /api/categories/:id | 删除类别（物品自动转移到未分类） |
| GET | /api/categories/:id/template | 获取类别模板配置 |
| PUT | /api/categories/:id/template | 更新类别模板配置 |

### 属性

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/attributes | 获取属性列表（树形结构） |
| POST | /api/attributes | 创建属性 |
| PUT | /api/attributes/:id | 更新属性 |
| DELETE | /api/attributes/:id | 删除属性（无引用时直接删除） |
| DELETE | /api/attributes/:id/force-delete | 强制删除属性（有引用时使用） |
| GET | /api/attributes/:id/check-reference | 检查属性引用情况 |

### 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/stats | 获取统计数据 |

### 上传

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload | 上传图片 |
| GET | /api/upload/:filename | 获取图片 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| FLASK_SECRET | Flask 密钥（敏感信息，需运行时注入） | 未设置时使用随机值 |
| FLASK_DEBUG | 调试模式 | false |
| PORT | 监听端口 | 9009 |
| ITEMLY_DB_PATH | 数据库文件路径 | /data/itemly.db |
| ITEMLY_UPLOAD_DIR | 上传文件目录 | /data/uploads |

## 数据存储

- 数据库：`itemly.db`（SQLite 单文件）
- 上传文件：`uploads/` 目录

## 类别管理功能

### 添加类别

类别管理页面采用左右两栏布局：
- **左侧**：已有类别列表，支持配置和删除操作
- **右侧**：添加类别表单

添加类别流程：
1. 输入类别名称
2. 点击"添加顶级属性"按钮添加属性
3. 点击属性右侧的 **+** 号添加子属性（支持多级）
4. 点击铅笔图标编辑属性名称
5. 点击垃圾桶图标删除属性
6. 点击"保存类别"完成创建

**注意**：
- 顶级属性自动设为该类别的必填项
- 添加物品时需填写所有必填属性
- 同一属性只能选择一个值（多级属性中选一个）

### 编辑类别

点击类别列表中的"配置"按钮可编辑类别：
- 修改类别名称
- 添加/删除/编辑属性
- 设置属性是否必填
- 删除被引用的属性时会弹出警告提示

### 删除类别

删除类别时：
- 该类别下的所有物品自动转移到"未分类"
- "未分类"类别在添加物品时不可见不可选
- 物品数据不会丢失

## 移动端适配

系统采用移动端优先设计理念：
- 响应式布局，适配各种屏幕尺寸
- 优化的触摸操作体验
- 悬浮式添加按钮，方便快捷
- 侧边栏筛选面板，节省空间

## 图片处理

系统使用 `browser-image-compression` 库在前端自动压缩图片：
- 最大尺寸：1024px
- 最大文件大小：1MB
- 支持格式：JPEG、PNG、GIF、WebP
- 保持图片清晰度

## 界面功能

### 首页
- 物品卡片展示（图片、名称、备注、分类、属性）
- 点击分类/属性标签可快速筛选
- 搜索框支持模糊搜索（名称、类别、属性值）
- 悬浮添加按钮

### 物品管理
- 统计面板（物品数、分类数、属性数）
- 筛选侧边栏（分类、属性）
- 筛选条件显示
- 批量编辑属性功能

### 类别管理
- 左右两栏布局（已有类别 + 添加类别）
- 添加类别时直接配置属性
- 支持多级属性添加
- 顶级属性自动设为必填项
- 删除类别时物品转移到未分类

### 属性管理
- 树形结构展示
- 支持多层级属性
- 删除属性时检查引用情况
- 被引用属性需确认后才能删除

### 设置
- 用户名修改
- 密码修改

## 部署排查 / 常见问题

部署完以后如果遇到问题，可按以下顺序核对：

### 1. 容器日志里看到 `SyntaxError: source code string cannot contain null bytes`

这是 `backend/__init__.py` 文件被编辑器保存成了带 BOM 的异常编码导致的。仓库中的文件已经被修复为纯 UTF-8 空文件。如果你是 fork 出来维护自己的版本，请确保该文件是 **0 字节的纯空文件 / 不含 BOM**，并重新构建镜像推送到 ghcr.io。

```bash
# 本地验证（Linux / macOS）：应该输出 nothing
file backend/__init__.py        # 期望：empty
hexdump -C backend/__init__.py  # 期望：无任何输出或仅换行

# Windows PowerShell 验证：长度应为 0 或仅 LF
(Get-Item backend\__init__.py).Length
```

修复后重新推送：

```bash
git add backend/__init__.py
git commit -m "Fix: sanitize backend/__init__.py encoding"
git push
# 等 CI 构建完成后，docker compose pull && docker compose up -d
```

### 2. 浏览器打开显示 `{"message":"请求的资源不存在","success":false}`

这说明后端正常启动了，但前端 `frontend/html/index.html` 没有被打进镜像。请检查 Dockerfile，确认有以下两行：

```dockerfile
COPY backend/ ./backend/
COPY frontend/ ./frontend/
```

如果缺失，请补齐后重新构建镜像。

### 3. 浏览器打开后显示「前端页面未部署」提示页

同上，这是 `backend/app.py` 为了避免用户永远看到 JSON 404 而增加的兜底页。遇到时按第 2 条处理即可。

### 4. `docker compose up -d` 提示镜像不存在 / 未授权

- 确认你的 `IMAGE_TAG` 拼写正确（如 `latest`、`sha-xxxxxxx`）
- 访问 [ghcr.io/ammon666/itemly](https://ghcr.io/ammon666/itemly) 查看当前可用标签

### 5. 升级到最新镜像的标准步骤

```bash
cd itemly
docker compose down
docker compose pull
docker compose up -d
docker compose logs -f --tail=50
```

数据保存在命名卷 `itemly_data` 中，重建容器 **不会** 丢失。

## 安全建议

1. 首次使用请立即修改默认密码
2. 在生产环境中设置强密码的 `FLASK_SECRET`
3. 定期备份数据库文件 `itemly.db`
4. 定期备份上传文件目录 `uploads/`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！