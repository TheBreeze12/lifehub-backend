# API接口文档

## 基础信息

- **基础URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **字符编码**: `UTF-8`

## 接口列表

### 接口总览

| 分类     | 接口                           | 方法 | 说明               |
| -------- | ------------------------------ | ---- | ------------------ |
| **基础** | `/`                            | GET  | API基本信息        |
| **基础** | `/health`                      | GET  | 健康检查           |
| **餐饮** | `/api/food/analyze`            | POST | 分析菜品营养成分   |
| **餐饮** | `/api/food/recognize`          | POST | 菜单图片识别       |
| **餐饮** | `/api/food/latest-recognition` | GET  | 获取最新识别结果   |
| **餐饮** | `/api/food/record`             | POST | 添加饮食记录       |
| **餐饮** | `/api/food/records`            | GET  | 获取所有饮食记录   |
| **餐饮** | `/api/food/records/today`      | GET  | 获取今日饮食记录   |
| **餐饮** | `/api/food/health`             | GET  | 食物服务健康检查   |
| **用户** | `/api/user/register`           | POST | 用户注册           |
| **用户** | `/api/user/login`              | POST | 用户登录（JWT）    |
| **用户** | `/api/user/refresh`            | POST | 刷新Token          |
| **用户** | `/api/user/me`                 | GET  | 获取当前用户（需认证）|
| **用户** | `/api/user/data`               | GET  | 用户登录（旧版）   |
| **用户** | `/api/user/preferences`        | GET  | 获取用户偏好       |
| **用户** | `/api/user/preferences`        | PUT  | 更新用户偏好       |
| **运动** | `/api/trip/generate`           | POST | 生成运动计划       |
| **运动** | `/api/trip/list`               | GET  | 获取运动计划列表   |
| **运动** | `/api/trip/recent`             | GET  | 获取最近运动计划   |
| **运动** | `/api/trip/home`               | GET  | 获取首页运动计划   |
| **运动** | `/api/trip/{tripId}`           | GET  | 获取运动计划详情   |
| **天气** | `/api/weather/by-address`      | GET  | 根据地址查询天气   |
| **天气** | `/api/weather/by-plan`         | GET  | 根据计划ID查询天气 |

---

### 1. 根路径

**接口地址**: `GET /`

**接口描述**: 查看API基本信息

**请求示例**:
```bash
GET http://localhost:8000/
```

**响应示例**:
```json
{
  "message": "智能生活服务工具API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### 2. 健康检查

**接口地址**: `GET /health`

**接口描述**: 检查服务运行状态和配置

**请求示例**:
```bash
GET http://localhost:8000/health
```

**响应示例**:
```json
{
  "status": "ok",
  "api_key_configured": true
}
```

**响应字段说明**:
| 字段               | 类型    | 说明                 |
| ------------------ | ------- | -------------------- |
| status             | string  | 服务状态，ok表示正常 |
| api_key_configured | boolean | API Key是否已配置    |

---

### 3. 分析菜品营养成分 ⭐

**接口地址**: `POST /api/food/analyze`

**接口描述**: 输入菜品名称，返回AI分析的营养成分数据

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名    | 类型   | 必填 | 说明                 |
| --------- | ------ | ---- | -------------------- |
| food_name | string | 是   | 菜品名称，1-50个字符 |

**请求示例**:
```bash
POST http://localhost:8000/api/food/analyze
Content-Type: application/json

