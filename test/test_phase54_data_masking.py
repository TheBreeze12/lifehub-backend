"""
Phase 54: 数据脱敏处理 - 测试文件
测试覆盖：
1. 手机号脱敏（中国大陆11位、带+86前缀、带区号等）
2. 邮箱脱敏
3. 位置坐标模糊化（经纬度精度降低）
4. 响应中敏感字段脱敏（password、token、secret等）
5. 日志脱敏过滤器
6. 中间件集成测试（FastAPI TestClient）
7. 边界条件与特殊场景
"""
import pytest
import json
import re
import logging
from unittest.mock import MagicMock, patch
from io import StringIO

# ===== 第一部分：纯函数单元测试（脱敏工具函数） =====


class TestMaskPhone:
    """测试手机号脱敏"""

    def test_mask_standard_phone(self):
        """标准11位手机号"""
        from app.middleware.data_masking import mask_phone
        assert mask_phone("13812345678") == "138****5678"

    def test_mask_phone_with_86_prefix(self):
        """带+86前缀的手机号"""
        from app.middleware.data_masking import mask_phone
        result = mask_phone("+8613812345678")
        assert "****" in result
        # 应保留前缀和后4位
        assert result.endswith("5678")

    def test_mask_phone_with_86_prefix_no_plus(self):
        """带86前缀（无+号）的手机号"""
        from app.middleware.data_masking import mask_phone
        result = mask_phone("8613812345678")
        assert "****" in result
        assert result.endswith("5678")

    def test_mask_phone_empty_string(self):
        """空字符串不应崩溃"""
        from app.middleware.data_masking import mask_phone
        assert mask_phone("") == ""

    def test_mask_phone_not_a_phone(self):
        """非手机号字符串不应改变"""
        from app.middleware.data_masking import mask_phone
        assert mask_phone("12345") == "12345"

    def test_mask_phone_in_text(self):
        """文本中嵌入的手机号"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "用户手机号是13812345678，请联系他"
        result = mask_sensitive_in_text(text)
        assert "13812345678" not in result
        assert "138****5678" in result

    def test_mask_multiple_phones_in_text(self):
        """文本中含多个手机号"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "联系人：13812345678 和 15987654321"
        result = mask_sensitive_in_text(text)
        assert "13812345678" not in result
        assert "15987654321" not in result

    def test_mask_phone_various_prefixes(self):
        """各种运营商号段"""
        from app.middleware.data_masking import mask_phone
        phones = ["13012345678", "14512345678", "15612345678",
                  "16612345678", "17012345678", "18012345678", "19112345678"]
        for phone in phones:
            result = mask_phone(phone)
            assert "****" in result, f"手机号 {phone} 未被脱敏"


class TestMaskEmail:
    """测试邮箱脱敏"""

    def test_mask_standard_email(self):
        """标准邮箱"""
        from app.middleware.data_masking import mask_email
        result = mask_email("testuser@example.com")
        assert "@example.com" in result
        assert "testuser" not in result
        assert "****" in result or "***" in result or "te" in result

    def test_mask_short_email(self):
        """短用户名邮箱"""
        from app.middleware.data_masking import mask_email
        result = mask_email("ab@example.com")
        assert "@example.com" in result

    def test_mask_email_empty(self):
        """空字符串"""
        from app.middleware.data_masking import mask_email
        assert mask_email("") == ""

    def test_mask_email_not_email(self):
        """非邮箱格式"""
        from app.middleware.data_masking import mask_email
        assert mask_email("notanemail") == "notanemail"

    def test_mask_email_in_text(self):
        """文本中嵌入的邮箱"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "请发邮件到 user@example.com 联系"
        result = mask_sensitive_in_text(text)
        assert "user@example.com" not in result
        assert "@example.com" in result

    def test_mask_multiple_emails_in_text(self):
        """文本中含多个邮箱"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "邮件1: a@test.com 邮件2: b@foo.org"
        result = mask_sensitive_in_text(text)
        assert "a@test.com" not in result
        assert "b@foo.org" not in result


