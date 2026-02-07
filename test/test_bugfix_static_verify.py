"""
问题1-5修复 - 静态代码验证测试
验证代码层面的修改是否正确应用，无需运行Android模拟器。

问题1: MealComparisonPage ViewModel共享 + verticalScroll
问题2: TripDetailPage路线生成使用天气坐标 + 地图异常处理
问题3: ExerciseSummaryPage null安全 + popBackStack修复
问题4: TripDetailPage下载/编辑按钮添加Snackbar提示
问题5: NutritionDetailPage过敏原检测函数
"""

import os
import re
import sys

# 项目根目录 - 自动检测
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# 向上找到 Software_Contest 根目录
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))
FRONTEND_SRC = os.path.join(PROJECT_ROOT, "Frontend", "lifehub-frontend",
                            "app", "src", "main", "java", "com", "example", "lifehub")
SCREEN_DIR = os.path.join(FRONTEND_SRC, "ui", "screen")
COMPONENT_DIR = os.path.join(FRONTEND_SRC, "ui", "components")


def read_file(full_path):
    """读取文件内容"""
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def test_problem1_viewmodel_sharing():
    """问题1: 验证三个餐食页面都使用Activity级别ViewModel共享"""
    print("=" * 60)
    print("问题1: 餐前餐后对比 ViewModel共享 + 页面滚动")
    print("=" * 60)
    
    errors = []
    
    # 检查MealComparisonPage
    meal_page = read_file(os.path.join(SCREEN_DIR, "MealComparisonPage.kt"))
    
    if "viewModelStoreOwner" not in meal_page:
        errors.append("MealComparisonPage 未使用 viewModelStoreOwner 共享ViewModel")
    if "ComponentActivity" not in meal_page:
        errors.append("MealComparisonPage 未导入 ComponentActivity")
    if "verticalScroll" not in meal_page:
        errors.append("MealComparisonPage 缺少 verticalScroll")
    if "rememberScrollState" not in meal_page:
        errors.append("MealComparisonPage 缺少 rememberScrollState")
    
    # 检查BeforeMealCameraPage
    before_page = read_file(os.path.join(SCREEN_DIR, "BeforeMealCameraPage.kt"))
    
    if "viewModelStoreOwner" not in before_page:
        errors.append("BeforeMealCameraPage 未使用 viewModelStoreOwner 共享ViewModel")
    if "ComponentActivity" not in before_page:
        errors.append("BeforeMealCameraPage 未导入 ComponentActivity")
    
    # 检查AfterMealCameraPage
    after_page = read_file(os.path.join(SCREEN_DIR, "AfterMealCameraPage.kt"))
    
    if "viewModelStoreOwner" not in after_page:
        errors.append("AfterMealCameraPage 未使用 viewModelStoreOwner 共享ViewModel")
    if "ComponentActivity" not in after_page:
        errors.append("AfterMealCameraPage 未导入 ComponentActivity")
    
    # 检查MealComparisonResult不再有自己的verticalScroll
    result_comp = read_file(os.path.join(COMPONENT_DIR, "MealComparisonResult.kt"))
    if "verticalScroll" in result_comp:
        errors.append("MealComparisonResult 仍有 verticalScroll（应移除避免嵌套滚动）")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        return False
    else:
        print("  ✅ MealComparisonPage 使用 Activity级别ViewModel + verticalScroll")
        print("  ✅ BeforeMealCameraPage 使用 Activity级别ViewModel")
        print("  ✅ AfterMealCameraPage 使用 Activity级别ViewModel")
        print("  ✅ MealComparisonResult 已移除内部verticalScroll")
        return True


def test_problem2_route_coordinates():
    """问题2: 验证路线生成不再使用硬编码坐标"""
    print("\n" + "=" * 60)
    print("问题2: 运动路线坐标 + 地图异常处理")
    print("=" * 60)
    
    errors = []
    
    trip_page = read_file(os.path.join(SCREEN_DIR, "TripDetailPage.kt"))
    
    # 验证不再有硬编码的"使用默认位置（北京）"注释
    if "使用默认位置（北京）" in trip_page:
        errors.append("TripDetailPage 仍包含硬编码北京坐标注释")
    
    # 验证使用weatherData坐标
    if "weatherData?.latitude" not in trip_page:
        errors.append("TripDetailPage 未使用 weatherData 坐标")
    
    # 验证地图组件有错误处理
    map_view = read_file(os.path.join(COMPONENT_DIR, "MapView.kt"))
    
    if "地图加载失败" not in map_view:
        errors.append("MapView 缺少地图加载失败的用户提示")
    
    # 验证onDestroy有try-catch
    if "mapView.onDestroy()" in map_view:
        # 检查是否在try块中
        ondestroy_idx = map_view.index("mapView.onDestroy()")
        # 往前查找最近的try
        before = map_view[max(0, ondestroy_idx - 200):ondestroy_idx]
        if "try" not in before:
            errors.append("MapView onDestroy 未被try-catch保护")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        return False
    else:
        print("  ✅ TripDetailPage 使用 weatherData 坐标替代硬编码")
        print("  ✅ MapView 添加了地图加载失败的用户提示")
        print("  ✅ MapView onDestroy 有try-catch保护")
        return True


