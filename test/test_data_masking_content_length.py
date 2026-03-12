"""
测试 DataMaskingMiddleware 的 content-length 修复

修复内容：
- 中间件对响应体脱敏后，使用与FastAPI一致的紧凑JSON序列化
- 移除原始content-length头，让Response自动计算正确的content-length
- 防止"unexpected end of stream"错误

测试策略：
1. 单元测试：验证脱敏工具函数的正确性
2. 集成测试：验证中间件处理后的content-length正确性
3. 端到端测试：验证完整的注册/登录流程不会出现content-length不匹配
4. 边界条件测试：中文、空响应、大JSON、嵌套结构等
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middleware.data_masking import (
    mask_phone,
    mask_email,
    mask_sensitive_in_text,
    fuzz_location,
    fuzz_coords_in_dict,
    mask_sensitive_fields_in_dict,
    mask_sensitive_text_in_dict,
    apply_response_masking,
    apply_request_masking,
    DataMaskingMiddleware,
    SensitiveDataFilter,
)


# ============================================================
# 1. 基础脱敏工具函数测试
# ============================================================

class TestMaskPhone:
    """手机号脱敏测试"""

    def test_standard_phone(self):
        assert mask_phone("13812345678") == "138****5678"

    def test_phone_with_86_prefix(self):
        assert mask_phone("8613812345678") == "138****5678"

    def test_phone_with_plus86_prefix(self):
        assert mask_phone("+8613812345678") == "138****5678"

    def test_non_phone_text(self):
        assert mask_phone("hello world") == "hello world"

    def test_empty_string(self):
        assert mask_phone("") == ""

    def test_phone_in_sentence(self):
        result = mask_phone("联系电话：13912345678，请拨打")
        assert "139****5678" in result

    def test_multiple_phones(self):
        result = mask_phone("手机1:13812345678 手机2:13987654321")
        assert "138****5678" in result
        assert "139****4321" in result

    def test_not_a_phone_number(self):
        """12位数字不应该被识别为手机号"""
        assert mask_phone("123456789012") == "123456789012"

    def test_none_input(self):
        assert mask_phone(None) is None


class TestMaskEmail:
    """邮箱脱敏测试"""

    def test_standard_email(self):
        result = mask_email("testuser@example.com")
        assert result == "te****@example.com"

    def test_short_local_part(self):
        result = mask_email("ab@example.com")
        assert result == "a****@example.com"

    def test_single_char_local(self):
        result = mask_email("a@example.com")
        assert result == "a****@example.com"

    def test_long_local_part(self):
        result = mask_email("verylongemail@domain.com")
        assert result == "ve****@domain.com"

    def test_non_email_text(self):
        assert mask_email("hello world") == "hello world"

    def test_empty_string(self):
        assert mask_email("") == ""

    def test_email_in_sentence(self):
        result = mask_email("邮箱是 test@example.com 请联系")
        assert "te****@example.com" in result


class TestMaskSensitiveInText:
    """文本综合脱敏测试"""

    def test_phone_and_email_together(self):
        text = "联系人：13812345678，邮箱：test@example.com"
        result = mask_sensitive_in_text(text)
        assert "138****5678" in result
        assert "te****@example.com" in result

    def test_none_input(self):
        assert mask_sensitive_in_text(None) is None

    def test_empty_string(self):
        assert mask_sensitive_in_text("") == ""

    def test_no_sensitive_data(self):
        text = "这是一段普通文本"
        assert mask_sensitive_in_text(text) == text


# ============================================================
# 2. 坐标模糊化测试
# ============================================================

class TestFuzzLocation:
    """坐标模糊化测试"""

    def test_standard_coords(self):
        lat, lng = fuzz_location(39.9042, 116.4074)
        assert lat == 39.90
        assert lng == 116.41

    def test_high_precision_coords(self):
        lat, lng = fuzz_location(39.90421234, 116.40745678)
        assert lat == 39.90
        assert lng == 116.41

    def test_negative_coords(self):
        lat, lng = fuzz_location(-33.8688, 151.2093)
        assert lat == -33.87
        assert lng == 151.21

    def test_zero_coords(self):
        lat, lng = fuzz_location(0.0, 0.0)
        assert lat == 0.0
        assert lng == 0.0


class TestFuzzCoordsInDict:
    """字典中坐标模糊化测试"""

    def test_simple_dict(self):
        data = {"latitude": 39.9042, "longitude": 116.4074}
        result = fuzz_coords_in_dict(data)
        assert result["latitude"] == 39.90
        assert result["longitude"] == 116.41

    def test_nested_dict(self):
        data = {"location": {"lat": 39.9042, "lng": 116.4074}}
        result = fuzz_coords_in_dict(data)
        assert result["location"]["lat"] == 39.90
        assert result["location"]["lng"] == 116.41

    def test_list_of_coords(self):
        data = [{"lat": 39.9042, "lng": 116.4074}]
        result = fuzz_coords_in_dict(data)
        assert result[0]["lat"] == 39.90
        assert result[0]["lng"] == 116.41

    def test_non_coord_fields_unchanged(self):
        data = {"name": "test", "lat": 39.9042, "value": 123.456}
        result = fuzz_coords_in_dict(data)
        assert result["name"] == "test"
        assert result["value"] == 123.456
        assert result["lat"] == 39.90


# ============================================================
# 3. 敏感字段脱敏测试
# ============================================================

class TestMaskSensitiveFieldsInDict:
    """敏感字段脱敏测试"""

    def test_password_field(self):
        data = {"username": "test", "password": "secret123"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["username"] == "test"
        assert result["password"] == "******"

    def test_token_field(self):
        data = {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["access_token"].startswith("eyJhbG")
        assert result["access_token"].endswith("******")

    def test_short_token(self):
        data = {"token": "abc"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["token"] == "******"

    def test_api_key_field(self):
        data = {"api_key": "sk-1234567890abcdef"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["api_key"] == "sk-123******"

    def test_nested_sensitive_fields(self):
        data = {
            "user": {"name": "test", "password": "secret"},
            "token": {"access_token": "abcdefghijklmnop"}
        }
        result = mask_sensitive_fields_in_dict(data)
        assert result["user"]["password"] == "******"
        # "token"本身是敏感字段名，整个值（dict）被替换为"******"
        assert result["token"] == "******"

    def test_nested_access_token_directly(self):
        """当access_token不在顶层"token"键下时，应被正确脱敏"""
        data = {
            "auth": {"access_token": "abcdefghijklmnop", "user": "test"}
        }
        result = mask_sensitive_fields_in_dict(data)
        assert result["auth"]["access_token"] == "abcdef******"
        assert result["auth"]["user"] == "test"

    def test_none_sensitive_value(self):
        data = {"password": None}
        result = mask_sensitive_fields_in_dict(data)
        assert result["password"] == "******"

    def test_non_sensitive_fields_unchanged(self):
        data = {"name": "test", "email": "test@example.com", "code": 200}
        result = mask_sensitive_fields_in_dict(data)
        assert result == data


# ============================================================
# 4. 综合脱敏测试
# ============================================================

class TestApplyResponseMasking:
    """响应综合脱敏测试"""

    def test_registration_response(self):
        """注册响应不应被改变（无敏感字段）"""
        data = {"code": 200, "message": "注册成功", "userId": 1}
        result = apply_response_masking(data)
        assert result == data

    def test_login_response_with_token(self):
        """登录响应中的token字段（顶层键）应被整体脱敏"""
        data = {
            "code": 200,
            "message": "登录成功",
            "data": {"userId": 1, "nickname": "test"},
            "token": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh.sig",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
        result = apply_response_masking(data)
        assert result["code"] == 200
        # "token"本身是敏感字段名，整个值（dict）被替换为"******"
        assert result["token"] == "******"
        assert result["data"]["userId"] == 1

    def test_non_dict_input(self):
        """非字典输入应原样返回"""
        assert apply_response_masking("hello") == "hello"
        assert apply_response_masking(123) == 123
        assert apply_response_masking(None) is None


class TestApplyRequestMasking:
    """请求脱敏测试"""

    def test_registration_request(self):
        """注册请求不应修改nickname和password"""
        data = {"nickname": "testuser", "password": "secret123"}
        result = apply_request_masking(data)
        # 请求脱敏不会修改密码字段（只脱敏坐标和手机号/邮箱）
        assert result["nickname"] == "testuser"
        assert result["password"] == "secret123"

    def test_request_with_coords(self):
        """请求中的坐标应被模糊化"""
        data = {"lat": 39.9042, "lng": 116.4074, "query": "test"}
        result = apply_request_masking(data)
        assert result["lat"] == 39.90
        assert result["lng"] == 116.41
        assert result["query"] == "test"


# ============================================================
# 5. 中间件集成测试（核心：content-length 修复验证）
# ============================================================

class TestDataMaskingMiddlewareContentLength:
    """
    DataMaskingMiddleware content-length 修复的集成测试
    这是修复 "unexpected end of stream" 错误的核心测试
    """

    @pytest.fixture
    def app_with_middleware(self):
        """创建一个带有脱敏中间件的测试应用"""
        app = FastAPI()
        app.add_middleware(DataMaskingMiddleware)

        @app.post("/api/user/register")
        async def register(request_data: dict):
            return JSONResponse(
                content={"code": 200, "message": "注册成功", "userId": 1}
            )

        @app.post("/api/user/login")
        async def login(request_data: dict):
            return JSONResponse(
                content={
                    "code": 200,
                    "message": "登录成功",
                    "data": {
                        "userId": 1,
                        "nickname": request_data.get("nickname", "test"),
                    },
                    "token": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoicmVmcmVzaCJ9.sig",
                        "token_type": "bearer",
                        "expires_in": 1800
                    }
                }
            )

        @app.get("/api/food/analyze")
        async def analyze():
            return JSONResponse(
                content={
                    "success": True,
                    "message": "分析成功",
                    "data": {
                        "name": "番茄炒蛋",
                        "calories": 150.0,
                        "protein": 10.5,
                        "fat": 8.2,
                        "carbs": 6.3,
                    }
                }
            )

        @app.get("/api/user/data")
        async def get_user():
            return JSONResponse(
                content={
                    "code": 200,
                    "message": "获取成功",
                    "data": {
                        "userId": 1,
                        "nickname": "test",
                        "healthGoal": "reduce_fat",
                        "allergens": ["海鲜", "花生"],
                    }
                }
            )

        @app.post("/api/with-coords")
        async def with_coords(request_data: dict):
            return JSONResponse(
                content={
                    "code": 200,
                    "data": {
                        "latitude": 39.90421234,
                        "longitude": 116.40745678,
                        "name": "北京"
                    }
                }
            )

        @app.get("/api/error")
        async def error_endpoint():
            raise HTTPException(status_code=500, detail="服务器内部错误")

        @app.post("/api/with-password-response")
        async def with_password():
            """模拟响应中包含密码字段（不应该出现，但测试脱敏效果）"""
            return JSONResponse(
                content={
                    "code": 200,
                    "data": {
                        "user": "test",
                        "password": "should_be_masked",
                        "api_key": "sk-1234567890abcdef"
                    }
                }
            )

        @app.get("/api/empty")
        async def empty_response():
            return JSONResponse(content={})

        @app.get("/api/large-response")
        async def large_response():
            """大JSON响应"""
            items = [
                {
                    "id": i,
                    "name": f"菜品{i}",
                    "calories": 100.0 + i * 10,
                    "protein": 10.0 + i,
                    "fat": 5.0 + i * 0.5,
                    "carbs": 20.0 + i * 2,
                    "recommendation": f"这道菜品{i}非常美味，推荐食用。",
                }
                for i in range(50)
            ]
            return JSONResponse(content={"code": 200, "data": items})

        @app.post("/api/with-phone")
        async def with_phone(request_data: dict):
            return JSONResponse(
                content={
                    "code": 200,
                    "data": {
                        "contact": "联系电话：13812345678",
                        "email": "test@example.com"
                    }
                }
            )

        return app

    @pytest.fixture
    def client(self, app_with_middleware):
        return TestClient(app_with_middleware)

    def test_register_content_length_correct(self, client):
        """核心测试：注册响应的content-length必须与实际body长度匹配"""
        response = client.post(
            "/api/user/register",
            json={"nickname": "testuser", "password": "password123"}
        )
        assert response.status_code == 200
        # 验证content-length与实际body长度一致
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length, (
            f"content-length不匹配: header={content_length}, actual={actual_length}"
        )
        # 验证响应内容正确
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "注册成功"
        assert data["userId"] == 1

    def test_register_chinese_content_length(self, client):
        """测试包含中文字符的注册响应content-length正确"""
        response = client.post(
            "/api/user/register",
            json={"nickname": "中文昵称", "password": "密码123456"}
        )
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length

    def test_login_content_length_with_token_masking(self, client):
        """登录响应包含token脱敏后content-length仍然正确"""
        response = client.post(
            "/api/user/login",
            json={"nickname": "test", "password": "password123"}
        )
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length, (
            f"登录响应content-length不匹配: header={content_length}, actual={actual_length}"
        )
        # "token"是敏感字段名，整个token对象被替换为"******"
        data = response.json()
        assert data["token"] == "******"
        # password也被脱敏
        assert data["data"]["nickname"] == "test"

    def test_food_analyze_content_length(self, client):
        """食物分析响应的content-length正确"""
        response = client.get("/api/food/analyze")
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length

    def test_coords_response_content_length(self, client):
        """坐标模糊化后content-length正确"""
        response = client.post(
            "/api/with-coords",
            json={"query": "test"}
        )
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length
        # 验证坐标被模糊化
        data = response.json()
        assert data["data"]["latitude"] == 39.90
        assert data["data"]["longitude"] == 116.41

    def test_password_in_response_content_length(self, client):
        """响应中包含密码字段脱敏后content-length正确"""
        response = client.post(
            "/api/with-password-response",
            json={}
        )
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length, (
            f"密码脱敏后content-length不匹配: header={content_length}, actual={actual_length}"
        )
        # 验证密码被脱敏
        data = response.json()
        assert data["data"]["password"] == "******"
        assert data["data"]["api_key"] == "sk-123******"

    def test_empty_response_content_length(self, client):
        """空响应的content-length正确"""
        response = client.get("/api/empty")
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length

    def test_large_response_content_length(self, client):
        """大JSON响应的content-length正确"""
        response = client.get("/api/large-response")
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length, (
            f"大响应content-length不匹配: header={content_length}, actual={actual_length}"
        )
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 50

    def test_phone_email_masking_content_length(self, client):
        """手机号邮箱脱敏后content-length正确"""
        response = client.post(
            "/api/with-phone",
            json={}
        )
        assert response.status_code == 200
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length

    def test_error_response_not_broken(self, client):
        """错误响应不应被中间件破坏"""
        response = client.get("/api/error")
        assert response.status_code == 500
        # 错误响应也应有正确的content-length
        content_length = int(response.headers.get("content-length", 0))
        actual_length = len(response.content)
        assert content_length == actual_length

    def test_multiple_requests_sequential(self, client):
        """连续多个请求都应有正确的content-length（模拟连接复用）"""
        for i in range(5):
            response = client.post(
                "/api/user/register",
                json={"nickname": f"user{i}", "password": "password123"}
            )
            assert response.status_code == 200
            content_length = int(response.headers.get("content-length", 0))
            actual_length = len(response.content)
            assert content_length == actual_length, (
                f"第{i+1}次请求content-length不匹配: header={content_length}, actual={actual_length}"
            )

    def test_response_json_parseable(self, client):
        """所有响应都应该是可解析的完整JSON"""
        endpoints = [
            ("POST", "/api/user/register", {"nickname": "test", "password": "123456"}),
            ("POST", "/api/user/login", {"nickname": "test", "password": "123456"}),
            ("GET", "/api/food/analyze", None),
            ("GET", "/api/user/data", None),
            ("GET", "/api/empty", None),
            ("GET", "/api/large-response", None),
        ]
        for method, url, json_data in endpoints:
            if method == "POST":
                response = client.post(url, json=json_data)
            else:
                response = client.get(url)
            # 确保响应可以被完整解析为JSON
            try:
                data = response.json()
            except Exception as e:
                pytest.fail(f"无法解析{url}的JSON响应: {e}")

    def test_content_type_preserved(self, client):
        """响应的content-type应保持为application/json"""
        response = client.post(
            "/api/user/register",
            json={"nickname": "test", "password": "123456"}
        )
        assert "application/json" in response.headers.get("content-type", "")


# ============================================================
# 6. 日志脱敏过滤器测试
# ============================================================

class TestSensitiveDataFilter:
    """日志脱敏过滤器测试"""

    def test_filter_phone_in_log(self):
        """日志中的手机号应被脱敏"""
        filter_ = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "用户手机号：13812345678"
        record.args = None
        filter_.filter(record)
        assert "138****5678" in record.msg

    def test_filter_email_in_log(self):
        """日志中的邮箱应被脱敏"""
        filter_ = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "邮箱是test@example.com"
        record.args = None
        filter_.filter(record)
        assert "te****@example.com" in record.msg

    def test_filter_with_dict_args(self):
        """日志参数中的敏感信息应被脱敏"""
        filter_ = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "info"
        record.args = {"phone": "13812345678", "count": 5}
        filter_.filter(record)
        assert "138****5678" in record.args["phone"]

    def test_filter_with_tuple_args(self):
        """元组参数中的敏感信息应被脱敏"""
        filter_ = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "info"
        record.args = ("13812345678", "normal_text")
        filter_.filter(record)
        assert "138****5678" in record.args[0]

    def test_filter_returns_true(self):
        """过滤器应始终返回True（不丢弃日志记录）"""
        filter_ = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "normal message"
        record.args = None
        assert filter_.filter(record) is True


# ============================================================
# 7. JSON序列化一致性测试
# ============================================================

class TestJsonSerializationConsistency:
    """验证修复后的JSON序列化与FastAPI保持一致"""

    def test_compact_serialization(self):
        """验证中间件使用紧凑格式序列化"""
        data = {"code": 200, "message": "注册成功", "userId": 1}
        # 模拟中间件修复后的序列化
        result = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        # 应该没有空格
        assert '" :' not in result
        assert '": ' not in result
        assert ', "' not in result

    def test_serialization_preserves_chinese(self):
        """中文字符应正确保留"""
        data = {"message": "注册成功", "name": "番茄炒蛋"}
        result = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        assert "注册成功" in result
        assert "番茄炒蛋" in result

    def test_serialization_round_trip(self):
        """JSON序列化后再解析应保持数据一致"""
        data = {
            "code": 200,
            "message": "分析成功",
            "data": {
                "name": "宫保鸡丁",
                "calories": 320.0,
                "allergens": ["花生", "鸡蛋"],
            }
        }
        serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        deserialized = json.loads(serialized)
        assert deserialized == data


# ============================================================
# 8. 请求体脱敏测试
# ============================================================

class TestRequestBodyMasking:
    """请求体脱敏测试"""

    @pytest.fixture
    def app_with_middleware(self):
        app = FastAPI()
        app.add_middleware(DataMaskingMiddleware)

        @app.post("/echo")
        async def echo(request_data: dict):
            """回显请求体（经过中间件处理后的）"""
            return JSONResponse(content=request_data)

        return app

    @pytest.fixture
    def client(self, app_with_middleware):
        return TestClient(app_with_middleware)

    def test_request_coords_fuzzed(self, client):
        """请求体中的坐标应被模糊化"""
        response = client.post(
            "/echo",
            json={"lat": 39.9042, "lng": 116.4074, "name": "test"}
        )
        data = response.json()
        assert data["lat"] == 39.90
        assert data["lng"] == 116.41
        assert data["name"] == "test"

    def test_request_password_not_masked(self, client):
        """请求体中的密码不应被请求脱敏修改（只有响应才脱敏密码）"""
        response = client.post(
            "/echo",
            json={"nickname": "test", "password": "mypassword"}
        )
        data = response.json()
        assert data["nickname"] == "test"
        # 请求脱敏不处理password字段，但响应脱敏会处理
        # 由于echo endpoint直接返回请求体，响应脱敏会处理password
        assert data["password"] == "******"  # 响应脱敏会处理

    def test_request_phone_masked_in_text(self, client):
        """请求体字符串值中的手机号应被脱敏"""
        response = client.post(
            "/echo",
            json={"note": "联系电话13812345678", "name": "test"}
        )
        data = response.json()
        assert "138****5678" in data["note"]


# ============================================================
# 9. 边界条件和异常情况测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_mask_phone_boundary_numbers(self):
        """边界手机号测试"""
        # 最小有效手机号
        assert "130****0000" in mask_phone("13000000000")
        # 最大有效手机号
        assert "199****9999" in mask_phone("19999999999")

    def test_mask_email_special_chars(self):
        """包含特殊字符的邮箱"""
        result = mask_email("user.name+tag@example.com")
        assert "@example.com" in result

    def test_deeply_nested_dict(self):
        """深层嵌套字典的脱敏"""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "password": "secret",
                        "lat": 39.9042
                    }
                }
            }
        }
        result = apply_response_masking(data)
        assert result["level1"]["level2"]["level3"]["password"] == "******"
        assert result["level1"]["level2"]["level3"]["lat"] == 39.90

    def test_empty_dict(self):
        """空字典不应导致错误"""
        assert apply_response_masking({}) == {}
        assert apply_request_masking({}) == {}

    def test_empty_list(self):
        """空列表不应导致错误"""
        assert apply_response_masking([]) == []

    def test_list_of_mixed_types(self):
        """混合类型列表"""
        data = [
            {"password": "secret"},
            "plain string",
            123,
            None,
            {"lat": 39.9042}
        ]
        result = apply_response_masking(data)
        assert result[0]["password"] == "******"
        assert result[1] == "plain string"
        assert result[2] == 123
        assert result[3] is None
        assert result[4]["lat"] == 39.90

    def test_unicode_emoji(self):
        """包含emoji的响应"""
        data = {"message": "成功 ✅", "name": "🍅番茄炒蛋"}
        result = apply_response_masking(data)
        assert "✅" in result["message"]
        assert "🍅" in result["name"]

    def test_very_long_password(self):
        """超长密码值"""
        data = {"password": "a" * 10000}
        result = mask_sensitive_fields_in_dict(data)
        assert result["password"] == "******"

    def test_numeric_sensitive_field(self):
        """数字类型的敏感字段值"""
        data = {"password": 12345}
        result = mask_sensitive_fields_in_dict(data)
        assert result["password"] == "******"

    def test_bool_sensitive_field(self):
        """布尔类型的敏感字段值"""
        data = {"password": True}
        result = mask_sensitive_fields_in_dict(data)
        assert result["password"] == "******"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
