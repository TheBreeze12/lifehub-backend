# 菜单图片识别API测试指南

## 📋 测试前准备

### 1. 确保后端服务已启动

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. 准备测试图片

准备一张菜单图片（JPG或PNG格式），可以是：
- 餐厅菜单照片
- 包含菜品名称的图片
- 建议图片大小不超过5MB

### 3. 确认API Key已配置

确保已设置 `DASHSCOPE_API_KEY` 环境变量。

---

## 🧪 测试方法

### 方法一：使用Swagger UI（最简单，推荐）

1. **打开API文档页面**
   ```
   http://localhost:8000/docs
   ```

2. **找到菜单识别接口**
   - 在接口列表中找到 `POST /api/food/recognize`
   - 点击展开查看接口详情

3. **测试接口**
   - 点击 "Try it out" 按钮
   - 在 `image` 字段点击 "Choose File" 选择菜单图片
   - （可选）在 `userId` 字段输入用户ID（如：1）
   - 点击 "Execute" 执行请求

4. **查看结果**
   - 在 "Responses" 部分查看返回的菜品列表
   - 每个菜品包含营养数据和推荐信息

**优点：**
- 无需编写代码
- 可视化界面
- 可以直接看到请求/响应格式

---

### 方法二：使用Python测试脚本

#### 2.1 完整测试脚本（交互式）

```bash
cd backend
python test_menu_recognize.py
```

脚本会：
- 检查后端服务是否运行
- 提示输入图片路径
- 测试基础识别（不带用户ID）
- 测试个性化识别（带用户ID）

**使用示例：**
```
请输入菜单图片路径（或按回车使用默认路径）:
图片路径: menu.jpg

测试1: 基础识别（不带用户健康目标）
...

测试2: 个性化识别（带用户健康目标）
请输入用户ID（按回车跳过，默认使用userId=1）:
用户ID: 1
...
```

#### 2.2 快速测试脚本（命令行）

```bash
# 基础测试（不带用户ID）
python test_menu_recognize_simple.py menu.jpg

# 带用户ID的测试
python test_menu_recognize_simple.py menu.jpg 1
```

**输出示例：**
```
正在识别: menu.jpg

✅ 识别成功！共 3 个菜品

  宫保鸡丁
    热量: 320.0 kcal | 蛋白质: 28.0g | 脂肪: 18.0g | 碳水: 15.0g
    推荐: ✅ 蛋白质丰富、热量较低，适合您的减脂目标

  麻婆豆腐
    热量: 180.0 kcal | 蛋白质: 12.0g | 脂肪: 10.0g | 碳水: 8.0g
    推荐: ✅ 营养均衡，适合日常食用

  红烧肉
    热量: 450.0 kcal | 蛋白质: 20.0g | 脂肪: 35.0g | 碳水: 12.0g
    推荐: ❌ 热量或脂肪含量较高，建议减少摄入
```

---

### 方法三：使用curl命令

```bash
# 基础测试（不带用户ID）
curl -X POST "http://localhost:8000/api/food/recognize" \
  -F "image=@menu.jpg"

# 带用户ID的测试
curl -X POST "http://localhost:8000/api/food/recognize" \
  -F "image=@menu.jpg" \
  -F "userId=1"
```

**Windows PowerShell 示例：**
```powershell
# 基础测试
curl.exe -X POST "http://localhost:8000/api/food/recognize" `
  -F "image=@menu.jpg"

# 带用户ID
curl.exe -X POST "http://localhost:8000/api/food/recognize" `
  -F "image=@menu.jpg" `
  -F "userId=1"
```

---

### 方法四：使用Postman/Apifox

1. **创建新请求**
   - 方法：`POST`
   - URL：`http://localhost:8000/api/food/recognize`

2. **设置请求体**
   - 选择 `form-data` 类型
   - 添加字段：
     - `image`：类型选择 `File`，选择菜单图片
     - `userId`：类型选择 `Text`，输入用户ID（可选）

3. **发送请求**
   - 点击 "Send"
   - 查看响应结果

---

### 方法五：使用Python代码测试

```python
import requests

# 准备图片文件
image_path = "menu.jpg"

# 发送请求
with open(image_path, 'rb') as f:
    files = {'image': ('menu.jpg', f, 'image/jpeg')}
    data = {'userId': 1}  # 可选
    
    response = requests.post(
        'http://localhost:8000/api/food/recognize',
        files=files,
        data=data
    )
    
    result = response.json()
    print(result)
```

---

## 📊 预期响应格式

### 成功响应

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
        "reason": "蛋白质丰富、热量较低，适合您的减脂目标"
      },
      {
        "name": "麻婆豆腐",
        "calories": 180.0,
        "protein": 12.0,
        "fat": 10.0,
        "carbs": 8.0,
        "isRecommended": true,
        "reason": "营养均衡，适合日常食用"
      }
    ]
  }
}
```

### 错误响应

```json
{
  "detail": "请上传图片文件"
}
```

或

```json
{
  "detail": "识别菜单失败: [错误信息]"
}
```

---

## ✅ 测试检查清单

- [ ] 后端服务已启动（http://localhost:8000）
- [ ] API Key已正确配置
- [ ] 已准备测试用的菜单图片
- [ ] 测试基础识别（不带userId）
- [ ] 测试个性化识别（带userId）
- [ ] 验证返回的菜品数据格式正确
- [ ] 验证推荐理由根据健康目标生成

---

## 🔍 测试场景

### 场景1：基础识别
- **输入**：菜单图片（不带userId）
- **预期**：识别菜品并返回营养数据，推荐理由为通用建议

### 场景2：减脂用户识别
- **输入**：菜单图片 + userId=1（用户健康目标为reduce_fat）
- **预期**：识别菜品，低热量高蛋白菜品标记为推荐

### 场景3：增肌用户识别
- **输入**：菜单图片 + userId=2（用户健康目标为gain_muscle）
- **预期**：高蛋白菜品标记为推荐

### 场景4：控糖用户识别
- **输入**：菜单图片 + userId=3（用户健康目标为control_sugar）
- **预期**：低碳水菜品标记为推荐

### 场景5：非菜单图片
- **输入**：普通照片（不是菜单）
- **预期**：返回空数组或错误提示

---

## ⚠️ 常见问题

### 1. 识别失败：返回空数组

**可能原因：**
- 图片不是菜单
- 图片质量太差
- 图片中文字不清晰

**解决方法：**
- 使用清晰的菜单照片
- 确保图片中有可见的菜品名称
- 尝试不同的菜单图片

### 2. API调用超时

**可能原因：**
- 网络问题
- API Key额度用完
- 图片太大

**解决方法：**
- 检查网络连接
- 确认API Key有效
- 压缩图片大小（建议<2MB）

### 3. 推荐理由不准确

**说明：**
- 推荐逻辑基于营养数据估算
- 实际菜品可能因制作方式不同而有差异
- 建议仅作为参考

---

## 📝 测试记录模板

```
测试时间: 2026-01-XX XX:XX
测试图片: menu.jpg
用户ID: 1
健康目标: reduce_fat

识别结果:
- 菜品数量: 3
- 推荐菜品: 2
- 不推荐菜品: 1

问题记录:
[记录测试中发现的问题]
```

---

## 🎯 下一步

测试通过后，可以：
1. 在前端集成此API
2. 优化识别准确率
3. 添加更多健康目标支持
4. 实现菜品推荐缓存

