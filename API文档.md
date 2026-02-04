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
| **餐饮** | `/api/food/diet/{record_id}`   | PUT  | 更新饮食记录       |
| **餐饮** | `/api/food/diet/{record_id}`   | DELETE | 删除饮食记录     |
| **餐饮** | `/api/food/allergen/check`     | POST | 检测菜品过敏原     |
| **餐饮** | `/api/food/allergen/categories`| GET  | 获取过敏原类别列表 |
| **餐饮** | `/api/food/meal/before`        | POST | 上传餐前图片       |
| **餐饮** | `/api/food/meal/after/{comparison_id}` | POST | 上传餐后图片并计算净摄入 |
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
    "recommendation": "这道菜营养均衡，蛋白质含量较高，适合减脂期食用。建议控制油量。",
    "allergens": ["egg"],
    "allergen_reasoning": "番茄炒蛋的主要食材是鸡蛋，属于蛋类过敏原。"
  }
}
```

**响应字段说明**:
| 字段                     | 类型     | 说明                                              |
| ------------------------ | -------- | ------------------------------------------------- |
| success                  | boolean  | 请求是否成功                                      |
| message                  | string   | 响应消息                                          |
| data                     | object   | 菜品数据对象                                      |
| data.name                | string   | 菜品名称                                          |
| data.calories            | float    | 热量（千卡/100g）                                 |
| data.protein             | float    | 蛋白质（克/100g）                                 |
| data.fat                 | float    | 脂肪（克/100g）                                   |
| data.carbs               | float    | 碳水化合物（克/100g）                             |
| data.recommendation      | string   | AI推荐理由                                        |
| data.allergens           | string[] | AI推理的过敏原代码列表（Phase 7新增）             |
| data.allergen_reasoning  | string   | 过敏原推理说明（Phase 7新增）                     |

**过敏原代码对照**（八大类）:
| 代码      | 中文名称 | 英文名称   | 说明                           |
| --------- | -------- | ---------- | ------------------------------ |
| milk      | 乳制品   | Milk       | 牛奶、奶酪、黄油、奶油等       |
| egg       | 鸡蛋     | Egg        | 各种蛋类及其制品               |
| fish      | 鱼类     | Fish       | 各种鱼类及鱼制品               |
| shellfish | 甲壳类   | Shellfish  | 虾、蟹、贝类等海鲜             |
| peanut    | 花生     | Peanut     | 花生及花生制品                 |
| tree_nut  | 树坚果   | Tree Nuts  | 杏仁、核桃、腰果等             |
| wheat     | 小麦     | Wheat      | 面粉、面条、面包等含麸质食品   |
| soy       | 大豆     | Soy        | 豆腐、豆浆、酱油等豆制品       |

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

### 9.1 更新饮食记录 ⭐

**接口地址**: `PUT /api/food/diet/{record_id}`

**接口描述**: 更新指定的饮食记录（支持部分更新，只能操作自己的记录）

**路径参数**:
| 参数名    | 类型 | 必填 | 说明   |
| --------- | ---- | ---- | ------ |
| record_id | int  | 是   | 记录ID |

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名     | 类型         | 必填 | 说明                                                      |
| ---------- | ------------ | ---- | --------------------------------------------------------- |
| userId     | int          | 是   | 用户ID（用于权限校验）                                    |
| foodName   | string\|null | 否   | 菜品名称，1-100个字符                                     |
| calories   | float\|null  | 否   | 热量（kcal），≥0                                          |
| protein    | float\|null  | 否   | 蛋白质（g），≥0                                           |
| fat        | float\|null  | 否   | 脂肪（g），≥0                                             |
| carbs      | float\|null  | 否   | 碳水化合物（g），≥0                                       |
| mealType   | string\|null | 否   | 餐次：早餐/午餐/晚餐/加餐 或 breakfast/lunch/dinner/snack |
| recordDate | string\|null | 否   | 记录日期（YYYY-MM-DD格式）                                |

**请求示例**:
```bash
PUT http://localhost:8000/api/food/diet/1
Content-Type: application/json