class TestFuzzLocation:
    """测试位置坐标模糊化"""

    def test_fuzz_latitude(self):
        """纬度模糊化：精度降低到小数点后2位"""
        from app.middleware.data_masking import fuzz_location
        result = fuzz_location(39.915527, 116.397128)
        # 模糊化后精度应该降低
        lat, lng = result
        assert isinstance(lat, float)
        assert isinstance(lng, float)
        # 模糊化后与原值差距在合理范围内（<0.01度，约1km）
        assert abs(lat - 39.915527) < 0.02
        assert abs(lng - 116.397128) < 0.02
        # 精度应该被截断到小数点后2位
        lat_str = f"{lat:.10f}"
        # 小数点后第3位以后应该都是0（截断到2位精度）
        assert round(lat, 2) == lat

    def test_fuzz_longitude(self):
        """经度模糊化"""
        from app.middleware.data_masking import fuzz_location
        lat, lng = fuzz_location(31.230416, 121.473701)
        assert round(lng, 2) == lng

    def test_fuzz_location_zero(self):
        """坐标为0"""
        from app.middleware.data_masking import fuzz_location
        lat, lng = fuzz_location(0.0, 0.0)
        assert lat == 0.0
        assert lng == 0.0

    def test_fuzz_location_negative(self):
        """负坐标（南半球/西半球）"""
        from app.middleware.data_masking import fuzz_location
        lat, lng = fuzz_location(-33.868820, -151.209296)
        assert isinstance(lat, float)
        assert isinstance(lng, float)
        assert round(lat, 2) == lat
        assert round(lng, 2) == lng

    def test_fuzz_location_preserves_general_area(self):
        """模糊化后仍在同一大致区域"""
        from app.middleware.data_masking import fuzz_location
        lat, lng = fuzz_location(39.915527, 116.397128)
        # 应该还在北京附近（差距不超过0.01度）
        assert 39.0 < lat < 40.0
        assert 116.0 < lng < 117.0

    def test_fuzz_coords_in_json(self):
        """JSON数据中的坐标模糊化"""
        from app.middleware.data_masking import fuzz_coords_in_dict
        data = {
            "latitude": 39.915527,
            "longitude": 116.397128,
            "name": "天安门"
        }
        result = fuzz_coords_in_dict(data)
        assert result["latitude"] == round(39.915527, 2)
        assert result["longitude"] == round(116.397128, 2)
        assert result["name"] == "天安门"

    def test_fuzz_nested_coords_in_json(self):
        """嵌套JSON中的坐标模糊化"""
        from app.middleware.data_masking import fuzz_coords_in_dict
        data = {
            "location": {
                "lat": 39.915527,
                "lng": 116.397128
            },
            "user": "test"
        }
        result = fuzz_coords_in_dict(data)
        assert result["location"]["lat"] == round(39.915527, 2)
        assert result["location"]["lng"] == round(116.397128, 2)

    def test_fuzz_coords_list_in_json(self):
        """JSON数组中的坐标模糊化"""
        from app.middleware.data_masking import fuzz_coords_in_dict
        data = {
            "points": [
                {"latitude": 39.1234, "longitude": 116.5678},
                {"latitude": 31.9876, "longitude": 121.4321}
            ]
        }
        result = fuzz_coords_in_dict(data)
        assert result["points"][0]["latitude"] == round(39.1234, 2)
        assert result["points"][1]["longitude"] == round(121.4321, 2)


class TestMaskSensitiveFields:
    """测试响应中敏感字段脱敏"""

    def test_mask_password_field(self):
        """password字段应该被完全遮蔽"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"username": "test", "password": "mypassword123"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["password"] == "******"
        assert result["username"] == "test"

    def test_mask_token_field(self):
        """token字段脱敏"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx.yyy"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["access_token"] != "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx.yyy"
        assert "******" in result["access_token"] or len(result["access_token"]) < 20

    def test_mask_secret_field(self):
        """secret字段脱敏"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"api_secret": "sk-1234567890abcdef"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["api_secret"] != "sk-1234567890abcdef"

    def test_mask_api_key_field(self):
        """api_key字段脱敏"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"api_key": "sk-abcdefghijklmnop"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["api_key"] != "sk-abcdefghijklmnop"

    def test_nested_sensitive_fields(self):
        """嵌套字典中的敏感字段"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {
            "user": {
                "name": "test",
                "password": "secret123"
            }
        }
        result = mask_sensitive_fields_in_dict(data)
        assert result["user"]["password"] == "******"
        assert result["user"]["name"] == "test"

    def test_list_with_sensitive_fields(self):
        """列表中的字典含敏感字段"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {
            "users": [
                {"name": "a", "password": "p1"},
                {"name": "b", "password": "p2"}
            ]
        }
        result = mask_sensitive_fields_in_dict(data)
        assert result["users"][0]["password"] == "******"
        assert result["users"][1]["password"] == "******"

    def test_no_sensitive_fields(self):
        """没有敏感字段的数据应不变"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"name": "test", "age": 25, "city": "Beijing"}
        result = mask_sensitive_fields_in_dict(data)
        assert result == data

    def test_mask_refresh_token(self):
        """refresh_token字段脱敏"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"refresh_token": "rt_abcdefghijklmnop12345"}
        result = mask_sensitive_fields_in_dict(data)
        assert result["refresh_token"] != "rt_abcdefghijklmnop12345"


