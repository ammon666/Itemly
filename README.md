# Itemly

轻量化物品管理系统

一个简洁、高效的个人物品管理解决方案，类似于简化版的 HomeBox。

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

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/yourusername/itemly.git
cd itemly

# 启动容器
docker-compose up -d

# 访问系统
open http://localhost:5000
```

### 方式二：本地开发

```bash
# 克隆项目
git clone https://github.com/yourusername/itemly.git
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
open http://localhost:5000
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
| FLASK_SECRET | Flask 密钥 | random |
| FLASK_DEBUG | 调试模式 | false |
| PORT | 监听端口 | 5000 |

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

## 安全建议

1. 首次使用请立即修改默认密码
2. 在生产环境中设置强密码的 `FLASK_SECRET`
3. 定期备份数据库文件 `itemly.db`
4. 定期备份上传文件目录 `uploads/`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！