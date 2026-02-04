"""
Phase 3 静态代码验证测试
验证前后端代码实现的正确性，不依赖数据库连接

测试内容：
1. 后端API路由定义正确
2. 前端API接口定义与后端匹配
3. Pydantic数据模型正确
4. 代码逻辑验证
"""
import os
import re
import sys
import ast
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "Backend" / "lifehub-backend"
FRONTEND_ROOT = PROJECT_ROOT / "Frontend" / "lifehub-frontend"


def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name: str, passed: bool, detail: str = ""):
    """打印测试结果"""
    status = "✅ 通过" if passed else "❌ 失败"
    print(f"  {name}: {status}")
    if detail:
        print(f"    └─ {detail}")


class Phase3Verifier:
    """Phase 3 代码验证器"""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, name: str, passed: bool, detail: str = ""):
        """添加测试结果"""
        self.results.append((name, passed, detail))
        print_result(name, passed, detail)
    
    def verify_backend_routes(self) -> bool:
        """验证后端API路由定义"""
        print_header("1. 验证后端API路由定义")
        
        food_router_path = BACKEND_ROOT / "app" / "routers" / "food.py"
        
        if not food_router_path.exists():
            self.add_result("food.py存在", False, f"文件不存在: {food_router_path}")
            return False
        
        self.add_result("food.py存在", True)
        
        content = food_router_path.read_text(encoding='utf-8')
        
        # 检查PUT /api/food/diet/{record_id} 路由
        put_route_pattern = r'@router\.put\(["\']\/diet\/\{record_id\}["\']'
        has_put_route = bool(re.search(put_route_pattern, content))
        self.add_result("PUT /diet/{record_id} 路由", has_put_route, 
                       "更新饮食记录路由" if has_put_route else "未找到更新路由")
        
        # 检查DELETE /api/food/diet/{record_id} 路由
        delete_route_pattern = r'@router\.delete\(["\']\/diet\/\{record_id\}["\']'
        has_delete_route = bool(re.search(delete_route_pattern, content))
        self.add_result("DELETE /diet/{record_id} 路由", has_delete_route,
                       "删除饮食记录路由" if has_delete_route else "未找到删除路由")
        
        # 检查update_diet_record函数
        has_update_func = "async def update_diet_record" in content
        self.add_result("update_diet_record函数", has_update_func)
        
        # 检查delete_diet_record函数
        has_delete_func = "async def delete_diet_record" in content
        self.add_result("delete_diet_record函数", has_delete_func)
        
        # 检查权限校验
        has_permission_check = "record.user_id != " in content and "HTTPException(status_code=403" in content
        self.add_result("权限校验(403)", has_permission_check, 
                       "检查只能操作自己的记录")
        
        # 检查404错误处理
        has_404_check = "HTTPException(status_code=404" in content
        self.add_result("404错误处理", has_404_check,
                       "记录不存在时返回404")
        
        return all([has_put_route, has_delete_route, has_update_func, 
                   has_delete_func, has_permission_check, has_404_check])
    
    def verify_backend_models(self) -> bool:
        """验证后端Pydantic数据模型"""
        print_header("2. 验证后端Pydantic数据模型")
        
        food_model_path = BACKEND_ROOT / "app" / "models" / "food.py"
        
        if not food_model_path.exists():
            self.add_result("food.py模型存在", False)
            return False
        
        self.add_result("food.py模型存在", True)
        
        content = food_model_path.read_text(encoding='utf-8')
        
        # 检查UpdateDietRecordRequest模型
        has_update_request = "class UpdateDietRecordRequest" in content
        self.add_result("UpdateDietRecordRequest模型", has_update_request)
        
        # 检查必要字段
        has_userid = "userId" in content or "user_id" in content
        self.add_result("userId字段", has_userid)
        
        has_optional_fields = "Optional[" in content or "| None" in content
        self.add_result("支持可选字段更新", has_optional_fields,
                       "部分更新需要可选字段")
        
        return has_update_request and has_userid
    
    def verify_frontend_api_service(self) -> bool:
        """验证前端ApiService接口定义"""
        print_header("3. 验证前端ApiService接口定义")
        
        api_service_path = FRONTEND_ROOT / "app" / "src" / "main" / "java" / "com" / "example" / "lifehub" / "network" / "ApiService.kt"
        
        if not api_service_path.exists():
            self.add_result("ApiService.kt存在", False)
            return False
        
        self.add_result("ApiService.kt存在", True)
        
        content = api_service_path.read_text(encoding='utf-8')
        
        # 检查PUT接口
        has_put_annotation = '@PUT("/api/food/diet/{record_id}")' in content
        self.add_result("@PUT注解", has_put_annotation)
        
        has_update_method = "suspend fun updateDietRecord" in content
        self.add_result("updateDietRecord方法", has_update_method)
        
        # 检查DELETE接口
        has_delete_annotation = '@DELETE("/api/food/diet/{record_id}")' in content
        self.add_result("@DELETE注解", has_delete_annotation)
        
        has_delete_method = "suspend fun deleteDietRecord" in content
        self.add_result("deleteDietRecord方法", has_delete_method)
        
        # 检查路径参数
        has_path_param = '@Path("record_id")' in content
        self.add_result("@Path参数", has_path_param)
        
        # 检查请求体
        has_body_param = "UpdateDietRecordRequest" in content
        self.add_result("UpdateDietRecordRequest参数", has_body_param)
        
        return all([has_put_annotation, has_update_method, has_delete_annotation,
                   has_delete_method, has_path_param, has_body_param])
    
    def verify_frontend_data_models(self) -> bool:
        """验证前端数据模型"""
        print_header("4. 验证前端数据模型")
        
        user_data_path = FRONTEND_ROOT / "app" / "src" / "main" / "java" / "com" / "example" / "lifehub" / "data" / "UserData.kt"
        
        if not user_data_path.exists():
            self.add_result("UserData.kt存在", False)
            return False
        
        self.add_result("UserData.kt存在", True)
        
        content = user_data_path.read_text(encoding='utf-8')
        
        # 检查UpdateDietRecordRequest
        has_update_request = "data class UpdateDietRecordRequest" in content
        self.add_result("UpdateDietRecordRequest类", has_update_request)
        
        # 检查UpdateDietRecordResponse
        has_update_response = "data class UpdateDietRecordResponse" in content
        self.add_result("UpdateDietRecordResponse类", has_update_response)
        
        # 检查DietRecordData
        has_record_data = "data class DietRecordData" in content
        self.add_result("DietRecordData类", has_record_data)
        
        # 检查可空类型支持
        has_nullable = "String? = null" in content or "Double? = null" in content
        self.add_result("可空类型支持", has_nullable,
                       "部分更新需要可空类型")
        
        return all([has_update_request, has_update_response, has_record_data])
    
    def verify_frontend_viewmodel(self) -> bool:
        """验证前端ViewModel"""
        print_header("5. 验证前端ViewModel")
        
        viewmodel_path = FRONTEND_ROOT / "app" / "src" / "main" / "java" / "com" / "example" / "lifehub" / "viewmodel" / "FoodViewModel.kt"
        
        if not viewmodel_path.exists():
            self.add_result("FoodViewModel.kt存在", False)
            return False
        
        self.add_result("FoodViewModel.kt存在", True)
        
        content = viewmodel_path.read_text(encoding='utf-8')
        
        # 检查UpdateDietRecordState
        has_update_state = "sealed class UpdateDietRecordState" in content
        self.add_result("UpdateDietRecordState状态类", has_update_state)
        
        # 检查DeleteDietRecordState
        has_delete_state = "sealed class DeleteDietRecordState" in content
        self.add_result("DeleteDietRecordState状态类", has_delete_state)
        
        # 检查updateDietRecord方法
        has_update_method = "fun updateDietRecord(" in content
        self.add_result("updateDietRecord方法", has_update_method)
        
        # 检查deleteDietRecord方法
        has_delete_method = "fun deleteDietRecord(" in content
        self.add_result("deleteDietRecord方法", has_delete_method)
        
        # 检查状态Flow
        has_update_flow = "_updateDietRecordState" in content
        self.add_result("updateDietRecordState Flow", has_update_flow)
        
        has_delete_flow = "_deleteDietRecordState" in content
        self.add_result("deleteDietRecordState Flow", has_delete_flow)
        
        # 检查错误处理
        has_error_handling = "UpdateDietRecordState.Error" in content and "DeleteDietRecordState.Error" in content
        self.add_result("错误状态处理", has_error_handling)
        
        # 检查Loading状态
        has_loading_state = "UpdateDietRecordState.Loading" in content and "DeleteDietRecordState.Loading" in content
        self.add_result("Loading状态处理", has_loading_state)
        
        return all([has_update_state, has_delete_state, has_update_method,
                   has_delete_method, has_update_flow, has_delete_flow,
                   has_error_handling, has_loading_state])
    
    def verify_api_contract_match(self) -> bool:
        """验证前后端API契约匹配"""
        print_header("6. 验证前后端API契约匹配")
        
        # 读取后端路由
        backend_food_path = BACKEND_ROOT / "app" / "routers" / "food.py"
        backend_content = backend_food_path.read_text(encoding='utf-8') if backend_food_path.exists() else ""
        
        # 读取前端API
        frontend_api_path = FRONTEND_ROOT / "app" / "src" / "main" / "java" / "com" / "example" / "lifehub" / "network" / "ApiService.kt"
        frontend_content = frontend_api_path.read_text(encoding='utf-8') if frontend_api_path.exists() else ""
        
        # 检查路径匹配
        backend_has_diet_path = "/diet/{record_id}" in backend_content
        frontend_has_diet_path = "/api/food/diet/{record_id}" in frontend_content
        self.add_result("路径匹配 /api/food/diet/{record_id}", 
                       backend_has_diet_path and frontend_has_diet_path)
        
        # 检查HTTP方法匹配
        backend_has_put = "@router.put" in backend_content
        frontend_has_put = "@PUT" in frontend_content
        self.add_result("PUT方法匹配", backend_has_put and frontend_has_put)
        
        backend_has_delete = "@router.delete" in backend_content
        frontend_has_delete = "@DELETE" in frontend_content
        self.add_result("DELETE方法匹配", backend_has_delete and frontend_has_delete)
        
        # 检查响应码匹配
        backend_has_200 = 'code=200' in backend_content or '"code": 200' in backend_content
        frontend_has_200_check = "response.code == 200" in frontend_content or ".code == 200" in frontend_content
        self.add_result("响应码200处理", backend_has_200)
        
        # 检查错误码处理
        backend_has_403 = "status_code=403" in backend_content
        backend_has_404 = "status_code=404" in backend_content
        self.add_result("后端403/404错误码", backend_has_403 and backend_has_404)
        
        return all([backend_has_diet_path, frontend_has_diet_path,
                   backend_has_put, frontend_has_put,
                   backend_has_delete, frontend_has_delete])
    
    def run_all_verifications(self) -> bool:
        """运行所有验证"""
        print("\n" + "🔍" * 30)
        print("   Phase 3 静态代码验证")
        print("🔍" * 30)
        print("\n验证前端饮食记录编辑/删除功能实现")
        print("(不依赖数据库连接)")
        
        all_passed = True
        
        all_passed &= self.verify_backend_routes()
        all_passed &= self.verify_backend_models()
        all_passed &= self.verify_frontend_api_service()
        all_passed &= self.verify_frontend_data_models()
        all_passed &= self.verify_frontend_viewmodel()
        all_passed &= self.verify_api_contract_match()
        
        # 打印汇总
        print_header("验证结果汇总")
        passed = sum(1 for _, p, _ in self.results if p)
        failed = sum(1 for _, p, _ in self.results if not p)
        
        print(f"\n  总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("\n🎉 所有验证通过！Phase 3 代码实现正确！")
            print("\n📝 Phase 3 实现内容：")
            print("  ✅ 后端 PUT /api/food/diet/{record_id} 更新接口")
            print("  ✅ 后端 DELETE /api/food/diet/{record_id} 删除接口")
            print("  ✅ 后端权限校验（只能操作自己的记录）")
            print("  ✅ 前端 ApiService 接口定义")
            print("  ✅ 前端数据模型（UpdateDietRecordRequest等）")
            print("  ✅ 前端 FoodViewModel 状态管理")
            print("  ✅ 前后端API契约一致")
        else:
            print(f"\n⚠️ 有 {failed} 项验证未通过，请检查代码实现")
            print("\n失败项：")
            for name, passed, detail in self.results:
                if not passed:
                    print(f"  ❌ {name}: {detail}")
        
        return failed == 0


if __name__ == "__main__":
    verifier = Phase3Verifier()
    success = verifier.run_all_verifications()
    sys.exit(0 if success else 1)