{
  "userId": 123,
  "foodName": "更新的菜名",
  "calories": 300.0
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "id": 1,
    "foodName": "更新的菜名",
    "calories": 300.0,
    "protein": 28.0,
    "fat": 18.0,
    "carbs": 15.0,
    "mealType": "lunch",
    "recordDate": "2026-01-23"
  }
}
```

**错误响应**:

*记录不存在*（HTTP 404）:
```json
{
  "detail": "饮食记录不存在，record_id: 1"
}
```

*无权操作*（HTTP 403）:
```json
{
  "detail": "无权操作此记录，只能修改自己的饮食记录"
}
```

*日期格式错误*（HTTP 400）:
```json
{
  "detail": "日期格式错误，请使用 YYYY-MM-DD 格式"
}
```

---

### 9.2 删除饮食记录 ⭐

**接口地址**: `DELETE /api/food/diet/{record_id}`

**接口描述**: 删除指定的饮食记录（只能删除自己的记录）

**路径参数**:
| 参数名    | 类型 | 必填 | 说明   |
| --------- | ---- | ---- | ------ |
| record_id | int  | 是   | 记录ID |

**请求参数**:
| 参数名 | 类型 | 必填 | 说明                   |
| ------ | ---- | ---- | ---------------------- |
| userId | int  | 是   | 用户ID（用于权限校验） |

**请求示例**:
```bash
DELETE http://localhost:8000/api/food/diet/1?userId=123
```

**响应示例**:
```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

**错误响应**:

*记录不存在*（HTTP 404）:
```json
{
  "detail": "饮食记录不存在，record_id: 1"
}
```

*无权操作*（HTTP 403）:
```json
{
  "detail": "无权操作此记录，只能删除自己的饮食记录"
}
```

---

### 9.3 检测菜品过敏原 ⭐

**接口地址**: `POST /api/food/allergen/check`

**接口描述**: 检测菜品中的过敏原，支持八大类过敏原的关键词匹配检测

**八大类过敏原**:
1. 乳制品（milk）- 牛奶及其制品
2. 鸡蛋（egg）- 各种蛋类
3. 鱼类（fish）- 各种鱼类
4. 甲壳类（shellfish）- 虾、蟹、贝类等
5. 花生（peanut）- 花生及制品
6. 树坚果（tree_nut）- 杏仁、核桃、腰果等
7. 小麦（wheat）- 小麦及麸质食品
8. 大豆（soy）- 大豆及豆制品

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
| 参数名         | 类型          | 必填 | 说明                               |
| -------------- | ------------- | ---- | ---------------------------------- |
| food_name      | string        | 是   | 菜品名称，1-100个字符              |
| ingredients    | array\|null   | 否   | 配料列表，提供后检测更精确         |
| user_allergens | array\|null   | 否   | 用户的过敏原列表，用于匹配告警     |

**请求示例**:
```bash
POST http://localhost:8000/api/food/allergen/check
Content-Type: application/json

{
  "food_name": "宫保鸡丁",
  "ingredients": ["鸡肉", "花生", "辣椒", "葱"],
  "user_allergens": ["花生", "鸡蛋"]
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "检测完成",
  "data": {
    "food_name": "宫保鸡丁",
    "detected_allergens": [
      {
        "code": "peanut",
        "name": "花生",
        "name_en": "Peanut",
        "matched_keywords": ["花生", "宫保"],
        "confidence": "high"
      }
    ],
    "allergen_count": 1,
    "has_allergens": true,
    "warnings": [
      {
        "allergen": "花生",
        "level": "high",
        "message": "警告：检测到您的过敏原【花生】，匹配关键词：花生, 宫保"
      }
    ],
    "has_warnings": true,
    "ingredients": ["鸡肉", "花生", "辣椒", "葱"]
  }
}
```

**响应字段说明**:
| 字段                                | 类型    | 说明                         |
| ----------------------------------- | ------- | ---------------------------- |
| code                                | int     | 状态码，200表示成功          |
| message                             | string  | 响应消息                     |
| data.food_name                      | string  | 菜品名称                     |
| data.detected_allergens             | array   | 检测到的过敏原列表           |
| data.detected_allergens[].code      | string  | 过敏原代码                   |
| data.detected_allergens[].name      | string  | 过敏原中文名称               |
| data.detected_allergens[].name_en   | string  | 过敏原英文名称               |
| data.detected_allergens[].matched_keywords | array | 匹配到的关键词           |
| data.detected_allergens[].confidence | string | 置信度：high/medium/low     |
| data.allergen_count                 | int     | 检测到的过敏原数量           |
| data.has_allergens                  | bool    | 是否包含过敏原               |
| data.warnings                       | array   | 用户过敏原告警列表           |
| data.has_warnings                   | bool    | 是否有告警                   |
| data.ingredients                    | array   | 配料列表（如果提供）         |

