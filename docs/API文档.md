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

