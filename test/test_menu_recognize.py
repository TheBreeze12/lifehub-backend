"""
测试菜单图片识别API
运行前请确保：
1. 后端服务已启动: uvicorn app.main:app --reload
2. 已设置DASHSCOPE_API_KEY环境变量
3. 准备一张菜单图片用于测试
"""
import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_recognize_menu(image_path: str, userId: int = None):
    """
    测试菜单图片识别
    
    Args:
        image_path: 图片文件路径
        userId: 用户ID（可选，用于根据健康目标生成推荐）
    """
    print(f"\n{'='*50}")
    print("测试：菜单图片识别")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/api/food/recognize"
    
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 错误：图片文件不存在: {image_path}")
        print("\n提示：请准备一张菜单图片用于测试")
        return False
    
    try:
        # 准备文件上传
        with open(image_path, 'rb') as f:
            files = {
                'image': (os.path.basename(image_path), f, 'image/jpeg')
            }
            
            # 准备表单数据
            data = {}
            if userId:
                data['userId'] = userId
            
            print(f"请求URL: {url}")
            print(f"图片文件: {image_path}")
            if userId:
                print(f"用户ID: {userId}")
            print("\n正在识别菜单...")
            
            # 发送请求
            response = requests.post(url, files=files, data=data)
            
            print(f"\n状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if result.get("code") == 200:
                    dishes = result.get("data", {}).get("dishes", [])
                    print(f"\n✅ 识别成功！共识别到 {len(dishes)} 个菜品")
                    print("-" * 50)
                    
                    for i, dish in enumerate(dishes, 1):
                        print(f"\n菜品 {i}: {dish.get('name')}")
                        print(f"  热量: {dish.get('calories')} kcal")
                        print(f"  蛋白质: {dish.get('protein')} g")
                        print(f"  脂肪: {dish.get('fat')} g")
                        print(f"  碳水: {dish.get('carbs')} g")
                        print(f"  推荐: {'✅ 推荐' if dish.get('isRecommended') else '❌ 不推荐'}")
                        print(f"  理由: {dish.get('reason')}")
                    
                    return True
                else:
                    print(f"❌ 识别失败: {result.get('message')}")
                    return False
            else:
                print(f"❌ 请求失败: {response.text}")
                return False
                
    except FileNotFoundError:
        print(f"❌ 错误：找不到图片文件: {image_path}")
        return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_with_user_preferences(image_path: str, userId: int = 1):
    """测试带用户健康目标的识别"""
    print(f"\n{'='*50}")
    print("测试：带用户健康目标的菜单识别")
    print(f"{'='*50}")
    print("（会根据用户的健康目标生成个性化推荐）")
    
    return test_recognize_menu(image_path, userId=userId)


def main():
    """主函数"""
    print("=" * 50)
    print("菜单图片识别API测试")
    print("=" * 50)
    print("\n请确保：")
    print("1. 后端服务已启动: uvicorn app.main:app --reload")
    print("2. 已设置DASHSCOPE_API_KEY环境变量")
    print("3. 准备一张菜单图片用于测试")
    print()
    
    # 检查服务是否运行
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=2)
        if health_response.status_code != 200:
            print("⚠️ 后端服务可能未启动")
            return
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
        print("\n请先启动后端服务:")
        print("  cd backend")
        print("  uvicorn app.main:app --reload")
        return
    
    # 获取图片路径
    print("请输入菜单图片路径（或按回车使用默认路径）:")
    image_path = input("图片路径: ").strip()
    
    if not image_path:
        # 尝试查找常见的测试图片位置
        possible_paths = [
            "test_menu.jpg",
            "test_menu.png",
            "menu.jpg",
            "menu.png",
            "../test_images/menu.jpg",
            "test_images/menu.jpg"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                image_path = path
                print(f"使用默认路径: {image_path}")
                break
        else:
            print("❌ 未找到测试图片，请手动指定路径")
            return
    
    # 测试1: 不带用户ID的识别
    print("\n" + "=" * 50)
    print("测试1: 基础识别（不带用户健康目标）")
    print("=" * 50)
    test_recognize_menu(image_path)
    
    # 测试2: 带用户ID的识别
    print("\n" + "=" * 50)
    print("测试2: 个性化识别（带用户健康目标）")
    print("=" * 50)
    print("请输入用户ID（按回车跳过，默认使用userId=1）:")
    user_input = input("用户ID: ").strip()
    userId = int(user_input) if user_input else 1
    
    test_with_user_preferences(image_path, userId=userId)
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()