---

### 9.4 获取过敏原类别列表 ⭐

**接口地址**: `GET /api/food/allergen/categories`

**接口描述**: 获取所有支持的过敏原类别信息

**请求示例**:
```bash
GET http://localhost:8000/api/food/allergen/categories
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "code": "milk",
      "name": "乳制品",
      "name_en": "Milk",
      "description": "包括牛奶及其制品，如奶酪、黄油、酸奶、奶油等"
    },
    {
      "code": "egg",
      "name": "鸡蛋",
      "name_en": "Egg",
      "description": "包括鸡蛋、鸭蛋、鹅蛋等各种蛋类及其制品"
    },
    {
      "code": "fish",
      "name": "鱼类",
      "name_en": "Fish",
      "description": "包括各种鱼类及鱼制品"
    },
    {
      "code": "shellfish",
      "name": "甲壳类",
      "name_en": "Shellfish",
      "description": "包括虾、蟹、贝类等甲壳类海鲜"
    },
    {
      "code": "peanut",
      "name": "花生",
      "name_en": "Peanut",
      "description": "包括花生及花生制品"
    },
    {
      "code": "tree_nut",
      "name": "树坚果",
      "name_en": "Tree Nuts",
      "description": "包括杏仁、核桃、腰果、榛子等树坚果及其制品"
    },
    {
      "code": "wheat",
      "name": "小麦",
      "name_en": "Wheat",
      "description": "包括小麦及其制品，含麸质食品"
    },
    {
      "code": "soy",
      "name": "大豆",
      "name_en": "Soy",
      "description": "包括大豆及其制品，如豆腐、豆浆、酱油等"
    }
  ]
}
```

**响应字段说明**:
| 字段              | 类型   | 说明             |
| ----------------- | ------ | ---------------- |
| code              | int    | 状态码           |
| message           | string | 响应消息         |
| data              | array  | 过敏原类别列表   |
| data[].code       | string | 过敏原代码       |
| data[].name       | string | 过敏原中文名称   |
| data[].name_en    | string | 过敏原英文名称   |
| data[].description| string | 过敏原描述       |

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
    "dailyBudget": 500,
    "weight": 70.5,
    "height": 175.0,
    "age": 25,
    "gender": "male"
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
| data.weight           | float\|null  | 体重（kg）                                              |
| data.height           | float\|null  | 身高（cm）                                              |
| data.age              | int\|null    | 年龄                                                    |
| data.gender           | string\|null | 性别：male/female/other                                 |

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
| weight           | float\|null  | 否   | 体重（kg），>0，≤500                                    |
| height           | float\|null  | 否   | 身高（cm），>0，≤300                                    |
| age              | int\|null    | 否   | 年龄，>0，≤150                                          |
| gender           | string\|null | 否   | 性别：male/female/other                                 |

**请求示例**:
```bash
PUT http://localhost:8000/api/user/preferences
Content-Type: application/json

{
  "userId": 123,
  "healthGoal": "reduce_fat",
  "allergens": ["海鲜", "花生"],
  "travelPreference": "self_driving",
  "dailyBudget": 500,
  "weight": 70.5,
  "height": 175.0,
  "age": 25,
  "gender": "male"
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
    "dailyBudget": 500,
    "weight": 70.5,
    "height": 175.0,
    "age": 25,
    "gender": "male"
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

### 9.5 上传餐前图片 ⭐

**接口地址**: `POST /api/food/meal/before`

**接口描述**: 上传餐前食物图片，AI自动识别菜品并估算份量和热量，创建对比记录

**请求头**:
```
Content-Type: multipart/form-data
```

**请求参数**:
| 参数名   | 类型   | 必填 | 说明                               |
| -------- | ------ | ---- | ---------------------------------- |
| image    | file   | 是   | 餐前食物图片（支持jpg, jpeg, png） |
| user_id  | int    | 是   | 用户ID                             |

**请求示例**:
```bash
POST http://localhost:8000/api/food/meal/before
Content-Type: multipart/form-data

