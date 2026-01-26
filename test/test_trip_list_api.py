"""
测试行程列表和详情API
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_get_trip_list(user_id: int):
    """测试获取用户全部行程列表"""
    print(f"\n{'='*50}")
    print(f"测试：获取用户全部行程列表 (userId={user_id})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/list"
    params = {"userId": user_id}
    
    try:
        response = requests.get(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                trips = data.get("data", [])
                print(f"\n✅ 获取成功，共 {len(trips)} 个行程")
                for trip in trips:
                    print(f"  - {trip.get('title')} (ID: {trip.get('tripId')}, {trip.get('startDate')} ~ {trip.get('endDate')})")
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


def test_get_recent_trips(user_id: int, limit: int = 5):
    """测试获取最近行程"""
    print(f"\n{'='*50}")
    print(f"测试：获取最近行程 (userId={user_id}, limit={limit})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/recent"
    params = {"userId": user_id, "limit": limit}
    
    try:
        response = requests.get(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                trips = data.get("data", [])
                print(f"\n✅ 获取成功，共 {len(trips)} 个最近行程")
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


def test_get_home_trips(user_id: int, limit: int = 3):
    """测试获取首页行程"""
    print(f"\n{'='*50}")
    print(f"测试：获取首页行程 (userId={user_id}, limit={limit})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/home"
    params = {"userId": user_id, "limit": limit}
    
    try:
        response = requests.get(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                trips = data.get("data", [])
                print(f"\n✅ 获取成功，共 {len(trips)} 个首页行程")
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


def test_get_trip_detail(trip_id: int):
    """测试获取行程详情"""
    print(f"\n{'='*50}")
    print(f"测试：获取行程详情 (tripId={trip_id})")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/trip/{trip_id}"
    
    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and data.get("data"):
                trip_data = data["data"]
                print(f"\n✅ 获取成功！")
                print(f"标题: {trip_data.get('title')}")
                print(f"目的地: {trip_data.get('destination')}")
                print(f"日期: {trip_data.get('startDate')} ~ {trip_data.get('endDate')}")
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
                print(f"❌ 获取失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 开始测试行程列表和详情API")
    print("⚠️  请确保后端服务已启动 (python -m app.main)")
    print("⚠️  请确保数据库中已存在测试用户和行程数据")
    
    test_user_id = 1
    
    # 1. 获取用户全部行程列表
    test_get_trip_list(test_user_id)
    
    # 2. 获取最近行程
    test_get_recent_trips(test_user_id, limit=5)
    
    # 3. 获取首页行程
    test_get_home_trips(test_user_id, limit=3)
    
    # 4. 获取行程详情（需要先知道一个tripId）
    # 可以先运行test_get_trip_list获取tripId，然后测试
    # test_get_trip_detail(1)
    
    print(f"\n{'='*50}")
    print("✅ 测试完成")
    print(f"{'='*50}")
    print("\n💡 提示：如果要测试行程详情，请先运行test_get_trip_list获取tripId")

