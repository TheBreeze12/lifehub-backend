# 智能生活服务工具 - 后端API

FastAPI实现的后端服务，提供餐饮营养分析功能。

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   └── food.py
│   ├── routers/             # API路由
│   │   ├── __init__.py
│   │   └── food.py
│   └── services/            # 业务服务
│       ├── __init__.py
│       └── ai_service.py
├── requirements.txt         # Python依赖
├── env_example.txt          # 环境变量示例
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

### 2. 配置环境变量

复制 `env_example.txt` 为 `.env`，并填入您的API Key：

```bash
# Windows
copy env_example.txt .env

# Linux/Mac
cp env_example.txt .env
```

编辑 `.env` 文件：

```
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
HOST=0.0.0.0
PORT=8000
```

**获取API Key：**
1. 访问 https://dashscope.aliyuncs.com/
2. 登录/注册阿里云账号
3. 进入控制台获取API Key
4. 新用户有免费额度

### 3. 运行服务

```bash
# 方法1：使用uvicorn命令
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方法2：直接运行main.py
python -m app.main
```

服务启动后：
- API文档：http://localhost:8000/docs
- 交互式文档：http://localhost:8000/redoc
- 健康检查：http://localhost:8000/health

## API接口

### 1. 分析菜品营养

**接口：** `POST /api/food/analyze`

**请求体：**
```json
{
  "food_name": "番茄炒蛋"
}
```

**响应：**
```json
{
  "success": true,
  "message": "分析成功",
  "data": {
    "name": "番茄炒蛋",
    "calories": 150.0,
    "protein": 10.5,
    "fat": 8.2,
    "carbs": 6.3,
    "recommendation": "这道菜营养均衡，蛋白质含量较高，适合减脂期食用。建议控制油量。"
  }
}
```

### 2. 健康检查

**接口：** `GET /health`

**响应：**
```json
{
  "status": "ok",
  "api_key_configured": true
}
```

## 测试API

### 使用curl

```bash
# 测试菜品分析
curl -X POST http://localhost:8000/api/food/analyze \
  -H "Content-Type: application/json" \
  -d "{\"food_name\": \"番茄炒蛋\"}"

# 健康检查
curl http://localhost:8000/health
```

### 使用Postman

1. 创建POST请求：`http://localhost:8000/api/food/analyze`
2. Headers添加：`Content-Type: application/json`
3. Body选择raw，输入：
   ```json
   {
     "food_name": "番茄炒蛋"
   }
   ```
4. 点击Send

### 使用浏览器

访问 http://localhost:8000/docs 使用Swagger UI进行交互式测试。

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

## 开发建议

### 添加缓存

```python
# 可以使用Redis缓存AI结果
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_analyze(food_name: str):
    return ai_service.analyze_food_nutrition(food_name)
```

### 日志记录

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"分析食物: {food_name}")
```

### 数据库存储

后续可以添加数据库存储用户查询历史：
```python
# 使用SQLAlchemy
from sqlalchemy import create_engine
```

## 下一步

- [ ] 添加用户认证
- [ ] 添加查询历史记录
- [ ] 添加Redis缓存
- [ ] 添加更多菜品分析功能
- [ ] 实现出行规划API

## 技术栈

- **FastAPI**: Web框架
- **Pydantic**: 数据验证
- **DashScope**: 通义千问SDK
- **Uvicorn**: ASGI服务器

## 许可

本项目为软件创新大赛参赛作品。