# 使用 curl
curl -X POST http://localhost:8000/api/food/meal/before \
  -F "image=@before_meal.jpg" \
  -F "user_id=1"
```

**响应示例**:
```json
{
  "code": 200,
  "message": "餐前图片上传成功",
  "data": {
    "comparison_id": 1,
    "before_image_url": "/uploads/meal/before_1_abc123.jpg",
    "before_features": {
      "dishes": [
        {
          "name": "红烧肉",
          "estimated_weight": 200,
          "estimated_calories": 500.0,
          "estimated_protein": 25.0,
          "estimated_fat": 35.0,
          "estimated_carbs": 10.0
        },
        {
          "name": "清炒时蔬",
          "estimated_weight": 150,
          "estimated_calories": 80.0,
          "estimated_protein": 3.0,
          "estimated_fat": 5.0,
          "estimated_carbs": 8.0
        }
      ],
      "total_estimated_calories": 580.0,
      "total_estimated_protein": 28.0,
      "total_estimated_fat": 40.0,
      "total_estimated_carbs": 18.0
    },
    "status": "pending_after"
  }
}
```

**响应字段说明**:
| 字段                                      | 类型    | 说明                              |
| ----------------------------------------- | ------- | --------------------------------- |
| code                                      | int     | 状态码，200表示成功               |
| message                                   | string  | 响应消息                          |
| data.comparison_id                        | int     | 对比记录ID（用于后续餐后上传）    |
| data.before_image_url                     | string  | 餐前图片保存路径                  |
| data.before_features                      | object  | AI识别的菜品特征                  |
| data.before_features.dishes               | array   | 识别到的菜品列表                  |
| data.before_features.dishes[].name        | string  | 菜品名称                          |
| data.before_features.dishes[].estimated_weight | int | 估算重量（g）                    |
| data.before_features.dishes[].estimated_calories | float | 估算热量（kcal）              |
| data.before_features.dishes[].estimated_protein | float | 估算蛋白质（g）               |
| data.before_features.dishes[].estimated_fat | float | 估算脂肪（g）                   |
| data.before_features.dishes[].estimated_carbs | float | 估算碳水化合物（g）            |
| data.before_features.total_estimated_calories | float | 总估算热量（kcal）            |
| data.before_features.total_estimated_protein | float | 总估算蛋白质（g）              |
| data.before_features.total_estimated_fat  | float   | 总估算脂肪（g）                   |
| data.before_features.total_estimated_carbs | float  | 总估算碳水化合物（g）             |
| data.status                               | string  | 记录状态（pending_after表示等待餐后上传） |

**错误响应**:

*文件类型错误*（HTTP 400）:
```json
{
  "detail": "请上传图片文件（支持jpg, jpeg, png格式）"
}
```

*用户不存在*（HTTP 404）:
```json
{
  "detail": "用户不存在，user_id: 123"
}
```

---

### 9.6 上传餐后图片并计算净摄入 ⭐

**接口地址**: `POST /api/food/meal/after/{comparison_id}`

**接口描述**: 上传餐后食物图片，AI对比餐前餐后图片，计算剩余比例和净摄入热量

**Phase 12实现**: 餐后图片上传与对比计算

**路径参数**:
| 参数名        | 类型 | 必填 | 说明                           |
| ------------- | ---- | ---- | ------------------------------ |
| comparison_id | int  | 是   | 餐前上传时返回的对比记录ID     |

**请求头**:
```
Content-Type: multipart/form-data
```

**请求参数**:
| 参数名 | 类型 | 必填 | 说明                                 |
| ------ | ---- | ---- | ------------------------------------ |
| image  | file | 是   | 餐后食物图片（支持jpg, jpeg, png格式）|

**请求示例**:
```bash
curl -X POST http://localhost:8000/api/food/meal/after/1 \
  -F "image=@after_meal.jpg"
