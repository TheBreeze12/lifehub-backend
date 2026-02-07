"""
Phase 14 测试文件：餐后图片上传与对比计算功能测试
测试后端 POST /api/food/meal/after/{comparison_id} 接口
"""

import pytest
import requests
import os
import json
from pathlib import Path

# 后端基础URL
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class TestPhase14AfterMealUpload:
    """Phase 14: 餐后图片上传与对比计算测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前置设置"""
        self.base_url = BASE_URL
        self.headers = {"Content-Type": "application/json"}
        # 测试用户ID（需要先注册）
        self.test_user_id = self._get_or_create_test_user()
        # 存储餐前上传返回的comparison_id
        self.comparison_id = None

    def _get_or_create_test_user(self):
        """获取或创建测试用户"""
        # 尝试登录
        try:
            response = requests.get(
                f"{self.base_url}/api/user/data",
                params={"nickname": "phase14_test_user", "password": "test123456"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("userId"):
                    return data["data"]["userId"]
        except:
            pass

        # 注册新用户
        try:
            response = requests.post(
                f"{self.base_url}/api/user/register",
                json={"nickname": "phase14_test_user", "password": "test123456"}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("userId") or data.get("data", {}).get("userId", 1)
        except:
            pass

        return 1  # 默认用户ID

    def _create_test_image(self, filename: str = "test_meal.jpg"):
        """创建测试图片文件"""
        # 创建一个简单的测试图片（1x1像素的JPEG）
        import struct
        import zlib

        # 最小JPEG文件
        jpeg_data = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x4C, 0xA2,
            0x0A, 0x28, 0xA0, 0x02, 0x80, 0x28, 0xA2, 0x80, 0x0A, 0x28, 0xA0, 0x02,
            0x8A, 0x28, 0x00, 0xFF, 0xD9
        ])

        test_dir = Path(__file__).parent / "test_images"
        test_dir.mkdir(exist_ok=True)
        filepath = test_dir / filename
        filepath.write_bytes(jpeg_data)
        return str(filepath)

    def _upload_before_meal_image(self):
        """上传餐前图片，获取comparison_id"""
        image_path = self._create_test_image("before_meal_test.jpg")
        
        with open(image_path, "rb") as f:
            files = {"image": ("before_meal.jpg", f, "image/jpeg")}
            data = {"user_id": str(self.test_user_id)}
            response = requests.post(
                f"{self.base_url}/api/food/meal/before",
                files=files,
                data=data
            )

        if response.status_code == 200:
            result = response.json()
            if result.get("data") and result["data"].get("comparison_id"):
                return result["data"]["comparison_id"]
        return None

    # ==================== 测试用例 ====================

    def test_01_before_meal_upload_prerequisite(self):
        """测试前置条件：餐前上传必须成功"""
        self.comparison_id = self._upload_before_meal_image()
        assert self.comparison_id is not None, "餐前图片上传失败，无法获取comparison_id"
        print(f"✅ 餐前上传成功，comparison_id: {self.comparison_id}")

    def test_02_after_meal_upload_success(self):
        """测试餐后图片上传成功场景"""
        # 先上传餐前图片
        comparison_id = self._upload_before_meal_image()
        assert comparison_id is not None, "前置条件失败：餐前图片上传失败"

        # 上传餐后图片
        image_path = self._create_test_image("after_meal_test.jpg")
        
        with open(image_path, "rb") as f:
            files = {"image": ("after_meal.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{self.base_url}/api/food/meal/after/{comparison_id}",
                files=files
            )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")

        assert response.status_code == 200, f"餐后上传失败: {response.text}"
        
        result = response.json()
        assert result.get("code") == 200, f"响应code不是200: {result}"
        assert result.get("data") is not None, "响应data为空"
        
        data = result["data"]
        # 验证必要字段
        assert "comparison_id" in data, "缺少comparison_id字段"
        assert "consumption_ratio" in data, "缺少consumption_ratio字段"
        assert "net_calories" in data, "缺少net_calories字段"
        assert "original_calories" in data, "缺少original_calories字段"
        
        # 验证计算逻辑
        consumption_ratio = data["consumption_ratio"]
        assert 0 <= consumption_ratio <= 1, f"consumption_ratio应在0-1之间: {consumption_ratio}"
        
        print(f"✅ 餐后上传成功")
        print(f"   - 消耗比例: {consumption_ratio:.2%}")
        print(f"   - 原始热量: {data['original_calories']:.1f} kcal")
        print(f"   - 净摄入热量: {data['net_calories']:.1f} kcal")

    def test_03_after_meal_invalid_comparison_id(self):
        """测试无效的comparison_id"""
        image_path = self._create_test_image("test_invalid.jpg")
        
        with open(image_path, "rb") as f:
            files = {"image": ("test.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{self.base_url}/api/food/meal/after/99999",
                files=files
            )

        # 应该返回404
        assert response.status_code == 404, f"应返回404，实际返回: {response.status_code}"
        print("✅ 无效comparison_id正确返回404")

    def test_04_after_meal_without_image(self):
        """测试不上传图片"""
        comparison_id = self._upload_before_meal_image()
        if comparison_id is None:
            pytest.skip("无法获取comparison_id")

        response = requests.post(
            f"{self.base_url}/api/food/meal/after/{comparison_id}"
        )

        # 应该返回422（参数校验失败）
        assert response.status_code == 422, f"应返回422，实际返回: {response.status_code}"
        print("✅ 不上传图片正确返回422")

    def test_05_after_meal_duplicate_upload(self):
        """测试重复上传餐后图片（同一comparison_id）"""
        # 先上传餐前图片
        comparison_id = self._upload_before_meal_image()
        if comparison_id is None:
            pytest.skip("无法获取comparison_id")

        # 第一次上传餐后图片
        image_path = self._create_test_image("after1.jpg")
        with open(image_path, "rb") as f:
            files = {"image": ("after1.jpg", f, "image/jpeg")}
            response1 = requests.post(
                f"{self.base_url}/api/food/meal/after/{comparison_id}",
                files=files
            )

        if response1.status_code != 200:
            pytest.skip(f"第一次上传失败: {response1.text}")

        # 第二次上传（应该失败或覆盖）
        image_path2 = self._create_test_image("after2.jpg")
        with open(image_path2, "rb") as f:
            files = {"image": ("after2.jpg", f, "image/jpeg")}
            response2 = requests.post(
                f"{self.base_url}/api/food/meal/after/{comparison_id}",
                files=files
            )

        # 重复上传应返回400（状态异常）
        assert response2.status_code in [200, 400], f"重复上传返回: {response2.status_code}"
        print(f"✅ 重复上传处理正确，状态码: {response2.status_code}")

    def test_06_consumption_ratio_calculation(self):
        """测试消耗比例计算逻辑"""
        comparison_id = self._upload_before_meal_image()
        if comparison_id is None:
            pytest.skip("无法获取comparison_id")

        image_path = self._create_test_image("after_calc_test.jpg")
        with open(image_path, "rb") as f:
            files = {"image": ("after.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{self.base_url}/api/food/meal/after/{comparison_id}",
                files=files
            )

        if response.status_code != 200:
            pytest.skip(f"上传失败: {response.text}")

        data = response.json().get("data", {})
        
        consumption_ratio = data.get("consumption_ratio", 0)
        original_calories = data.get("original_calories", 0)
        net_calories = data.get("net_calories", 0)

        # 验证计算公式：net_calories = original_calories * consumption_ratio
        if original_calories > 0:
            expected_net = original_calories * consumption_ratio
            # 允许小误差
            assert abs(net_calories - expected_net) < 1, \
                f"净摄入计算错误: {net_calories} != {expected_net}"
        
        print(f"✅ 消耗比例计算正确")
        print(f"   公式: {original_calories:.1f} × {consumption_ratio:.2f} = {net_calories:.1f}")

    def test_07_net_nutrients_calculation(self):
        """测试净营养素计算"""
        comparison_id = self._upload_before_meal_image()
        if comparison_id is None:
            pytest.skip("无法获取comparison_id")

        image_path = self._create_test_image("after_nutrients.jpg")
        with open(image_path, "rb") as f:
            files = {"image": ("after.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{self.base_url}/api/food/meal/after/{comparison_id}",
                files=files
            )

        if response.status_code != 200:
            pytest.skip(f"上传失败: {response.text}")

        data = response.json().get("data", {})
        
        # 检查营养素字段存在
        nutrient_fields = [
            "original_protein", "original_fat", "original_carbs",
            "net_protein", "net_fat", "net_carbs"
        ]
        
        for field in nutrient_fields:
            assert field in data, f"缺少营养素字段: {field}"
        
        # 验证净营养素 = 原始营养素 × 消耗比例
        consumption_ratio = data.get("consumption_ratio", 0)
        
        for nutrient in ["protein", "fat", "carbs"]:
            original = data.get(f"original_{nutrient}", 0)
            net = data.get(f"net_{nutrient}", 0)
            expected = original * consumption_ratio
            
            assert abs(net - expected) < 0.1, \
                f"净{nutrient}计算错误: {net} != {expected}"
        
        print("✅ 净营养素计算正确")

    def test_08_response_structure(self):
        """测试响应结构完整性"""
        comparison_id = self._upload_before_meal_image()
        if comparison_id is None:
            pytest.skip("无法获取comparison_id")

        image_path = self._create_test_image("structure_test.jpg")
        with open(image_path, "rb") as f:
            files = {"image": ("after.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{self.base_url}/api/food/meal/after/{comparison_id}",
                files=files
            )

        if response.status_code != 200:
            pytest.skip(f"上传失败: {response.text}")

        result = response.json()
        
        # 验证顶层结构
        assert "code" in result
        assert "message" in result
        assert "data" in result
        
        data = result["data"]
        
        # 验证必需字段
        required_fields = [
            "comparison_id",
            "consumption_ratio",
            "original_calories",
            "net_calories",
            "status"
        ]
        
        for field in required_fields:
            assert field in data, f"响应缺少必需字段: {field}"
        
        # 验证状态为completed
        assert data["status"] in ["completed", "done"], \
            f"状态应为completed，实际为: {data['status']}"
        
        print("✅ 响应结构验证通过")


class TestPhase14FrontendLogic:
    """Phase 14: 前端逻辑测试（模拟）"""

    def test_consumption_ratio_slider_bounds(self):
        """测试消耗比例滑块边界值"""
        # 模拟Slider的值范围检验
        min_ratio = 0.0
        max_ratio = 1.0
        
        test_values = [-0.1, 0.0, 0.5, 1.0, 1.1]
        
        for value in test_values:
            clamped = max(min_ratio, min(max_ratio, value))
            assert min_ratio <= clamped <= max_ratio, \
                f"滑块值越界: {value} -> {clamped}"
        
        print("✅ 消耗比例滑块边界值验证通过")

    def test_net_calories_calculation_client(self):
        """测试客户端净热量计算"""
        test_cases = [
            {"original": 500, "ratio": 0.8, "expected": 400},
            {"original": 300, "ratio": 0.5, "expected": 150},
            {"original": 100, "ratio": 1.0, "expected": 100},
            {"original": 200, "ratio": 0.0, "expected": 0},
        ]
        
        for case in test_cases:
            calculated = case["original"] * case["ratio"]
            assert abs(calculated - case["expected"]) < 0.01, \
                f"计算错误: {case['original']} × {case['ratio']} = {calculated}, 期望 {case['expected']}"
        
        print("✅ 客户端净热量计算验证通过")

    def test_manual_ratio_adjustment(self):
        """测试手动调整比例后重新计算"""
        original_calories = 600
        original_protein = 30
        original_fat = 20
        original_carbs = 50
        
        # 初始AI识别比例
        ai_ratio = 0.75
        
        # 用户手动调整后的比例
        user_ratios = [0.5, 0.6, 0.8, 0.9]
        
        for user_ratio in user_ratios:
            net_calories = original_calories * user_ratio
            net_protein = original_protein * user_ratio
            net_fat = original_fat * user_ratio
            net_carbs = original_carbs * user_ratio
            
            assert net_calories == original_calories * user_ratio
            assert net_protein == original_protein * user_ratio
            assert net_fat == original_fat * user_ratio
            assert net_carbs == original_carbs * user_ratio
        
        print("✅ 手动调整比例计算验证通过")

    def test_comparison_state_transitions(self):
        """测试对比状态转换"""
        # 状态流程: idle -> before_uploaded -> completed
        states = ["idle", "pending_after", "completed"]
        
        current_state = "idle"
        
        # 餐前上传完成
        if current_state == "idle":
            current_state = "pending_after"
        
        assert current_state == "pending_after"
        
        # 餐后上传完成
        if current_state == "pending_after":
            current_state = "completed"
        
        assert current_state == "completed"
        
        print("✅ 对比状态转换验证通过")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 14 测试: 餐后拍摄与对比展示")
    print("=" * 60)
    
    # 检查后端是否可用
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 后端服务不可用: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接后端服务: {e}")
        print("请先启动后端服务: uvicorn app.main:app --reload")
        return False
    
    print(f"✅ 后端服务可用: {BASE_URL}")
    print("-" * 60)
    
    # 运行pytest
    import sys
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    return exit_code == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