{
  "food_name": "番茄炒蛋"
}
```

**响应示例**:
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

**响应字段说明**:
| 字段                | 类型    | 说明                  |
| ------------------- | ------- | --------------------- |
| success             | boolean | 请求是否成功          |
| message             | string  | 响应消息              |
| data                | object  | 菜品数据对象          |
| data.name           | string  | 菜品名称              |
| data.calories       | float   | 热量（千卡/100g）     |
| data.protein        | float   | 蛋白质（克/100g）     |
| data.fat            | float   | 脂肪（克/100g）       |
| data.carbs          | float   | 碳水化合物（克/100g） |
| data.recommendation | string  | AI推荐理由            |

**错误响应**:

*API Key未配置*:
```json
{
  "detail": "服务配置错误: 未设置DASHSCOPE_API_KEY环境变量"
}
```
HTTP状态码: 500

*请求参数错误*:
```json
{
  "detail": [
    {
      "loc": ["body", "food_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
HTTP状态码: 422

---

### 4. 食物服务健康检查

**接口地址**: `GET /api/food/health`

**接口描述**: 检查食物分析服务状态

**请求示例**:
```bash
GET http://localhost:8000/api/food/health
```

**响应示例**:
```json
{
  "status": "ok",
  "service": "food-analysis"
}
```

---

### 5. 菜单图片识别 ⭐

**接口地址**: `POST /api/food/recognize`

**接口描述**: 上传菜单图片，AI识别菜品并分析营养成分，根据用户健康目标提供推荐

**请求头**:
```
Content-Type: multipart/form-data
```

**请求参数**:
| 参数名 | 类型   | 必填 | 说明                                 |
| ------ | ------ | ---- | ------------------------------------ |
| image  | file   | 是   | 菜单图片文件（支持常见图片格式）     |
| userId | string | 否   | 用户ID（可选，用于根据健康目标推荐） |

**请求示例**:
```bash
POST http://localhost:8000/api/food/recognize
Content-Type: multipart/form-data

# 使用 curl
curl -X POST http://localhost:8000/api/food/recognize \
  -F "image=@menu.jpg" \
  -F "userId=123"
```

**响应示例**:
```json
{
  "code": 200,
  "message": "识别成功",
  "data": {
    "dishes": [
      {
        "name": "宫保鸡丁",
        "calories": 320.0,
        "protein": 28.0,
        "fat": 18.0,
        "carbs": 15.0,
        "isRecommended": true,
        "reason": "蛋白质丰富，适合您的减脂目标"
      },
      {
        "name": "糖醋里脊",
        "calories": 280.0,
        "protein": 20.0,
        "fat": 12.0,
        "carbs": 25.0,
        "isRecommended": false,
        "reason": "糖分较高，建议适量食用"
      }
    ]
  }
}
```

**响应字段说明**:
| 字段                        | 类型    | 说明                |
| --------------------------- | ------- | ------------------- |
| code                        | int     | 状态码，200表示成功 |
| message                     | string  | 响应消息            |
| data                        | object  | 识别结果            |
| data.dishes                 | array   | 菜品列表            |
| data.dishes[].name          | string  | 菜品名称            |
| data.dishes[].calories      | float   | 热量（千卡）        |
| data.dishes[].protein       | float   | 蛋白质（克）        |
| data.dishes[].fat           | float   | 脂肪（克）          |
| data.dishes[].carbs         | float   | 碳水化合物（克）    |
| data.dishes[].isRecommended | boolean | 是否推荐            |
| data.dishes[].reason        | string  | 推荐理由            |

**错误响应**:
- 文件类型错误（HTTP 400）:
```json
{
  "detail": "请上传图片文件"
}
```

---

### 6. 获取最新菜单识别结果

**接口地址**: `GET /api/food/latest-recognition`

**接口描述**: 获取用户最新的菜单识别结果

**请求参数**:
| 参数名 | 类型 | 必填 | 说明                                 |
| ------ | ---- | ---- | ------------------------------------ |
| userId | int  | 否   | 用户ID（可选，不提供则返回全局最新） |

**请求示例**:
```bash
GET http://localhost:8000/api/food/latest-recognition?userId=123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "dishes": [
      {
        "name": "宫保鸡丁",
        "calories": 320.0,
        "protein": 28.0,
        "fat": 18.0,
        "carbs": 15.0,
        "isRecommended": true,
        "reason": "蛋白质丰富，适合您的减脂目标"
      }
    ]
  }
}
```

**未找到记录时响应**:
```json
{
  "code": 404,
  "message": "未找到识别记录",
  "data": {
    "dishes": []
  }
}
```

---

### 7. 添加饮食记录

**接口地址**: `POST /api/food/record`

**接口描述**: 添加用户的饮食记录

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名     | 类型   | 必填 | 说明                                                      |
| ---------- | ------ | ---- | --------------------------------------------------------- |
| userId     | int    | 是   | 用户ID                                                    |
| foodName   | string | 是   | 菜品名称，1-100个字符                                     |
| calories   | float  | 是   | 热量（kcal），≥0                                          |
| protein    | float  | 否   | 蛋白质（g），≥0，默认0.0                                  |
| fat        | float  | 否   | 脂肪（g），≥0，默认0.0                                    |
| carbs      | float  | 否   | 碳水化合物（g），≥0，默认0.0                              |
| mealType   | string | 是   | 餐次：早餐/午餐/晚餐/加餐 或 breakfast/lunch/dinner/snack |
| recordDate | string | 是   | 记录日期（YYYY-MM-DD格式）                                |

**请求示例**:
```bash
POST http://localhost:8000/api/food/record
Content-Type: application/json

{
  "userId": 123,
  "foodName": "宫保鸡丁",
  "calories": 320.0,
  "protein": 28.0,
  "fat": 18.0,
  "carbs": 15.0,
  "mealType": "午餐",
  "recordDate": "2026-01-23"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "记录成功",
  "data": null
}
```

**错误响应**:
- 用户不存在（HTTP 404）:
```json
{
  "detail": "用户不存在"
}
```

- 日期格式错误（HTTP 400）:
```json
{
  "detail": "日期格式错误，请使用 YYYY-MM-DD 格式"
}
```

---

### 8. 获取饮食记录

**接口地址**: `GET /api/food/records`

**接口描述**: 获取用户所有饮食记录，按日期分组

**请求参数**:
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| userId | int  | 是   | 用户ID |

**请求示例**:
```bash
GET http://localhost:8000/api/food/records?userId=123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "2026-01-23": [
      {
        "id": 1,
        "userId": 123,
        "foodName": "宫保鸡丁",
        "calories": 320.0,
        "protein": 28.0,
        "fat": 18.0,
        "carbs": 15.0,
        "mealType": "午餐",
        "recordDate": "2026-01-23",
        "createdAt": "2026-01-23T10:30:00"
      },
      {
        "id": 2,
        "userId": 123,
        "foodName": "番茄炒蛋",
        "calories": 150.0,
        "protein": 10.5,
        "fat": 8.2,
        "carbs": 6.3,
        "mealType": "晚餐",
        "recordDate": "2026-01-23",
        "createdAt": "2026-01-23T18:00:00"
      }
    ],
    "2026-01-22": [
      {
        "id": 3,
        "userId": 123,
        "foodName": "白粥",
        "calories": 50.0,
        "protein": 1.0,
        "fat": 0.2,
        "carbs": 10.0,
        "mealType": "早餐",
        "recordDate": "2026-01-22",
        "createdAt": "2026-01-22T08:00:00"
      }
    ]
  }
}
```

**响应字段说明**:
| 字段                  | 类型   | 说明                             |
| --------------------- | ------ | -------------------------------- |
| code                  | int    | 状态码，200表示成功              |
| message               | string | 响应消息                         |
| data                  | object | 按日期分组的记录，键为日期字符串 |
| data[日期].id         | int    | 记录ID                           |
| data[日期].userId     | int    | 用户ID                           |
| data[日期].foodName   | string | 菜品名称                         |
| data[日期].calories   | float  | 热量（kcal）                     |
| data[日期].protein    | float  | 蛋白质（g）                      |
| data[日期].fat        | float  | 脂肪（g）                        |
| data[日期].carbs      | float  | 碳水化合物（g）                  |
| data[日期].mealType   | string | 餐次                             |
| data[日期].recordDate | string | 记录日期（YYYY-MM-DD）           |
| data[日期].createdAt  | string | 创建时间（ISO格式）              |

---

### 9. 获取今日饮食记录

**接口地址**: `GET /api/food/records/today`

**接口描述**: 获取用户今天的饮食记录

**请求参数**:
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| userId | int  | 是   | 用户ID |

**请求示例**:
```bash
GET http://localhost:8000/api/food/records/today?userId=123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "2026-01-23": [
      {
        "id": 1,
        "userId": 123,
        "foodName": "宫保鸡丁",
        "calories": 320.0,
        "protein": 28.0,
        "fat": 18.0,
        "carbs": 15.0,
        "mealType": "午餐",
        "recordDate": "2026-01-23",
        "createdAt": "2026-01-23T10:30:00"
      }
    ]
  }
}
```

---

### 10. 获取用户偏好

**接口地址**: `GET /api/user/preferences`

**接口描述**: 获取用户的偏好设置（健康目标、过敏原、出行偏好等）

**请求参数**:
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| userId | int  | 是   | 用户ID |

**请求示例**:
```bash
GET http://localhost:8000/api/user/preferences?userId=123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "userId": 123,
    "nickname": "健康达人",
    "healthGoal": "reduce_fat",
    "allergens": ["海鲜", "花生"],
    "travelPreference": "self_driving",
    "dailyBudget": 500
  }
}
```

**响应字段说明**:
| 字段                  | 类型         | 说明                                                    |
| --------------------- | ------------ | ------------------------------------------------------- |
| code                  | int          | 状态码，200表示成功                                     |
| message               | string       | 响应消息                                                |
| data                  | object       | 用户偏好数据                                            |
| data.userId           | int          | 用户ID                                                  |
| data.nickname         | string\|null | 用户昵称                                                |
| data.healthGoal       | string\|null | 健康目标：reduce_fat/gain_muscle/control_sugar/balanced |
| data.allergens        | array\|null  | 过敏原列表，如：["海鲜", "花生"]                        |
| data.travelPreference | string\|null | 出行偏好：self_driving/public_transport/walking         |
| data.dailyBudget      | int\|null    | 出行日预算（元）                                        |

**错误响应**:
- 用户不存在（HTTP 404）:
```json
{
  "detail": "用户不存在，userId: 123"
}
```

---

### 11. 更新用户偏好

**接口地址**: `PUT /api/user/preferences`

**接口描述**: 更新用户的偏好设置（支持部分更新）

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名           | 类型         | 必填 | 说明                                                    |
| ---------------- | ------------ | ---- | ------------------------------------------------------- |
| userId           | int          | 是   | 用户ID，>0                                              |
| healthGoal       | string\|null | 否   | 健康目标：reduce_fat/gain_muscle/control_sugar/balanced |
| allergens        | array\|null  | 否   | 过敏原列表，如：["海鲜", "花生"]                        |
| travelPreference | string\|null | 否   | 出行偏好：self_driving/public_transport/walking         |
| dailyBudget      | int\|null    | 否   | 出行日预算（元），≥0                                    |

**请求示例**:
```bash
PUT http://localhost:8000/api/user/preferences
Content-Type: application/json

{
  "userId": 123,
  "healthGoal": "reduce_fat",
  "allergens": ["海鲜", "花生"],
  "travelPreference": "self_driving",
  "dailyBudget": 500
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "userId": 123,
    "nickname": "健康达人",
    "healthGoal": "reduce_fat",
    "allergens": ["海鲜", "花生"],
    "travelPreference": "self_driving",
    "dailyBudget": 500
  }
}
```

**错误响应**:
- 用户不存在（HTTP 404）:
```json
{
  "detail": "用户不存在，userId: 123"
}
```

---

### 11.1 用户注册 ⭐

**接口地址**: `POST /api/user/register`

**接口描述**: 注册新用户

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名   | 类型   | 必填 | 说明                   |
| -------- | ------ | ---- | ---------------------- |
| nickname | string | 是   | 用户昵称，最大50个字符 |
| password | string | 是   | 用户密码，6-128个字符  |

**请求示例**:
```bash
POST http://localhost:8000/api/user/register
Content-Type: application/json

{
  "nickname": "健康达人",
  "password": "securepassword123"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "注册成功",
  "userId": 123
}
```

**错误响应**:
- 用户已存在（HTTP 400）:
```json
{
  "detail": "用户已存在，nickname: 健康达人"
}
```

- 密码长度不符合要求（HTTP 422）:
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 6 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

---

### 11.2 用户登录

**接口地址**: `GET /api/user/data`

**接口描述**: 通过昵称和密码登录，获取用户信息

**请求参数**:
| 参数名   | 类型   | 必填 | 说明     |
| -------- | ------ | ---- | -------- |
| nickname | string | 是   | 用户昵称 |
| password | string | 是   | 用户密码 |

**请求示例**:
```bash
GET http://localhost:8000/api/user/data?nickname=健康达人&password=securepassword123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "userId": 123,
    "nickname": "健康达人",
    "healthGoal": "reduce_fat",
    "allergens": ["海鲜", "花生"],
    "travelPreference": "self_driving",
    "dailyBudget": 500
  }
}
```

**错误响应**:
- 用户不存在（HTTP 404）:
```json
{
  "detail": "用户不存在，nickname: 健康达人"
}
```

- 密码错误（HTTP 401）:
```json
{
  "detail": "密码错误"
}
```

---

### 12. 生成运动计划 ⭐

**接口地址**: `POST /api/trip/generate`

**接口描述**: 根据用户查询与偏好，AI生成餐后运动计划（基于“餐后30–60分钟”原则，地点为具体可运动的场所）。

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名                 | 类型         | 必填 | 说明                                                                   |
| ---------------------- | ------------ | ---- | ---------------------------------------------------------------------- |
| userId                 | int          | 是   | 用户ID，>0                                                             |
| query                  | string       | 是   | 用户查询文本，1-500个字符，如："今天午餐后在北京安排散步，消耗200千卡" |
| preferences            | object\|null | 否   | 用户偏好对象                                                           |
| preferences.healthGoal | string\|null | 否   | 健康目标：reduce_fat/gain_muscle/control_sugar/balanced                |
| preferences.allergens  | array\|null  | 否   | 过敏原列表，如：["海鲜", "花生"]                                       |

**请求示例**:
```bash
POST http://localhost:8000/api/trip/generate
Content-Type: application/json

{
  "userId": 123,
  "query": "今天午餐后在北京安排散步，目标消耗200千卡，地点选具体公园",
  "preferences": {
    "healthGoal": "reduce_fat",
    "allergens": ["海鲜", "花生"]
  }
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "运动计划生成成功",
  "data": {
    "tripId": 456,
    "title": "餐后散步计划",
    "destination": "北京中央公园",
    "startDate": "2026-02-01",
    "endDate": "2026-02-01",
    "items": [
      {
        "dayIndex": 1,
        "startTime": "12:45",
        "placeName": "北京中央公园健身步道",
        "placeType": "walking",
        "duration": 30,
        "cost": 150,
        "notes": "餐后散步，建议慢走，注意补水"
      },
      {
        "dayIndex": 1,
        "startTime": "19:30",
        "placeName": "北京滨江健身步道",
        "placeType": "running",
        "duration": 20,
        "cost": 160,
        "notes": "轻慢跑，控制强度，避免过饱运动"
      },
    ]
  }
}
```

**响应字段说明**:
| 字段                   | 类型         | 说明                                                               |
| ---------------------- | ------------ | ------------------------------------------------------------------ |
| code                   | int          | 状态码，200表示成功                                                |
| message                | string       | 响应消息                                                           |
| data                   | object       | 运动计划数据                                                       |
| data.tripId            | int          | 计划ID                                                             |
| data.title             | string       | 计划标题                                                           |
| data.destination       | string\|null | 运动区域/起点（具体地点）                                          |
| data.startDate         | string       | 开始日期（YYYY-MM-DD）                                             |
| data.endDate           | string       | 结束日期（YYYY-MM-DD）                                             |
| data.items             | array        | 行程节点列表                                                       |
| data.items[].dayIndex  | int          | 第几天（从1开始）                                                  |
| data.items[].startTime | string\|null | 开始时间（HH:mm，依据提示词或当前时间，遵循餐后30–60分钟动态生成） |
| data.items[].placeName | string       | 运动地点名称（必须为具体地点）                                     |
| data.items[].placeType | string\|null | 运动类型/场景：walking/running/cycling/park/gym/indoor/outdoor     |
| data.items[].duration  | int\|null    | 预计时长（分钟）                                                   |
| data.items[].cost      | int\|null    | 预计消耗卡路里（kcal）                                             |
| data.items[].notes     | string\|null | 运动建议、注意事项                                                 |

**错误响应**:
- 请求参数错误（HTTP 400）:
```json
{
  "detail": "请求参数错误: ..."
}
```

---

### 13. 天气：根据地址获取当前天气 ⭐

**接口地址**: `GET /api/weather/by-address`

**接口描述**: 通过地址文本进行地理编码，查询当前天气（Open-Meteo，无需API Key）

**请求参数**:
| 参数名  | 类型   | 必填 | 说明                             |
| ------- | ------ | ---- | -------------------------------- |
| address | string | 是   | 地址文本，例如"北京市朝阳区望京" |

**请求示例**:
```bash
GET http://localhost:8000/api/weather/by-address?address=北京市朝阳区望京
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "address": "北京市朝阳区望京",
    "latitude": 39.99,
    "longitude": 116.47,
    "temperature": 2.1,
    "windspeed": 5.0,
    "winddirection": 320,
    "weathercode": 3,
    "time": "2026-02-01T10:00",
    "hourly": {
      "time": ["2026-02-01T10:00", "2026-02-01T11:00"],
      "temperature_2m": [2.1, 2.3],
      "precipitation": [0.0, 0.0]
    }
  }
}
```

**响应字段说明**:
| 字段                       | 类型   | 说明                       |
| -------------------------- | ------ | -------------------------- |
| code                       | int    | 状态码，200表示成功        |
| message                    | string | 响应消息                   |
| data                       | object | 天气数据对象               |
| data.address               | string | 地址提示（原始查询地址）   |
| data.latitude              | float  | 纬度                       |
| data.longitude             | float  | 经度                       |
| data.temperature           | float  | 当前气温（℃）              |
| data.windspeed             | float  | 风速（m/s）                |
| data.winddirection         | int    | 风向（度）                 |
| data.weathercode           | int    | 天气代码（Open-Meteo约定） |
| data.time                  | string | 时间（ISO）                |
| data.hourly                | object | 小时级预报（截取若干条）   |
| data.hourly.time           | array  | 时间列表                   |
| data.hourly.temperature_2m | array  | 小时级温度（℃）            |
| data.hourly.precipitation  | array  | 小时级降水量（mm）         |

**错误响应**:
- 地址为空（HTTP 400）:
```json
{ "detail": "地址不能为空" }
```
- 地址解析失败（HTTP 400）:
```json
{ "detail": "无法解析地址为坐标，请提供更精确的地址" }
```

---

### 14. 天气：根据计划ID获取当前天气 ⭐

**接口地址**: `GET /api/weather/by-plan`

**接口描述**: 通过行程计划 `planId` 查询当前天气
- 若计划包含 `latitude/longitude`，按坐标查询
- 否则按计划的 `destination` 地址查询

**请求参数**:
| 参数名 | 类型 | 必填 | 说明       |
| ------ | ---- | ---- | ---------- |
| planId | int  | 是   | 行程计划ID |

**请求示例**:
```bash
GET http://localhost:8000/api/weather/by-plan?planId=456
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "address": "杭州西湖风景区",
    "latitude": 30.25,
    "longitude": 120.16,
    "temperature": 7.3,
    "windspeed": 3.6,
    "winddirection": 270,
    "weathercode": 1,
    "time": "2026-02-01T10:00",
    "hourly": {
      "time": ["2026-02-01T10:00", "2026-02-01T11:00"],
      "temperature_2m": [7.3, 7.6],
      "precipitation": [0.0, 0.0]
    }
  }
}
```

**错误响应**:
- 行程不存在（HTTP 404）:
```json
{ "detail": "行程不存在，planId: 456" }
```
- 目的地为空且无坐标（HTTP 400）:
```json
{ "detail": "该计划无坐标且目的地为空，无法查询天气" }
```


### 15. 获取运动计划列表

**接口地址**: `GET /api/trip/list`

**接口描述**: 获取用户全部运动计划列表，按创建时间倒序

**请求参数**:
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| userId | int  | 是   | 用户ID |

**请求示例**:
```bash
GET http://localhost:8000/api/trip/list?userId=123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "tripId": 456,
      "title": "杭州2日亲子游",
      "destination": "杭州",
      "startDate": "2026-01-25",
      "endDate": "2026-01-26",
      "status": "planning",
      "itemCount": 5
    },
    {
      "tripId": 455,
      "title": "周末餐后慢跑计划",
      "destination": "上海滨江健身步道",
      "startDate": "2026-02-01",
      "endDate": "2026-02-02",
      "status": "done",
      "itemCount": 8
    }
  ]
      "title": "三日餐后散步计划",
      "destination": "北京中央公园",
      "startDate": "2026-01-29",
      "endDate": "2026-01-31",
| 字段               | 类型         | 说明                        |
| ------------------ | ------------ | --------------------------- |
| code               | int          | 状态码，200表示成功         |
| message            | string       | 响应消息                    |
| data               | array        | 行程摘要列表                |
| data[].tripId      | int          | 行程ID                      |
| data[].title       | string       | 行程标题                    |
| data[].destination | string\|null | 目的地                      |
| data[].startDate   | string       | 开始日期（YYYY-MM-DD）      |
| data[].endDate     | string       | 结束日期（YYYY-MM-DD）      |
| data[].status      | string\|null | 状态：planning/ongoing/done |
| data[].itemCount   | int          | 行程节点数量                |

---

### 16. 获取最近运动计划

**接口地址**: `GET /api/trip/recent`

**接口描述**: 获取用户最近运动计划（用于快速访问）

**请求参数**:
| 参数名 | 类型 | 必填 | 说明                  |
| ------ | ---- | ---- | --------------------- |
| userId | int  | 是   | 用户ID                |
| limit  | int  | 否   | 返回数量限制，默认5条 |

**请求示例**:
```bash
GET http://localhost:8000/api/trip/recent?userId=123&limit=5
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "tripId": 456,
      "title": "餐后散步三日计划",
      "destination": "深圳中心公园",
      "startDate": "2026-01-30",
      "endDate": "2026-02-01",
      "status": "planning",
      "itemCount": 5
    }
  ]
}
```

---

### 16. 获取首页运动计划

**接口地址**: `GET /api/trip/home`

**接口描述**: 获取首页展示的运动计划（最近的几个计划）

**请求参数**:
| 参数名 | 类型 | 必填 | 说明                  |
| ------ | ---- | ---- | --------------------- |
| userId | int  | 是   | 用户ID                |
| limit  | int  | 否   | 返回数量限制，默认3条 |

**请求示例**:
```bash
GET http://localhost:8000/api/trip/home?userId=123&limit=3
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "tripId": 456,
      "title": "餐后慢跑两日计划",
      "destination": "成都城北健身步道",
      "startDate": "2026-02-01",
      "endDate": "2026-02-02",
      "status": "planning",
      "itemCount": 5
    }
  ]
}
```

---

### 17. 获取运动计划详情

**接口地址**: `GET /api/trip/{tripId}`

**接口描述**: 获取某个运动计划的具体信息，包括所有运动节点

**路径参数**:
| 参数名 | 类型 | 必填 | 说明   |
| ------ | ---- | ---- | ------ |
| tripId | int  | 是   | 行程ID |

**请求示例**:
```bash
GET http://localhost:8000/api/trip/456
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "tripId": 456,
    "title": "两天餐后运动计划",
    "destination": "重庆中央公园",
    "startDate": "2026-02-01",
    "endDate": "2026-02-02",
    "items": [
      {
        "dayIndex": 1,
        "startTime": "12:45",
        "placeName": "重庆中央公园健身步道",
        "placeType": "walking",
        "duration": 40,
        "cost": 180,
        "notes": "餐后散步，慢走为主"
      },
      {
        "dayIndex": 1,
        "startTime": "19:30",
        "placeName": "重庆滨江健身步道",
        "placeType": "running",
        "duration": 25,
        "cost": 200,
        "notes": "轻慢跑，注意补水"
      }
    ]
  }
}
```

**错误响应**:
- 行程不存在（HTTP 404）:
```json
{
  "detail": "行程不存在，tripId: 456"
}
```

---


### 18. 用户登录（JWT认证）⭐

**接口地址**: `POST /api/user/login`

**接口描述**: 用户登录，返回JWT双令牌（Access Token + Refresh Token）

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名   | 类型   | 必填 | 说明                   |
| -------- | ------ | ---- | ---------------------- |
| nickname | string | 是   | 用户昵称，最大50个字符 |
| password | string | 是   | 用户密码，6-128个字符  |

**请求示例**:
```bash
POST http://localhost:8000/api/user/login
Content-Type: application/json

