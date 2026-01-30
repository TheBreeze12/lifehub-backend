"""
测试运动计划生成API（餐后运动规划）
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_generate_trip():
    """测试生成运动计划"""
    print(f"\n{'='*50}")
    print("测试：生成运动计划（餐后运动规划）")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/generate"
    
    # 测试数据
    payload = {
        "userId": 1,
        "query": "规划餐后运动，消耗300卡路里",
        "preferences": {
            "healthGoal": "reduce_fat",
            "allergens": []
        }
    }
    
    try:
        print(f"请求URL: {url}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, json=payload)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200 and data.get("data"):
                trip_data = data["data"]
                print(f"\n✅ 运动计划生成成功！")
                print(f"计划ID: {trip_data.get('tripId')}")
                print(f"标题: {trip_data.get('title')}")
                print(f"运动区域: {trip_data.get('destination')}")
                print(f"运动日期: {trip_data.get('startDate')}")
                print(f"运动节点数: {len(trip_data.get('items', []))}")
                
                # 显示运动节点
                total_calories = 0
                if trip_data.get("items"):
                    print("\n运动安排：")
                    for i, item in enumerate(trip_data["items"], 1):
                        calories = item.get('cost', 0)
                        total_calories += calories
                        print(f"  {i}. [{item.get('dayIndex')}天] {item.get('startTime')} - {item.get('placeName')} ({item.get('placeType')})")
                        print(f"     时长: {item.get('duration')}分钟，消耗: {calories:.0f}卡路里")
                        if item.get("notes"):
                            print(f"     备注: {item.get('notes')}")
                    print(f"\n总消耗卡路里: {total_calories:.0f} kcal")
                
                return True
            else:
                print(f"❌ 生成失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_generate_trip_simple():
    """测试简单运动计划生成（无偏好）"""
    print(f"\n{'='*50}")
    print("测试：简单运动计划生成（无偏好）")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/generate"
    
    payload = {
        "userId": 1,
        "query": "餐后散步30分钟"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                print("✅ 简单行程生成成功！")
                return True
            else:
                print(f"❌ 生成失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 开始测试运动计划生成API（餐后运动规划）")
    print("⚠️  请确保后端服务已启动 (python -m app.main)")
    print("⚠️  请确保数据库中已存在测试用户（userId=1）")
    
    # 测试1：完整运动计划生成（带偏好）
    test_generate_trip()
    
    # 测试2：简单运动计划生成（无偏好）
    # test_generate_trip_simple()
    
    print(f"\n{'='*50}")
    print("✅ 测试完成")
    print(f"{'='*50}")

