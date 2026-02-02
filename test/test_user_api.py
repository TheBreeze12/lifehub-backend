"""
测试用户偏好API
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_get_user_preferences(user_id: int):
    """测试获取用户偏好"""
    print(f"\n{'='*50}")
    print(f"测试：获取用户偏好 (userId={user_id})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/user/preferences"
    params = {"userId": user_id}
    
    try:
        response = requests.get(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("✅ 获取用户偏好成功")
                return True
            else:
                print(f"❌ 获取失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_update_user_preferences(user_id: int):
    """测试更新用户偏好"""
    print(f"\n{'='*50}")
    print(f"测试：更新用户偏好 (userId={user_id})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/user/preferences"
    
    # 测试数据
    payload = {
        "userId": user_id,
        "healthGoal": "reduce_fat",
        "allergens": ["海鲜", "花生"],
        "travelPreference": "self_driving",
        "dailyBudget": 500
    }
    
    try:
        response = requests.put(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("✅ 更新用户偏好成功")
                return True
            else:
                print(f"❌ 更新失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_partial_update(user_id: int):
    """测试部分更新（只更新部分字段）"""
    print(f"\n{'='*50}")
    print(f"测试：部分更新用户偏好 (userId={user_id})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/user/preferences"
    
    # 只更新健康目标和预算
    payload = {
        "userId": user_id,
        "healthGoal": "control_sugar",
        "dailyBudget": 800
    }
    
    try:
        response = requests.put(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("✅ 部分更新成功")
                # 验证其他字段未被修改
                user_data = data.get("data", {})
                if user_data.get("allergens") == ["海鲜", "花生"]:
                    print("✅ 其他字段保持不变")
                return True
            else:
                print(f"❌ 更新失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False

def test_register_user():
    """测试注册新用户"""
    nickname = str(input("请输入昵称: "))
    password = str(input("请输入密码: "))
    print(f"\n{'='*50}")
    print(f"测试：注册新用户 (nickname={nickname})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/user/register"
    
    payload = {
        "nickname": nickname,
        "password": password
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("✅ 注册用户成功")
                return True
            else:
                print(f"❌ 注册失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False

# if __name__ == "__main__":
    print("🧪 开始测试用户偏好API")
    print("⚠️  请确保后端服务已启动 (python -m app.main)")
    print("⚠️  请确保数据库中已存在测试用户（userId=1或2）")
    
    # 测试用户ID（请根据实际情况修改）
    test_user_id = 1
    
    # 1. 先获取用户偏好（查看当前状态）
    test_get_user_preferences(test_user_id)
    
    # 2. 更新用户偏好
    test_update_user_preferences(test_user_id)
    
    # 3. 再次获取，验证更新是否成功
    test_get_user_preferences(test_user_id)
    
    # 4. 测试部分更新
    test_partial_update(test_user_id)
    
    # 5. 最终获取，验证部分更新
    test_get_user_preferences(test_user_id)
    
    print(f"\n{'='*50}")
    print("✅ 测试完成")
    print(f"{'='*50}")
    
if __name__ == "__main__":
    test_register_user()