{
  "nickname": "健康达人",
  "password": "securepassword123"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "userId": 123,
    "nickname": "健康达人",
    "healthGoal": "reduce_fat",
    "allergens": ["海鲜", "花生"],
    "travelPreference": "self_driving",
    "dailyBudget": 500
  },
  "token": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**响应字段说明**:
| 字段                  | 类型         | 说明                          |
| --------------------- | ------------ | ----------------------------- |
| code                  | int          | 状态码，200表示成功           |
| message               | string       | 响应消息                      |
| data                  | object       | 用户偏好数据                  |
| token                 | object       | JWT Token信息                 |
| token.access_token    | string       | Access Token，用于API认证     |
| token.refresh_token   | string       | Refresh Token，用于刷新Token  |
| token.token_type      | string       | Token类型，固定为"bearer"     |
| token.expires_in      | int          | Access Token过期时间（秒）    |

**错误响应**:
- 用户不存在（HTTP 404）: `{"detail": "用户不存在，nickname: 健康达人"}`
- 密码错误（HTTP 401）: `{"detail": "密码错误"}`

---

### 19. 刷新Token ⭐

**接口地址**: `POST /api/user/refresh`

**接口描述**: 使用Refresh Token获取新的Access Token和Refresh Token

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名        | 类型   | 必填 | 说明          |
| ------------- | ------ | ---- | ------------- |
| refresh_token | string | 是   | Refresh Token |