```

**响应示例**:
```json
{
  "code": 200,
  "message": "餐后图片上传成功，对比完成",
  "data": {
    "comparison_id": 1,
    "before_image_url": "/uploads/meal/before_1_abc123.jpg",
    "after_image_url": "/uploads/meal/after_1_1_def456.jpg",
    "consumption_ratio": 0.75,
    "original_calories": 580.0,
    "net_calories": 435.0,
    "original_protein": 28.0,
    "original_fat": 40.0,
    "original_carbs": 18.0,
    "net_protein": 21.0,
    "net_fat": 30.0,
    "net_carbs": 13.5,
    "comparison_analysis": "您吃掉了约75%的食物，红烧肉剩余约1/4，蔬菜全部吃完。",
    "status": "completed"
  }
}
```

**响应字段说明**:
| 字段                     | 类型   | 说明                                    |
| ------------------------ | ------ | --------------------------------------- |
| code                     | int    | 状态码，200表示成功                     |
| message                  | string | 响应消息                                |
| data.comparison_id       | int    | 对比记录ID                              |
| data.before_image_url    | string | 餐前图片路径                            |
| data.after_image_url     | string | 餐后图片路径                            |
| data.consumption_ratio   | float  | 消耗比例（0-1，1表示全部吃完）          |
| data.original_calories   | float  | 原始估算热量（kcal）                    |
| data.net_calories        | float  | 净摄入热量 = 原始热量 × 消耗比例        |
| data.original_protein    | float  | 原始蛋白质（g）                         |
| data.original_fat        | float  | 原始脂肪（g）                           |
| data.original_carbs      | float  | 原始碳水化合物（g）                     |
| data.net_protein         | float  | 净摄入蛋白质（g）                       |
| data.net_fat             | float  | 净摄入脂肪（g）                         |
| data.net_carbs           | float  | 净摄入碳水化合物（g）                   |
| data.comparison_analysis | string | AI对比分析说明                          |
| data.status              | string | 记录状态（completed表示对比完成）       |

**计算公式**:
- 消耗比例 = 1 - 剩余比例
- 净摄入热量 = 原始热量 × 消耗比例
- 净摄入蛋白质 = 原始蛋白质 × 消耗比例
- 净摄入脂肪 = 原始脂肪 × 消耗比例
- 净摄入碳水化合物 = 原始碳水化合物 × 消耗比例

**错误响应**:

*文件类型错误*（HTTP 400）:
```json
{
  "detail": "请上传图片文件（支持jpg, jpeg, png格式）"
}
```

*对比记录不存在*（HTTP 404）:
```json
{
  "detail": "对比记录不存在，comparison_id: 99999"
}
```

*重复上传*（HTTP 400）:
```json
{
  "detail": "该对比记录已完成，请勿重复上传"
}
```

*状态异常*（HTTP 400）:
```json
{
  "detail": "对比记录状态异常: pending_before"
}
```

---

### 17. 每日热量统计 ⭐

**接口地址**: `GET /api/stats/calories/daily`

**接口描述**: 获取指定用户在指定日期的热量摄入和消耗统计

**请求参数**:
| 参数名 | 类型   | 必填 | 说明                     |
| ------ | ------ | ---- | ------------------------ |
| userId | int    | 是   | 用户ID，>0               |
| date   | string | 是   | 统计日期（YYYY-MM-DD格式）|

**请求示例**:
```bash
GET http://localhost:8000/api/stats/calories/daily?userId=1&date=2026-02-04
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "date": "2026-02-04",
    "user_id": 1,
    "intake_calories": 1800.0,
    "meal_count": 3,
    "burn_calories": 500.0,
    "exercise_count": 2,
    "exercise_duration": 60,
    "net_calories": 1300.0,
    "meal_breakdown": {
      "breakfast": 400.0,
      "lunch": 700.0,
      "dinner": 600.0,
      "snack": 100.0
    }
  }
}
```

**响应字段说明**:
| 字段                       | 类型   | 说明                                   |
| -------------------------- | ------ | -------------------------------------- |
| code                       | int    | 状态码，200表示成功                    |
| message                    | string | 响应消息                               |
| data.date                  | string | 统计日期                               |
| data.user_id               | int    | 用户ID                                 |
| data.intake_calories       | float  | 摄入热量（kcal，来自饮食记录）         |
| data.meal_count            | int    | 餐次数量                               |
| data.burn_calories         | float  | 消耗热量（kcal，来自运动计划）         |
| data.exercise_count        | int    | 运动项目数量                           |
| data.exercise_duration     | int    | 运动总时长（分钟）                     |
| data.net_calories          | float  | 净热量（摄入-消耗）                    |
| data.meal_breakdown        | object | 餐次分类统计（早餐/午餐/晚餐/加餐）    |

**错误响应**:
- 日期格式错误（HTTP 400）:
```json
{
  "detail": "日期格式错误，请使用 YYYY-MM-DD 格式，收到: invalid-date"
}
```

---

### 18. 每周热量统计 ⭐

**接口地址**: `GET /api/stats/calories/weekly`

**接口描述**: 获取指定用户在指定周的热量摄入和消耗统计

**请求参数**:
| 参数名     | 类型   | 必填 | 说明                         |
| ---------- | ------ | ---- | ---------------------------- |
| userId     | int    | 是   | 用户ID，>0                   |
| week_start | string | 是   | 周起始日期（YYYY-MM-DD格式） |

**请求示例**:
```bash
GET http://localhost:8000/api/stats/calories/weekly?userId=1&week_start=2026-02-03
```

**响应示例**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "week_start": "2026-02-03",
    "week_end": "2026-02-09",
    "user_id": 1,
    "total_intake": 12600.0,
    "total_burn": 3500.0,
    "total_net": 9100.0,
    "avg_intake": 1800.0,
    "avg_burn": 500.0,
    "avg_net": 1300.0,
    "total_meals": 21,
    "total_exercises": 14,
    "active_days": 7,
    "daily_breakdown": [
      {
        "date": "2026-02-03",
        "intake_calories": 1800.0,
        "burn_calories": 500.0,
        "net_calories": 1300.0
      }
    ]
  }
}
```

