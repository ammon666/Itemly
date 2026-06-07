# Itemly
轻量化物品管理系统

一个简洁、高效的个人物品管理解决方案，类似于简化版的 HomeBox。

## 功能特性

- 物品管理：查看、编辑、删除、批量操作
- 多层级类别管理
- 多层级标签管理
- 物品模板：支持自定义字段
- 图片上传：前端自动压缩，不损失清晰度
- 统计面板：实时查看物品数量统计
- 响应式设计：完美适配桌面和移动设备
- Docker 部署：开箱即用

## 技术栈

- 前端：Bootstrap 5 + 原生 JavaScript + browser-image-compression
- 后端：Python Flask
- 数据库：SQLite
- 部署：Docker + Docker Compose

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
│   │   ├── categories.py  # 类别管理
│   │   ├── tags.py       # 标签管理
│   │   ├── templates.py  # 模板管理
│   │   └── stats.py      # 统计
│   └── utils/            # 工具函数
├── frontend/             # 前端代码
│   └── html/             # HTML 页面
├── uploads/              # 上传文件目录
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile            # Docker 镜像配置
└── README.md            # 项目说明
```

## API 接口

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/logout | 用户登出 |
| GET | /api/auth/check | 检查登录状态 |
| PUT | /api/auth/password | 修改密码 |
| PUT | /api/auth/profile | 修改个人信息 |

### 物品

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/items | 获取物品列表 |
| GET | /api/items/:id | 获取物品详情 |
| POST | /api/items | 创建物品 |
| PUT | /api/items/:id | 更新物品 |
| DELETE | /api/items/:id | 删除物品 |
| POST | /api/items/batch-delete | 批量删除 |
| POST | /api/items/batch-update | 批量更新 |

### 类别

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/categories | 获取类别列表 |
| POST | /api/categories | 创建类别 |
| PUT | /api/categories/:id | 更新类别 |
| DELETE | /api/categories/:id | 删除类别 |

### 标签

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tags | 获取标签列表 |
| POST | /api/tags | 创建标签 |
| PUT | /api/tags/:id | 更新标签 |
| DELETE | /api/tags/:id | 删除标签 |

### 模板

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/templates | 获取模板列表 |
| GET | /api/templates/:id | 获取模板详情 |
| POST | /api/templates | 创建模板 |
| PUT | /api/templates/:id | 更新模板 |
| DELETE | /api/templates/:id | 删除模板 |

### 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/stats | 获取统计数据 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| FLASK_SECRET | Flask 密钥 | random |
| FLASK_DEBUG | 调试模式 | false |
| PORT | 监听端口 | 5000 |

## 数据存储

- 数据库：`itemly.db`（SQLite 单文件）
- 上传文件：`uploads/` 目录

## 移动端适配

系统采用移动端优先设计理念：
- 响应式布局，适配各种屏幕尺寸
- 优化的触摸操作体验
- 悬浮式添加按钮，方便快捷
- 侧边栏可收起，节省空间

## 图片处理

系统使用 `browser-image-compression` 库在前端自动压缩图片：
- 最大尺寸：1024px
- 最大文件大小：1MB
- 支持格式：JPEG、PNG、GIF、WebP
- 保持图片清晰度

## 安全建议

1. 首次使用请立即修改默认密码
2. 在生产环境中设置强密码的 `FLASK_SECRET`
3. 定期备份数据库文件 `itemly.db`
4. 定期备份上传文件目录 `uploads/`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
