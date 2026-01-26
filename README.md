# 智能生活服务工具 - 后端API

基于FastAPI的后端服务，提供AI驱动的餐饮营养分析、菜单识别、饮食记录管理和智能行程规划功能。

## ✨ 核心功能

- 🍽️ **餐饮服务**：菜品营养分析、菜单图片识别、饮食记录管理
- 🗺️ **行程规划**：AI生成个性化行程计划、行程管理
- 👤 **用户中心**：用户偏好设置、健康目标管理

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── database.py          # 数据库配置和连接
│   │
│   ├── models/              # API数据模型（Pydantic）
│   │   ├── __init__.py
│   │   ├── food.py          # 餐饮相关模型
│   │   ├── trip.py          # 行程相关模型
│   │   └── user.py          # 用户相关模型
│   │
│   ├── db_models/           # 数据库模型（SQLAlchemy）
│   │   ├── __init__.py
│   │   ├── user.py          # 用户表模型
│   │   ├── diet_record.py   # 饮食记录表模型
│   │   ├── menu_recognition.py  # 菜单识别记录模型
│   │   ├── trip_plan.py     # 行程计划表模型
│   │   └── trip_item.py     # 行程节点表模型
│   │
│   ├── routers/             # API路由
│   │   ├── __init__.py
│   │   ├── food.py          # 餐饮API路由
│   │   ├── trip.py          # 行程API路由
│   │   └── user.py          # 用户API路由
│   │
│   └── services/            # 业务服务
│       ├── __init__.py
│       └── ai_service.py    # AI服务封装（通义千问、豆包AI）
│
├── utils/                    # 工具脚本
│   ├── init_database.py     # 数据库初始化脚本
│   └── ...
│
├── test/                     # 测试脚本
│   ├── test_user_api.py
│   ├── test_menu_recognize.py
│   └── ...
│
├── docs/                     # 文档
│   ├── 快速开始.md
│   ├── API文档.md
│   ├── 项目说明.md
│   └── 数据库连接指南.md
│
├── requirements.txt          # Python依赖
├── env_example.txt           # 环境变量示例
├── start.bat                 # Windows启动脚本
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# Windows激活虚拟环境
venv\Scripts\activate

# Linux/Mac激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库

#### 安装MySQL

**Windows:**
- 下载：https://dev.mysql.com/downloads/mysql/
- 或使用XAMPP：https://www.apachefriends.org/

**macOS/Linux:**
```bash
# macOS
brew install mysql
brew services start mysql

# Linux (Ubuntu)
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

#### 创建数据库

```sql
CREATE DATABASE lifehub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 配置环境变量

复制 `env_example.txt` 为 `.env`：

```bash
# Windows
copy env_example.txt .env

# Linux/Mac
cp env_example.txt .env
```

编辑 `.env` 文件：

```env
# AI服务配置
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
VOLC_ACCESS_KEY=你的火山引擎AccessKey（可选）
VOLC_SECRET_KEY=你的火山引擎SecretKey（可选）

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_NAME=lifehub

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

**获取API Key：**
- **通义千问**：访问 https://dashscope.aliyuncs.com/ 获取
- **火山引擎豆包**：访问 https://console.volcengine.com/ 获取（可选）

### 4. 初始化数据库

```bash
python utils/init_database.py
```

### 5. 运行服务

```bash
# 方法1：使用uvicorn命令
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方法2：直接运行main.py
python -m app.main

# 方法3：使用启动脚本（Windows）
start.bat
```

服务启动后：
- **API文档**：http://localhost:8000/docs
- **交互式文档**：http://localhost:8000/redoc
- **健康检查**：http://localhost:8000/health

## Android连接说明

### 使用模拟器

如果使用Android模拟器，需要使用特殊IP地址：

```kotlin
// Android代码中
const val BASE_URL = "http://10.0.2.2:8000"  // 模拟器专用
```

`10.0.2.2` 是模拟器访问宿主机localhost的特殊地址。

### 使用真机

1. 确保手机和电脑在同一WiFi网络
2. 查看电脑IP地址：
   ```bash
   # Windows
   ipconfig
   
   # Linux/Mac
   ifconfig
   ```
3. Android代码中使用电脑IP：
   ```kotlin
   const val BASE_URL = "http://192.168.1.100:8000"  // 替换为实际IP
   ```

## 常见问题

### 1. API Key错误

**错误：** `服务配置错误: 未设置DASHSCOPE_API_KEY环境变量`

**解决：**
- 确认已创建 `.env` 文件
- 确认API Key正确填写
- 重启服务

### 2. 端口被占用

**错误：** `[Errno 10048] error while attempting to bind on address`

**解决：**
```bash
# 更改端口
uvicorn app.main:app --reload --port 8001
```

### 3. CORS错误（跨域）

前端出现跨域错误，检查 `main.py` 中的CORS配置是否正确。

### 4. AI响应慢

通义千问API首次调用可能较慢，后续会快一些。可以：
- 添加缓存机制
- 使用更快的模型（如qwen-plus）

## 技术栈

- **FastAPI**: Web框架
- **Pydantic**: 数据验证
- **DashScope**: 通义千问SDK
- **Uvicorn**: ASGI服务器

## 许可

本项目为软件创新大赛参赛作品。

