"""
测试行程生成API
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_generate_trip():
    """测试生成行程"""
    print(f"\n{'='*50}")
    print("测试：生成行程")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/generate"
    
    # 测试数据
    payload = {
        "userId": 1,
        "query": "规划周末带娃去杭州玩2天",
        "preferences": {
            "healthGoal": "reduce_fat",
            "allergens": ["海鲜", "花生"]
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
                print(f"\n✅ 行程生成成功！")
                print(f"行程ID: {trip_data.get('tripId')}")
                print(f"标题: {trip_data.get('title')}")
                print(f"目的地: {trip_data.get('destination')}")
                print(f"开始日期: {trip_data.get('startDate')}")
                print(f"结束日期: {trip_data.get('endDate')}")
                print(f"行程节点数: {len(trip_data.get('items', []))}")
                
                # 显示行程节点
                if trip_data.get("items"):
                    print("\n行程安排：")
                    for i, item in enumerate(trip_data["items"], 1):
                        print(f"  {i}. [{item.get('dayIndex')}天] {item.get('startTime')} - {item.get('placeName')} ({item.get('placeType')})")
                        if item.get("notes"):
                            print(f"     备注: {item.get('notes')}")
                
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
    """测试简单行程生成（无偏好）"""
    print(f"\n{'='*50}")
    print("测试：简单行程生成（无偏好）")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/generate"
    
    payload = {
        "userId": 1,
        "query": "去北京玩3天"
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
    print("🧪 开始测试行程生成API")
    print("⚠️  请确保后端服务已启动 (python -m app.main)")
    print("⚠️  请确保数据库中已存在测试用户（userId=1）")
    
    # 测试1：完整行程生成（带偏好）
    test_generate_trip()
    
    # 测试2：简单行程生成（无偏好）
    # test_generate_trip_simple()
    
    print(f"\n{'='*50}")
    print("✅ 测试完成")
    print(f"{'='*50}")