**请求示例**:
```bash
POST http://localhost:8000/api/user/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "Token刷新成功",
  "token": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**错误响应**:
- 无效的Refresh Token（HTTP 401）: `{"detail": "无效的Refresh Token"}`

---

### 20. 获取当前用户信息（需认证）⭐

**接口地址**: `GET /api/user/me`

**接口描述**: 获取当前登录用户信息，需要JWT认证

**请求头**:
```
Authorization: Bearer <access_token>
```

**请求示例**:
```bash
GET http://localhost:8000/api/user/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "userId": 123,
    "nickname": "健康达人",
    "healthGoal": "reduce_fat",
    "allergens": ["海鲜", "花生"],
    "travelPreference": "self_driving",
    "dailyBudget": 500
  }
}
```

**错误响应**:
- 未提供认证凭证（HTTP 401）: `{"detail": "未提供认证凭证"}`
- 无效的认证凭证（HTTP 401）: `{"detail": "无效的认证凭证"}`

---

## JWT认证说明

### Token类型
- **Access Token**: 用于API认证，有效期30分钟
- **Refresh Token**: 用于刷新Access Token，有效期7天

### 使用方法
1. 调用 `/api/user/login` 获取Token对
2. 将Access Token放入请求头：`Authorization: Bearer <access_token>`
3. Access Token过期前，使用Refresh Token调用 `/api/user/refresh` 获取新Token

### 注意事项
- Access Token过期后需要使用Refresh Token刷新
- Refresh Token过期后需要重新登录
- 密码使用bcrypt加密存储
- 旧版 `/api/user/data` 接口仍可用（向后兼容）

---

## 错误码说明

| HTTP状态码 | 说明             |
| ---------- | ---------------- |
| 200        | 请求成功         |
| 401        | 未授权（Token无效或密码错误） |
| 404        | 资源不存在       |
| 422        | 请求参数验证失败 |
| 500        | 服务器内部错误   |

---

## 注意事项

1. **API Key配置**: 必须在 `.env` 文件中配置 `DASHSCOPE_API_KEY`
2. **请求频率**: 通义千问API有调用频率限制，建议添加缓存机制
3. **响应时间**: 首次调用可能较慢（3-5秒），后续会快一些
4. **数据准确性**: 营养数据为AI估算，仅供参考
5. **跨域访问**: 开发环境已配置CORS允许所有来源

---

## 交互式文档

访问以下地址可以使用交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

在Swagger UI中可以：
- 查看所有接口
- 直接测试API
- 查看请求/响应示例
- 下载OpenAPI规范

---

## 更新日志

### v1.1.0 (2026-02-03)
- ✅ 实现JWT双令牌认证机制（Access Token + Refresh Token）
- ✅ 添加用户登录接口 `/api/user/login`（返回JWT Token）
- ✅ 添加Token刷新接口 `/api/user/refresh`
- ✅ 添加获取当前用户接口 `/api/user/me`（需JWT认证）
- ✅ 密码使用bcrypt加密存储
- ✅ 保留旧版登录接口向后兼容

### v1.0.0 (2026-01-22)
- ✅ 实现菜品营养分析API
- ✅ 集成通义千问AI
- ✅ 添加健康检查接口
- ✅ 配置CORS支持
- ✅ 实现菜单图片识别功能
- ✅ 实现饮食记录管理
- ✅ 实现智能行程规划（运动计划）
- ✅ 实现用户注册和登录
- ✅ 实现用户偏好设置
- ✅ 集成天气查询服务（Open-Meteo）

