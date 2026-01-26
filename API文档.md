# API接口文档

## 基础信息

- **基础URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **字符编码**: `UTF-8`

## 接口列表

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

### 12. 生成行程计划 ⭐

**接口地址**: `POST /api/trip/generate`

**接口描述**: 根据用户查询和偏好，AI生成个性化行程计划

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名                 | 类型         | 必填 | 说明                                                    |
| ---------------------- | ------------ | ---- | ------------------------------------------------------- |
| userId                 | int          | 是   | 用户ID，>0                                              |
| query                  | string       | 是   | 用户查询文本，1-500个字符，如："规划周末带娃去杭州玩"   |
| preferences            | object\|null | 否   | 用户偏好对象                                            |
| preferences.healthGoal | string\|null | 否   | 健康目标：reduce_fat/gain_muscle/control_sugar/balanced |
| preferences.allergens  | array\|null  | 否   | 过敏原列表，如：["海鲜", "花生"]                        |

**请求示例**:
```bash
POST http://localhost:8000/api/trip/generate
Content-Type: application/json

{
  "userId": 123,
  "query": "规划周末带娃去杭州玩",
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
  "message": "行程生成成功",
  "data": {
    "tripId": 456,
    "title": "杭州2日亲子游",
    "destination": "杭州",
    "startDate": "2026-01-25",
    "endDate": "2026-01-26",
    "items": [
      {
        "dayIndex": 1,
        "startTime": "09:00",
        "placeName": "西湖风景区",
        "placeType": "attraction",
        "duration": 180,
        "cost": 0.0,
        "notes": "建议游玩3小时，适合亲子活动"
      },
      {
        "dayIndex": 1,
        "startTime": "12:00",
        "placeName": "楼外楼",
        "placeType": "dining",
        "duration": 60,
        "cost": 200.0,
        "notes": "注意避开海鲜类菜品"
      },
      {
        "dayIndex": 2,
        "startTime": "10:00",
        "placeName": "灵隐寺",
        "placeType": "attraction",
        "duration": 120,
        "cost": 45.0,
        "notes": "适合文化体验"
      }
    ]
  }
}
```

**响应字段说明**:
| 字段                   | 类型         | 说明                                            |
| ---------------------- | ------------ | ----------------------------------------------- |
| code                   | int          | 状态码，200表示成功                             |
| message                | string       | 响应消息                                        |
| data                   | object       | 行程数据                                        |
| data.tripId            | int          | 行程ID                                          |
| data.title             | string       | 行程标题                                        |
| data.destination       | string\|null | 目的地                                          |
| data.startDate         | string       | 开始日期（YYYY-MM-DD）                          |
| data.endDate           | string       | 结束日期（YYYY-MM-DD）                          |
| data.items             | array        | 行程节点列表                                    |
| data.items[].dayIndex  | int          | 第几天（从1开始）                               |
| data.items[].startTime | string\|null | 开始时间（HH:mm格式）                           |
| data.items[].placeName | string       | 地点名称                                        |
| data.items[].placeType | string\|null | 类型：attraction/dining/transport/accommodation |
| data.items[].duration  | int\|null    | 预计时长（分钟）                                |
| data.items[].cost      | float\|null  | 预计费用（元）                                  |
| data.items[].notes     | string\|null | 备注                                            |

**错误响应**:
- 请求参数错误（HTTP 400）:
```json
{
  "detail": "请求参数错误: ..."
}
```

---

### 13. 获取行程列表

**接口地址**: `GET /api/trip/list`

**接口描述**: 获取用户全部行程规划列表，按创建时间倒序

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
      "title": "北京3日游",
      "destination": "北京",
      "startDate": "2026-01-20",
      "endDate": "2026-01-22",
      "status": "done",
      "itemCount": 8
    }
  ]
}
```

**响应字段说明**:
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

### 14. 获取最近行程

**接口地址**: `GET /api/trip/recent`

**接口描述**: 获取用户最近行程规划（用于快速访问）

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
      "title": "杭州2日亲子游",
      "destination": "杭州",
      "startDate": "2026-01-25",
      "endDate": "2026-01-26",
      "status": "planning",
      "itemCount": 5
    }
  ]
}
```

---

### 15. 获取首页行程

**接口地址**: `GET /api/trip/home`

**接口描述**: 获取首页展示的行程（最近的几个行程）

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
      "title": "杭州2日亲子游",
      "destination": "杭州",
      "startDate": "2026-01-25",
      "endDate": "2026-01-26",
      "status": "planning",
      "itemCount": 5
    }
  ]
}
```

---

### 16. 获取行程详情

**接口地址**: `GET /api/trip/{tripId}`

**接口描述**: 获取某个行程的具体信息，包括所有行程节点

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
    "title": "杭州2日亲子游",
    "destination": "杭州",
    "startDate": "2026-01-25",
    "endDate": "2026-01-26",
    "items": [
      {
        "dayIndex": 1,
        "startTime": "09:00",
        "placeName": "西湖风景区",
        "placeType": "attraction",
        "duration": 180,
        "cost": 0.0,
        "notes": "建议游玩3小时"
      },
      {
        "dayIndex": 1,
        "startTime": "12:00",
        "placeName": "楼外楼",
        "placeType": "dining",
        "duration": 60,
        "cost": 200.0,
        "notes": "注意避开海鲜类菜品"
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

## 使用示例

### Python (requests)

```python
import requests

# 分析菜品
url = "http://localhost:8000/api/food/analyze"
data = {"food_name": "番茄炒蛋"}

response = requests.post(url, json=data)
result = response.json()

if result["success"]:
    food_data = result["data"]
    print(f"热量: {food_data['calories']} kcal")
    print(f"推荐: {food_data['recommendation']}")
```

### JavaScript (fetch)

```javascript
// 分析菜品
fetch('http://localhost:8000/api/food/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    food_name: '番茄炒蛋'
  })
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('热量:', data.data.calories);
    console.log('推荐:', data.data.recommendation);
  }
});
```

### Kotlin (Retrofit)

```kotlin
// 定义API接口
interface ApiService {
    @POST("api/food/analyze")
    suspend fun analyzeFood(
        @Body request: FoodRequest
    ): Response<FoodResponse>
}

// 数据类
data class FoodRequest(
    val food_name: String
)

data class FoodResponse(
    val success: Boolean,
    val message: String,
    val data: FoodData?
)

data class FoodData(
    val name: String,
    val calories: Double,
    val protein: Double,
    val fat: Double,
    val carbs: Double,
    val recommendation: String
)

// 调用示例
val request = FoodRequest(food_name = "番茄炒蛋")
val response = apiService.analyzeFood(request)

if (response.isSuccessful && response.body()?.success == true) {
    val foodData = response.body()?.data
    println("热量: ${foodData?.calories} kcal")
    println("推荐: ${foodData?.recommendation}")
}
```

### curl

```bash
# 分析菜品
curl -X POST http://localhost:8000/api/food/analyze \
  -H "Content-Type: application/json" \
  -d '{"food_name": "番茄炒蛋"}'

# 健康检查
curl http://localhost:8000/health
```

---

## 错误码说明

| HTTP状态码 | 说明             |
| ---------- | ---------------- |
| 200        | 请求成功         |
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

### v1.0.0 (2026-01-22)
- ✅ 实现菜品营养分析API
- ✅ 集成通义千问AI
- ✅ 添加健康检查接口
- ✅ 配置CORS支持

