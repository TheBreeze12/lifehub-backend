"""
简单的菜单识别测试脚本（快速测试用）
使用方法：
python test_menu_recognize_simple.py <图片路径> [用户ID]
"""
import requests
import json
import sys
import os

BASE_URL = "http://localhost:8000"


def test_recognize(image_path: str, userId: int = None):
    """快速测试菜单识别"""
    url = f"{BASE_URL}/api/food/recognize"
    
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
            data = {'userId': userId} if userId else {}
            
            print(f"正在识别: {image_path}")
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                dishes = result.get("data", {}).get("dishes", [])
                
                print(f"\n✅ 识别成功！共 {len(dishes)} 个菜品\n")
                for dish in dishes:
                    print(f"  {dish['name']}")
                    print(f"    热量: {dish['calories']} kcal | "
                          f"蛋白质: {dish['protein']}g | "
                          f"脂肪: {dish['fat']}g | "
                          f"碳水: {dish['carbs']}g")
                    print(f"    推荐: {'✅' if dish['isRecommended'] else '❌'} {dish['reason']}\n")
            else:
                print(f"❌ 失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python test_menu_recognize_simple.py <图片路径> [用户ID]")
        print("示例: python test_menu_recognize_simple.py menu.jpg 1")
        sys.exit(1)
    
    image_path = sys.argv[1]
    userId = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    test_recognize(image_path, userId)

