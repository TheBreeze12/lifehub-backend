"""
Phase 5 测试: 身体参数设置API集成测试
验证后端API支持前端身体参数设置功能

测试内容:
1. 获取用户偏好时包含身体参数
2. 更新身体参数（体重、身高、年龄、性别）
3. 部分更新身体参数
4. 身体参数边界值验证
5. 身体参数与其他偏好混合更新
"""

import pytest
import requests
import json
from typing import Optional

# 后端服务基础URL
BASE_URL = "http://localhost:8000"

# 测试用户ID（需要确保数据库中存在该用户）
TEST_USER_ID = 1


class TestBodyParamsAPI:
    """身体参数API测试类"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.base_url = BASE_URL
        self.headers = {"Content-Type": "application/json"}

    # ==================== 获取偏好测试 ====================

    def test_get_preferences_includes_body_params(self):
        """测试获取用户偏好时返回身体参数字段"""
        response = requests.get(
            f"{self.base_url}/api/user/preferences",
            params={"userId": TEST_USER_ID}
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert "data" in data, "响应中缺少data字段"
        
        user_data = data["data"]
        # 验证身体参数字段存在（可能为null）
        assert "weight" in user_data, "响应中缺少weight字段"
        assert "height" in user_data, "响应中缺少height字段"
        assert "age" in user_data, "响应中缺少age字段"
        assert "gender" in user_data, "响应中缺少gender字段"
        
        print(f"✅ 获取用户偏好成功，身体参数: weight={user_data.get('weight')}, "
              f"height={user_data.get('height')}, age={user_data.get('age')}, "
              f"gender={user_data.get('gender')}")

    # ==================== 更新身体参数测试 ====================

    def test_update_body_params_all(self):
        """测试更新所有身体参数"""
        update_data = {
            "userId": TEST_USER_ID,
            "weight": 70.5,
            "height": 175.0,
            "age": 25,
            "gender": "male"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        
        user_data = data["data"]
        assert user_data["weight"] == 70.5, f"体重更新失败: {user_data.get('weight')}"
        assert user_data["height"] == 175.0, f"身高更新失败: {user_data.get('height')}"
        assert user_data["age"] == 25, f"年龄更新失败: {user_data.get('age')}"
        assert user_data["gender"] == "male", f"性别更新失败: {user_data.get('gender')}"
        
        print(f"✅ 更新所有身体参数成功")

    def test_update_weight_only(self):
        """测试只更新体重"""
        update_data = {
            "userId": TEST_USER_ID,
            "weight": 68.0
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert data["data"]["weight"] == 68.0, "体重更新失败"
        
        print(f"✅ 只更新体重成功: {data['data']['weight']}kg")

    def test_update_height_only(self):
        """测试只更新身高"""
        update_data = {
            "userId": TEST_USER_ID,
            "height": 172.5
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert data["data"]["height"] == 172.5, "身高更新失败"
        
        print(f"✅ 只更新身高成功: {data['data']['height']}cm")

    def test_update_age_only(self):
        """测试只更新年龄"""
        update_data = {
            "userId": TEST_USER_ID,
            "age": 28
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert data["data"]["age"] == 28, "年龄更新失败"
        
        print(f"✅ 只更新年龄成功: {data['data']['age']}岁")

    def test_update_gender_male(self):
        """测试更新性别为男"""
        update_data = {
            "userId": TEST_USER_ID,
            "gender": "male"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert data["data"]["gender"] == "male", "性别更新失败"
        
        print(f"✅ 更新性别为男成功")

    def test_update_gender_female(self):
        """测试更新性别为女"""
        update_data = {
            "userId": TEST_USER_ID,
            "gender": "female"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert data["data"]["gender"] == "female", "性别更新失败"
        
        print(f"✅ 更新性别为女成功")

    def test_update_gender_other(self):
        """测试更新性别为其他"""
        update_data = {
            "userId": TEST_USER_ID,
            "gender": "other"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        assert data["data"]["gender"] == "other", "性别更新失败"
        
        print(f"✅ 更新性别为其他成功")

    # ==================== 混合更新测试 ====================

    def test_update_body_params_with_health_goal(self):
        """测试同时更新身体参数和健康目标"""
        update_data = {
            "userId": TEST_USER_ID,
            "healthGoal": "reduce_fat",
            "weight": 72.0,
            "height": 176.0,
            "age": 26,
            "gender": "male"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        
        user_data = data["data"]
        assert user_data["healthGoal"] == "reduce_fat", "健康目标更新失败"
        assert user_data["weight"] == 72.0, "体重更新失败"
        assert user_data["height"] == 176.0, "身高更新失败"
        assert user_data["age"] == 26, "年龄更新失败"
        assert user_data["gender"] == "male", "性别更新失败"
        
        print(f"✅ 同时更新身体参数和健康目标成功")

    def test_update_body_params_with_allergens(self):
        """测试同时更新身体参数和过敏原"""
        update_data = {
            "userId": TEST_USER_ID,
            "allergens": ["花生", "海鲜"],
            "weight": 65.0,
            "gender": "female"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        
        user_data = data["data"]
        assert "花生" in user_data["allergens"], "过敏原更新失败"
        assert user_data["weight"] == 65.0, "体重更新失败"
        assert user_data["gender"] == "female", "性别更新失败"
        
        print(f"✅ 同时更新身体参数和过敏原成功")

    # ==================== 边界值测试 ====================

    def test_weight_boundary_min(self):
        """测试体重最小边界值"""
        update_data = {
            "userId": TEST_USER_ID,
            "weight": 0.1
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        
        print(f"✅ 体重最小边界值测试通过")

    def test_weight_boundary_max(self):
        """测试体重最大边界值"""
        update_data = {
            "userId": TEST_USER_ID,
            "weight": 500.0
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        
        print(f"✅ 体重最大边界值测试通过")

    def test_height_boundary_max(self):
        """测试身高最大边界值"""
        update_data = {
            "userId": TEST_USER_ID,
            "height": 300.0
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"请求失败: {response.text}"
        
        data = response.json()
        assert data["code"] == 200, f"API返回错误: {data}"
        
        print(f"✅ 身高最大边界值测试通过")

    def test_age_boundary_values(self):
        """测试年龄边界值"""
        # 最小年龄
        update_data = {"userId": TEST_USER_ID, "age": 1}
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        assert response.status_code == 200, f"最小年龄测试失败: {response.text}"
        
        # 最大年龄
        update_data = {"userId": TEST_USER_ID, "age": 150}
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        assert response.status_code == 200, f"最大年龄测试失败: {response.text}"
        
        print(f"✅ 年龄边界值测试通过")

    # ==================== 数据持久化测试 ====================

    def test_body_params_persistence(self):
        """测试身体参数数据持久化"""
        # 1. 设置身体参数
        update_data = {
            "userId": TEST_USER_ID,
            "weight": 73.5,
            "height": 178.0,
            "age": 30,
            "gender": "male"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        assert response.status_code == 200, f"更新失败: {response.text}"
        
        # 2. 重新获取验证持久化
        response = requests.get(
            f"{self.base_url}/api/user/preferences",
            params={"userId": TEST_USER_ID}
        )
        assert response.status_code == 200, f"获取失败: {response.text}"
        
        data = response.json()
        user_data = data["data"]
        
        assert user_data["weight"] == 73.5, f"体重持久化失败: {user_data.get('weight')}"
        assert user_data["height"] == 178.0, f"身高持久化失败: {user_data.get('height')}"
        assert user_data["age"] == 30, f"年龄持久化失败: {user_data.get('age')}"
        assert user_data["gender"] == "male", f"性别持久化失败: {user_data.get('gender')}"
        
        print(f"✅ 身体参数数据持久化测试通过")

    # ==================== 恢复测试数据 ====================

    def test_zz_restore_test_data(self):
        """测试完成后恢复测试数据（确保最后执行）"""
        update_data = {
            "userId": TEST_USER_ID,
            "healthGoal": "balanced",
            "allergens": [],
            "travelPreference": "walking",
            "dailyBudget": 500,
            "weight": 70.0,
            "height": 175.0,
            "age": 25,
            "gender": "male"
        }
        
        response = requests.put(
            f"{self.base_url}/api/user/preferences",
            headers=self.headers,
            json=update_data
        )
        
        if response.status_code == 200:
            print(f"✅ 测试数据已恢复")
        else:
            print(f"⚠️ 测试数据恢复失败: {response.text}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 5 身体参数API集成测试")
    print("=" * 60)
    
    test_instance = TestBodyParamsAPI()
    test_instance.setup_method()
    
    # 运行测试
    test_methods = [
        ("获取偏好包含身体参数", test_instance.test_get_preferences_includes_body_params),
        ("更新所有身体参数", test_instance.test_update_body_params_all),
        ("只更新体重", test_instance.test_update_weight_only),
        ("只更新身高", test_instance.test_update_height_only),
        ("只更新年龄", test_instance.test_update_age_only),
        ("更新性别为男", test_instance.test_update_gender_male),
        ("更新性别为女", test_instance.test_update_gender_female),
        ("更新性别为其他", test_instance.test_update_gender_other),
        ("混合更新健康目标", test_instance.test_update_body_params_with_health_goal),
        ("混合更新过敏原", test_instance.test_update_body_params_with_allergens),
        ("体重最小边界值", test_instance.test_weight_boundary_min),
        ("体重最大边界值", test_instance.test_weight_boundary_max),
        ("身高最大边界值", test_instance.test_height_boundary_max),
        ("年龄边界值", test_instance.test_age_boundary_values),
        ("数据持久化", test_instance.test_body_params_persistence),
        ("恢复测试数据", test_instance.test_zz_restore_test_data),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in test_methods:
        try:
            print(f"\n🔄 运行测试: {name}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ 测试失败: {name} - {str(e)}")
            failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {name} - {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed}/{passed + failed}, 失败 {failed}")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