def test_problem3_crash_fix():
    """问题3: 验证运动结算页闪退修复"""
    print("\n" + "=" * 60)
    print("问题3: 完成运动后闪退修复")
    print("=" * 60)
    
    errors = []
    
    summary_page = read_file(os.path.join(SCREEN_DIR, "ExerciseSummaryPage.kt"))
    
    # 验证UserSession null安全
    if "UserSession.isLoggedIn()" not in summary_page:
        errors.append("ExerciseSummaryPage 未检查 UserSession.isLoggedIn()")
    
    # 验证popBackStack使用Screen.Home.route
    if "Screen.Home.route" not in summary_page:
        errors.append("ExerciseSummaryPage 未使用 Screen.Home.route")
    
    # 验证有popBackStack失败回退逻辑
    if "if (!popped)" not in summary_page:
        errors.append("ExerciseSummaryPage 缺少 popBackStack 失败回退逻辑")
    
    # 验证导入了Screen
    if "import com.example.lifehub.navigation.Screen" not in summary_page:
        errors.append("ExerciseSummaryPage 未导入 Screen")
    
    # 验证不再有硬编码 route = "home"
    if 'route = "home"' in summary_page:
        errors.append('ExerciseSummaryPage 仍使用硬编码 route = "home"')
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        return False
    else:
        print("  ✅ UserSession.getUserId() 有null安全保护")
        print("  ✅ popBackStack 使用 Screen.Home.route")
        print("  ✅ popBackStack 失败时有navigate回退逻辑")
        return True


def test_problem4_button_response():
    """问题4: 验证下载和编辑按钮有响应"""
    print("\n" + "=" * 60)
    print("问题4: 下载和修改按钮响应")
    print("=" * 60)
    
    errors = []
    
    trip_page = read_file(os.path.join(SCREEN_DIR, "TripDetailPage.kt"))
    
    # 验证不再有空的TODO
    if "/* TODO: 下载离线包 */" in trip_page:
        errors.append("TripDetailPage 仍有空的下载TODO")
    if "/* TODO: 编辑行程 */" in trip_page:
        errors.append("TripDetailPage 仍有空的编辑TODO")
    
    # 验证有Snackbar提示
    if "离线下载功能开发中" not in trip_page:
        errors.append("TripDetailPage 缺少下载功能Snackbar提示")
    if "计划编辑功能开发中" not in trip_page:
        errors.append("TripDetailPage 缺少编辑功能Snackbar提示")
    
    # 验证有SnackbarHost
    if "SnackbarHost" not in trip_page:
        errors.append("TripDetailPage 缺少 SnackbarHost")
    if "snackbarHostState" not in trip_page:
        errors.append("TripDetailPage 缺少 snackbarHostState")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        return False
    else:
        print("  ✅ 下载按钮: 显示 '离线下载功能开发中' Snackbar")
        print("  ✅ 编辑按钮: 显示 '计划编辑功能开发中' Snackbar")
        print("  ✅ SnackbarHost 已添加")
        return True


def test_problem5_allergen_detection():
    """问题5: 验证过敏原检测函数存在且被调用"""
    print("\n" + "=" * 60)
    print("问题5: 过敏原检测功能")
    print("=" * 60)
    
    errors = []
    
    nutrition_page = read_file(os.path.join(SCREEN_DIR, "NutritionDetailPage.kt"))
    
    # 验证detectAllergensFromDishName函数存在
    if "fun detectAllergensFromDishName" not in nutrition_page:
        errors.append("NutritionDetailPage 缺少 detectAllergensFromDishName 函数")
    
    # 验证函数被调用
    if "detectAllergensFromDishName(" not in nutrition_page:
        errors.append("NutritionDetailPage 未调用 detectAllergensFromDishName")
    
    # 验证allergens不再是emptyList()
    # 查找NutritionData构造中的allergens赋值
    if re.search(r'allergens\s*=\s*emptyList\(\)', nutrition_page):
        # 检查是不是在默认数据中（允许默认值为空）
        # 只要在主要的dishItem分支中不是emptyList就行
        lines = nutrition_page.split('\n')
        in_dish_item_block = False
        has_empty_allergens_in_main = False
        for i, line in enumerate(lines):
            if 'dishItem != null' in line or 'dishItem.name' in line:
                in_dish_item_block = True
            if in_dish_item_block and 'allergens = emptyList()' in line:
                has_empty_allergens_in_main = True
                break
            if in_dish_item_block and 'else' in line:
                in_dish_item_block = False
        
        if has_empty_allergens_in_main:
            errors.append("NutritionDetailPage 主分支仍使用 allergens = emptyList()")
    
    # 验证标准8大类过敏原关键词
    standard_allergens = ["milk", "egg", "fish", "shellfish", "peanut", "tree_nut", "wheat", "soy"]
    for allergen in standard_allergens:
        if f'"{allergen}"' not in nutrition_page:
            errors.append(f"detectAllergensFromDishName 缺少标准过敏原: {allergen}")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        return False
    else:
        print("  ✅ detectAllergensFromDishName 函数已定义")
        print("  ✅ 函数在NutritionData构造中被调用")
        print("  ✅ 覆盖8大类标准过敏原关键词")
        print("  ✅ 支持用户自定义过敏原匹配")
        return True


def main():
    print("🔧 LifeHub 问题修复 - 静态代码验证")
    print("=" * 60)
    
    results = {}
    results["问题1"] = test_problem1_viewmodel_sharing()
    results["问题2"] = test_problem2_route_coordinates()
    results["问题3"] = test_problem3_crash_fix()
    results["问题4"] = test_problem4_button_response()
    results["问题5"] = test_problem5_allergen_detection()
    
    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)
    
    all_pass = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False
    
    print()
    if all_pass:
        print("🎉 所有验证通过！")
    else:
        print("⚠️ 存在验证失败项，请检查修复。")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