**响应字段说明**:
| 字段                              | 类型   | 说明                   |
| --------------------------------- | ------ | ---------------------- |
| code                              | int    | 状态码，200表示成功    |
| message                           | string | 响应消息               |
| data.week_start                   | string | 周起始日期             |
| data.week_end                     | string | 周结束日期             |
| data.user_id                      | int    | 用户ID                 |
| data.total_intake                 | float  | 周总摄入热量（kcal）   |
| data.total_burn                   | float  | 周总消耗热量（kcal）   |
| data.total_net                    | float  | 周净热量               |
| data.avg_intake                   | float  | 日均摄入热量（kcal）   |
| data.avg_burn                     | float  | 日均消耗热量（kcal）   |
| data.avg_net                      | float  | 日均净热量             |
| data.total_meals                  | int    | 周总餐次               |
| data.total_exercises              | int    | 周总运动次数           |
| data.active_days                  | int    | 有记录的天数           |
| data.daily_breakdown              | array  | 每日明细（7天）        |
| data.daily_breakdown[].date       | string | 日期                   |
| data.daily_breakdown[].intake_calories | float | 当日摄入热量      |
| data.daily_breakdown[].burn_calories   | float | 当日消耗热量      |
| data.daily_breakdown[].net_calories    | float | 当日净热量        |

**错误响应**:
- 日期格式错误（HTTP 400）:
```json
{
  "detail": "日期格式错误，请使用 YYYY-MM-DD 格式，收到: invalid-date"
}
```

---

## 更新日志

### v1.4.0 (2026-02-04)
- ✅ 添加每日热量统计接口 `/api/stats/calories/daily`（Phase 15）
- ✅ 添加每周热量统计接口 `/api/stats/calories/weekly`（Phase 15）
- ✅ 统计摄入热量（来自饮食记录）和消耗热量（来自运动计划）
- ✅ 支持餐次分类统计和每日明细

### v1.3.0 (2026-02-04)
- ✅ 添加餐后图片上传接口 `/api/food/meal/after/{comparison_id}`（Phase 12）
- ✅ 实现AI餐前餐后图片对比（Qwen-VL）
- ✅ 计算消耗比例和净摄入热量
- ✅ 创建meal_comparison_service处理对比逻辑

### v1.2.0 (2026-02-04)
- ✅ 添加餐前图片上传接口 `/api/food/meal/before`（Phase 11）
- ✅ 实现AI图片特征提取（菜品识别、份量估算、热量估算）
- ✅ 创建MealComparison数据模型用于餐前餐后对比

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