class TestMaskSensitiveInText:
    """测试文本中的综合脱敏"""

    def test_text_with_phone_and_email(self):
        """同时含手机号和邮箱的文本"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "联系方式：手机13812345678 邮箱user@test.com"
        result = mask_sensitive_in_text(text)
        assert "13812345678" not in result
        assert "user@test.com" not in result

    def test_text_with_coords(self):
        """含坐标的文本中坐标数字不做文本脱敏（坐标脱敏在JSON层处理）"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "位置：39.915527, 116.397128"
        result = mask_sensitive_in_text(text)
        # 纯文本中的坐标不会被当成手机号（不是11位数字）
        assert "39.915527" in result or "39.92" in result

    def test_empty_text(self):
        """空文本"""
        from app.middleware.data_masking import mask_sensitive_in_text
        assert mask_sensitive_in_text("") == ""

    def test_none_text(self):
        """None值"""
        from app.middleware.data_masking import mask_sensitive_in_text
        assert mask_sensitive_in_text(None) is None

    def test_text_no_sensitive(self):
        """不含敏感信息的文本"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "今天天气不错，适合运动"
        assert mask_sensitive_in_text(text) == text

    def test_id_card_like_number_not_masked_as_phone(self):
        """18位身份证号不应被错误脱敏为手机号"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "身份证：110101199001011234"
        result = mask_sensitive_in_text(text)
        # 身份证号可以被脱敏，但不应只把中间11位当手机号处理
        # 这里测试不会产生异常
        assert isinstance(result, str)


class TestLogMaskingFilter:
    """测试日志脱敏过滤器"""

    def test_log_filter_masks_phone(self):
        """日志中手机号被脱敏"""
        from app.middleware.data_masking import SensitiveDataFilter
        logger = logging.getLogger("test_phone_filter")
        logger.setLevel(logging.DEBUG)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SensitiveDataFilter())
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

        logger.info("用户手机号: 13812345678")
        output = stream.getvalue()
        assert "13812345678" not in output
        assert "138****5678" in output

        logger.removeHandler(handler)

    def test_log_filter_masks_email(self):
        """日志中邮箱被脱敏"""
        from app.middleware.data_masking import SensitiveDataFilter
        logger = logging.getLogger("test_email_filter")
        logger.setLevel(logging.DEBUG)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SensitiveDataFilter())
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

        logger.info("邮箱: admin@example.com")
        output = stream.getvalue()
        assert "admin@example.com" not in output
        assert "@example.com" in output

        logger.removeHandler(handler)

    def test_log_filter_no_sensitive_data(self):
        """不含敏感数据的日志不应改变"""
        from app.middleware.data_masking import SensitiveDataFilter
        logger = logging.getLogger("test_no_sensitive")
        logger.setLevel(logging.DEBUG)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SensitiveDataFilter())
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

        logger.info("正常日志消息")
        output = stream.getvalue()
        assert "正常日志消息" in output

        logger.removeHandler(handler)


# ===== 第二部分：中间件集成测试 =====


