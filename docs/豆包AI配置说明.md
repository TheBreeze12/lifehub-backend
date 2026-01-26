# 豆包AI配置说明

## 📋 概述

菜单识别和菜品分析功能现在使用**火山引擎豆包AI**，其他功能（行程生成）继续使用**通义千问**。

## 🔑 获取API Key

### 1. 注册火山引擎账号

1. 访问 https://www.volcengine.com/
2. 注册/登录账号

### 2. 开通豆包AI服务

1. 进入控制台
2. 找到"豆包AI"或"ARK"服务
3. 开通服务并获取API Key

### 3. 配置环境变量

在 `.env` 文件中添加：

```bash
# 通义千问API Key（用于行程生成）
DASHSCOPE_API_KEY=sk-你的通义千问API_Key

# 火山引擎豆包AI API Key（用于菜单识别和菜品分析）
ARK_API_KEY=你的豆包AI_API_Key
```

## 📦 安装依赖

```bash
pip install --upgrade "volcengine-python-sdk[ark]"
```

或者使用requirements.txt：

```bash
pip install -r requirements.txt
```

## ✅ 验证配置

启动服务后，查看控制台输出：

- 如果看到 `✓ 火山引擎豆包AI初始化成功`，说明配置正确
- 如果看到警告信息，说明需要配置ARK_API_KEY

## 🔄 回退机制

如果豆包AI不可用或调用失败，系统会自动回退到通义千问：

- **菜单识别**：豆包AI失败 → 使用通义千问Qwen-VL
- **菜品分析**：豆包AI失败 → 使用通义千问Qwen-Turbo

## 📝 注意事项

1. **图片格式**：豆包AI使用base64 data URI格式传递图片
2. **API限制**：注意豆包AI的调用频率和额度限制
3. **响应格式**：代码已处理多种响应格式，确保兼容性

## 🧪 测试

使用测试脚本验证配置：

```bash
python test_menu_recognize_simple.py image.png 1
```

如果豆包AI配置正确，会在日志中看到相关调用信息。