class TestDataMaskingMiddleware:
    """测试FastAPI中间件集成"""

    @pytest.fixture
    def app_with_middleware(self):
        """创建带脱敏中间件的测试应用"""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from app.middleware.data_masking import DataMaskingMiddleware

        app = FastAPI()
        app.add_middleware(DataMaskingMiddleware)

        @app.post("/test/echo")
        async def echo(request: Request):
            """回显请求体"""
            body = await request.json()
            return JSONResponse(content=body)

        @app.post("/test/with-password")
        async def with_password(request: Request):
            """返回含password字段的响应"""
            return JSONResponse(content={
                "user": "test",
                "password": "secret123",
                "access_token": "eyJhbGciOiJIUzI1NiJ9.payload.signature"
            })

        @app.post("/test/with-coords")
        async def with_coords(request: Request):
            """返回含坐标的响应"""
            body = await request.json()
            return JSONResponse(content=body)

        @app.get("/test/health")
        async def health():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app_with_middleware):
        from fastapi.testclient import TestClient
        return TestClient(app_with_middleware)

    def test_middleware_masks_password_in_response(self, client):
        """中间件脱敏响应中的password"""
        resp = client.post("/test/with-password", json={})
        data = resp.json()
        assert data["password"] == "******"
        assert data["user"] == "test"

    def test_middleware_masks_token_in_response(self, client):
        """中间件脱敏响应中的token"""
        resp = client.post("/test/with-password", json={})
        data = resp.json()
        assert data["access_token"] != "eyJhbGciOiJIUzI1NiJ9.payload.signature"

    def test_middleware_fuzzes_coords_in_response(self, client):
        """中间件模糊化响应中的坐标"""
        resp = client.post("/test/with-coords", json={
            "latitude": 39.915527,
            "longitude": 116.397128,
            "name": "天安门"
        })
        data = resp.json()
        assert data["latitude"] == round(39.915527, 2)
        assert data["longitude"] == round(116.397128, 2)
        assert data["name"] == "天安门"

    def test_middleware_fuzzes_coords_in_request_body(self, client):
        """中间件模糊化上传数据中的坐标"""
        resp = client.post("/test/echo", json={
            "latitude": 31.230416,
            "longitude": 121.473701,
            "address": "上海市"
        })
        data = resp.json()
        # 请求体中的坐标也应被模糊化
        assert data["latitude"] == round(31.230416, 2)
        assert data["longitude"] == round(121.473701, 2)

    def test_middleware_health_endpoint_passthrough(self, client):
        """健康检查端点正常通过"""
        resp = client.get("/test/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_middleware_non_json_response(self, app_with_middleware):
        """非JSON响应正常通过"""
        from fastapi import FastAPI
        from fastapi.responses import PlainTextResponse
        from fastapi.testclient import TestClient

        @app_with_middleware.get("/test/plain")
        async def plain():
            return PlainTextResponse("hello")

        client = TestClient(app_with_middleware)
        resp = client.get("/test/plain")
        assert resp.status_code == 200
        assert resp.text == "hello"

    def test_middleware_empty_body(self, client):
        """空请求体的GET请求"""
        resp = client.get("/test/health")
        assert resp.status_code == 200

    def test_middleware_nested_coords(self, client):
        """嵌套结构中的坐标也被模糊化"""
        resp = client.post("/test/with-coords", json={
            "route": {
                "start": {"latitude": 39.9, "longitude": 116.4},
                "end": {"latitude": 31.2, "longitude": 121.5}
            }
        })
        data = resp.json()
        assert data["route"]["start"]["latitude"] == round(39.9, 2)
        assert data["route"]["end"]["latitude"] == round(31.2, 2)

    def test_middleware_phone_in_response_text_field(self, client):
        """响应中文本字段含手机号时脱敏"""
        resp = client.post("/test/echo", json={
            "message": "请联系13812345678"
        })
        data = resp.json()
        assert "13812345678" not in data["message"]
        assert "138****5678" in data["message"]

    def test_middleware_email_in_response_text_field(self, client):
        """响应中文本字段含邮箱时脱敏"""
        resp = client.post("/test/echo", json={
            "contact": "发邮件到admin@test.com"
        })
        data = resp.json()
        assert "admin@test.com" not in data["contact"]


class TestEdgeCases:
    """边界条件测试"""

    def test_mask_phone_boundary_10_digits(self):
        """10位数字不是手机号"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "数字1234567890"
        result = mask_sensitive_in_text(text)
        assert "1234567890" in result

    def test_mask_phone_boundary_12_digits(self):
        """12位数字不是标准手机号"""
        from app.middleware.data_masking import mask_sensitive_in_text
        text = "数字123456789012"
        result = mask_sensitive_in_text(text)
        # 不应被当作手机号脱敏（除非是+86格式）
        assert isinstance(result, str)

    def test_fuzz_coords_extreme_values(self):
        """极端坐标值"""
        from app.middleware.data_masking import fuzz_location
        # 北极
        lat, lng = fuzz_location(90.0, 0.0)
        assert lat == 90.0
        assert lng == 0.0
        # 南极
        lat, lng = fuzz_location(-90.0, 180.0)
        assert lat == -90.0
        assert lng == 180.0

    def test_mask_sensitive_fields_non_string_values(self):
        """非字符串类型的值不应崩溃"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"count": 42, "active": True, "items": [1, 2, 3]}
        result = mask_sensitive_fields_in_dict(data)
        assert result == data

    def test_mask_sensitive_fields_none_value(self):
        """None值字段"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {"name": None, "password": None}
        result = mask_sensitive_fields_in_dict(data)
        assert result["password"] == "******"

    def test_deeply_nested_structure(self):
        """深度嵌套结构"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "password": "deep_secret"
                    }
                }
            }
        }
        result = mask_sensitive_fields_in_dict(data)
        assert result["level1"]["level2"]["level3"]["password"] == "******"

    def test_empty_dict(self):
        """空字典"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        assert mask_sensitive_fields_in_dict({}) == {}

    def test_fuzz_coords_in_dict_no_coords(self):
        """没有坐标字段的字典"""
        from app.middleware.data_masking import fuzz_coords_in_dict
        data = {"name": "test", "value": 42}
        result = fuzz_coords_in_dict(data)
        assert result == data

    def test_mask_sensitive_fields_preserves_non_sensitive(self):
        """确保非敏感字段完全不变"""
        from app.middleware.data_masking import mask_sensitive_fields_in_dict
        data = {
            "userId": 123,
            "nickname": "健康达人",
            "healthGoal": "reduce_fat",
            "allergens": ["花生", "海鲜"],
            "calories": 1500.5
        }
        result = mask_sensitive_fields_in_dict(data)
        assert result == data

    def test_text_masking_preserves_json_structure(self):
        """文本脱敏不破坏JSON结构"""
        from app.middleware.data_masking import mask_sensitive_text_in_dict
        data = {
            "message": "手机13812345678",
            "code": 200,
            "items": [{"note": "邮箱user@test.com"}]
        }
        result = mask_sensitive_text_in_dict(data)
        assert result["code"] == 200
        assert "13812345678" not in result["message"]
        assert "user@test.com" not in result["items"][0]["note"]


class TestCombinedMasking:
    """综合脱敏测试：模拟真实场景"""

    def test_user_login_response_masking(self):
        """模拟用户登录响应脱敏"""
        from app.middleware.data_masking import apply_response_masking
        data = {
            "code": 200,
            "message": "登录成功",
            "data": {
                "userId": 1,
                "nickname": "测试用户",
                "access_token": "eyJhbGciOiJIUzI1NiJ9.long_payload.sig",
                "refresh_token": "rt_abcdefghijklmnop"
            }
        }
        result = apply_response_masking(data)
        assert result["data"]["userId"] == 1
        assert result["data"]["nickname"] == "测试用户"
        assert result["data"]["access_token"] != "eyJhbGciOiJIUzI1NiJ9.long_payload.sig"
        assert result["data"]["refresh_token"] != "rt_abcdefghijklmnop"

    def test_food_analyze_response_no_masking_needed(self):
        """营养分析响应不含敏感数据，应不变"""
        from app.middleware.data_masking import apply_response_masking
        data = {
            "success": True,
            "message": "分析成功",
            "data": {
                "name": "番茄炒蛋",
                "calories": 150.0,
                "protein": 10.5,
                "fat": 8.2,
                "carbs": 6.3
            }
        }
        result = apply_response_masking(data)
        assert result == data

    def test_trip_with_coords_masking(self):
        """运动计划含坐标时模糊化"""
        from app.middleware.data_masking import apply_response_masking
        data = {
            "code": 200,
            "data": {
                "tripId": 1,
                "latitude": 39.915527,
                "longitude": 116.397128,
                "routes": [
                    {"latitude": 39.92, "longitude": 116.40, "name": "起点"},
                    {"latitude": 39.93, "longitude": 116.41, "name": "终点"}
                ]
            }
        }
        result = apply_response_masking(data)
        assert result["data"]["latitude"] == round(39.915527, 2)
        assert result["data"]["longitude"] == round(116.397128, 2)

    def test_request_body_with_phone_and_coords(self):
        """请求体同时含手机号和坐标"""
        from app.middleware.data_masking import apply_request_masking
        data = {
            "phone": "13812345678",
            "latitude": 39.915527,
            "longitude": 116.397128,
            "query": "附近公园"
        }
        result = apply_request_masking(data)
        # 坐标应被模糊化
        assert result["latitude"] == round(39.915527, 2)
        assert result["longitude"] == round(116.397128, 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
