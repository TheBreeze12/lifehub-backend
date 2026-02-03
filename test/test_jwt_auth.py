"""
JWT认证机制测试
测试Phase 1实现的JWT双令牌认证功能

测试场景:
1. 用户注册（密码bcrypt加密）
2. 用户登录获取JWT Token
3. 使用Access Token访问保护接口
4. 使用Refresh Token刷新Access Token
5. 无效Token测试
6. 过期Token测试
"""
import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from typing import Optional, Dict, Any

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_USER_NICKNAME = f"test_jwt_user_{int(time.time())}"
TEST_USER_PASSWORD = "TestPassword123!"


class JWTAuthTester:
    """JWT认证测试类"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.test_results: list = []
    
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}"
        if message:
            result += f": {message}"
        print(result)
        self.test_results.append((test_name, success, message))
    
    def test_register_user(self) -> bool:
        """测试1: 用户注册（密码bcrypt加密）"""
        print("\n" + "="*60)
        print("测试1: 用户注册（密码bcrypt加密）")
        print("="*60)
        
        url = f"{self.base_url}/api/user/register"
        payload = {
            "nickname": TEST_USER_NICKNAME,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("code") == 200:
                self.user_id = data.get("userId")
                self.log_result("用户注册", True, f"用户ID: {self.user_id}")
                return True
            else:
                self.log_result("用户注册", False, f"响应: {data}")
                return False
                
        except Exception as e:
            self.log_result("用户注册", False, f"异常: {str(e)}")
            return False
    
    def test_register_duplicate_user(self) -> bool:
        """测试1.1: 重复注册用户应失败"""
        print("\n" + "="*60)
        print("测试1.1: 重复注册用户应失败")
        print("="*60)
        
        url = f"{self.base_url}/api/user/register"
        payload = {
            "nickname": TEST_USER_NICKNAME,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            # 期望返回400错误
            if response.status_code == 400 or response.status_code == 500:
                self.log_result("重复注册拒绝", True, "正确拒绝重复注册")
                return True
            else:
                self.log_result("重复注册拒绝", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("重复注册拒绝", False, f"异常: {str(e)}")
            return False
    
    def test_login_with_jwt(self) -> bool:
        """测试2: 用户登录获取JWT Token"""
        print("\n" + "="*60)
        print("测试2: 用户登录获取JWT Token")
        print("="*60)
        
        url = f"{self.base_url}/api/user/login"
        payload = {
            "nickname": TEST_USER_NICKNAME,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("code") == 200:
                token_info = data.get("token")
                user_data = data.get("data")
                
                if token_info and "access_token" in token_info and "refresh_token" in token_info:
                    self.access_token = token_info["access_token"]
                    self.refresh_token = token_info["refresh_token"]
                    
                    # 验证Token格式（JWT应该有三段，用.分隔）
                    access_parts = self.access_token.split(".")
                    refresh_parts = self.refresh_token.split(".")
                    
                    if len(access_parts) == 3 and len(refresh_parts) == 3:
                        self.log_result("登录获取JWT", True, 
                            f"Access Token长度: {len(self.access_token)}, "
                            f"Refresh Token长度: {len(self.refresh_token)}, "
                            f"expires_in: {token_info.get('expires_in')}秒")
                        
                        # 验证用户数据
                        if user_data and user_data.get("userId"):
                            self.log_result("登录返回用户数据", True, 
                                f"userId: {user_data.get('userId')}, nickname: {user_data.get('nickname')}")
                        else:
                            self.log_result("登录返回用户数据", False, "用户数据缺失")
                        
                        return True
                    else:
                        self.log_result("登录获取JWT", False, "Token格式不正确")
                        return False
                else:
                    self.log_result("登录获取JWT", False, f"Token信息缺失: {data}")
                    return False
            else:
                self.log_result("登录获取JWT", False, f"响应: {data}")
                return False
                
        except Exception as e:
            self.log_result("登录获取JWT", False, f"异常: {str(e)}")
            return False
    
    def test_login_wrong_password(self) -> bool:
        """测试2.1: 错误密码登录应失败"""
        print("\n" + "="*60)
        print("测试2.1: 错误密码登录应失败")
        print("="*60)
        
        url = f"{self.base_url}/api/user/login"
        payload = {
            "nickname": TEST_USER_NICKNAME,
            "password": "WrongPassword123!"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 401:
                self.log_result("错误密码拒绝", True, "正确返回401")
                return True
            else:
                self.log_result("错误密码拒绝", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("错误密码拒绝", False, f"异常: {str(e)}")
            return False
    
    def test_login_nonexistent_user(self) -> bool:
        """测试2.2: 不存在的用户登录应失败"""
        print("\n" + "="*60)
        print("测试2.2: 不存在的用户登录应失败")
        print("="*60)
        
        url = f"{self.base_url}/api/user/login"
        payload = {
            "nickname": "nonexistent_user_12345",
            "password": "AnyPassword123!"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 404:
                self.log_result("不存在用户拒绝", True, "正确返回404")
                return True
            else:
                self.log_result("不存在用户拒绝", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("不存在用户拒绝", False, f"异常: {str(e)}")
            return False
    
    def test_access_protected_endpoint(self) -> bool:
        """测试3: 使用Access Token访问保护接口"""
        print("\n" + "="*60)
        print("测试3: 使用Access Token访问保护接口")
        print("="*60)
        
        if not self.access_token:
            self.log_result("访问保护接口", False, "没有Access Token")
            return False
        
        url = f"{self.base_url}/api/user/me"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("code") == 200:
                user_data = data.get("data")
                if user_data and user_data.get("nickname") == TEST_USER_NICKNAME:
                    self.log_result("访问保护接口", True, 
                        f"成功获取用户信息: {user_data.get('nickname')}")
                    return True
                else:
                    self.log_result("访问保护接口", False, f"用户数据不匹配: {user_data}")
                    return False
            else:
                self.log_result("访问保护接口", False, f"响应: {data}")
                return False
                
        except Exception as e:
            self.log_result("访问保护接口", False, f"异常: {str(e)}")
            return False
    
    def test_access_without_token(self) -> bool:
        """测试3.1: 不带Token访问保护接口应失败"""
        print("\n" + "="*60)
        print("测试3.1: 不带Token访问保护接口应失败")
        print("="*60)
        
        url = f"{self.base_url}/api/user/me"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 401:
                self.log_result("无Token拒绝访问", True, "正确返回401")
                return True
            else:
                self.log_result("无Token拒绝访问", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("无Token拒绝访问", False, f"异常: {str(e)}")
            return False
    
    def test_access_with_invalid_token(self) -> bool:
        """测试3.2: 无效Token访问保护接口应失败"""
        print("\n" + "="*60)
        print("测试3.2: 无效Token访问保护接口应失败")
        print("="*60)
        
        url = f"{self.base_url}/api/user/me"
        headers = {
            "Authorization": "Bearer invalid.token.here"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 401:
                self.log_result("无效Token拒绝", True, "正确返回401")
                return True
            else:
                self.log_result("无效Token拒绝", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("无效Token拒绝", False, f"异常: {str(e)}")
            return False
    
    def test_refresh_token(self) -> bool:
        """测试4: 使用Refresh Token刷新Access Token"""
        print("\n" + "="*60)
        print("测试4: 使用Refresh Token刷新Access Token")
        print("="*60)
        
        if not self.refresh_token:
            self.log_result("刷新Token", False, "没有Refresh Token")
            return False
        
        url = f"{self.base_url}/api/user/refresh"
        payload = {
            "refresh_token": self.refresh_token
        }
        
        old_access_token = self.access_token
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("code") == 200:
                token_info = data.get("token")
                
                if token_info and "access_token" in token_info:
                    new_access_token = token_info["access_token"]
                    new_refresh_token = token_info["refresh_token"]
                    
                    # 验证新Token与旧Token不同
                    if new_access_token != old_access_token:
                        self.access_token = new_access_token
                        self.refresh_token = new_refresh_token
                        self.log_result("刷新Token", True, "成功获取新Token")
                        
                        # 验证新Token可用
                        return self.test_new_token_works()
                    else:
                        self.log_result("刷新Token", False, "新旧Token相同")
                        return False
                else:
                    self.log_result("刷新Token", False, f"Token信息缺失: {data}")
                    return False
            else:
                self.log_result("刷新Token", False, f"响应: {data}")
                return False
                
        except Exception as e:
            self.log_result("刷新Token", False, f"异常: {str(e)}")
            return False
    
    def test_new_token_works(self) -> bool:
        """测试4.1: 验证刷新后的Token可用"""
        print("\n" + "="*60)
        print("测试4.1: 验证刷新后的Token可用")
        print("="*60)
        
        url = f"{self.base_url}/api/user/me"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("code") == 200:
                self.log_result("新Token可用", True, "刷新后的Token正常工作")
                return True
            else:
                self.log_result("新Token可用", False, f"响应: {data}")
                return False
                
        except Exception as e:
            self.log_result("新Token可用", False, f"异常: {str(e)}")
            return False
    
    def test_refresh_with_invalid_token(self) -> bool:
        """测试4.2: 无效Refresh Token应失败"""
        print("\n" + "="*60)
        print("测试4.2: 无效Refresh Token应失败")
        print("="*60)
        
        url = f"{self.base_url}/api/user/refresh"
        payload = {
            "refresh_token": "invalid.refresh.token"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 401:
                self.log_result("无效Refresh Token拒绝", True, "正确返回401")
                return True
            else:
                self.log_result("无效Refresh Token拒绝", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("无效Refresh Token拒绝", False, f"异常: {str(e)}")
            return False
    
    def test_legacy_login_still_works(self) -> bool:
        """测试5: 旧版登录接口仍然可用（向后兼容）"""
        print("\n" + "="*60)
        print("测试5: 旧版登录接口仍然可用（向后兼容）")
        print("="*60)
        
        url = f"{self.base_url}/api/user/data"
        params = {
            "nickname": TEST_USER_NICKNAME,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("code") == 200:
                user_data = data.get("data")
                if user_data and user_data.get("nickname") == TEST_USER_NICKNAME:
                    self.log_result("旧版登录兼容", True, "旧版接口正常工作")
                    return True
                else:
                    self.log_result("旧版登录兼容", False, f"用户数据不匹配: {user_data}")
                    return False
            else:
                self.log_result("旧版登录兼容", False, f"响应: {data}")
                return False
                
        except Exception as e:
            self.log_result("旧版登录兼容", False, f"异常: {str(e)}")
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("\n" + "="*70)
        print("JWT认证机制测试 - Phase 1")
        print(f"测试用户: {TEST_USER_NICKNAME}")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 检查服务是否可用
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ 后端服务不可用: {self.base_url}")
                return False
            print(f"✅ 后端服务正常: {self.base_url}")
        except Exception as e:
            print(f"❌ 无法连接到后端服务: {str(e)}")
            print("请确保后端服务已启动: uvicorn app.main:app --host 0.0.0.0 --port 8000")
            return False
        
        # 执行测试
        all_passed = True
        
        # 测试1: 用户注册
        if not self.test_register_user():
            all_passed = False
        
        # 测试1.1: 重复注册
        if not self.test_register_duplicate_user():
            all_passed = False
        
        # 测试2: JWT登录
        if not self.test_login_with_jwt():
            all_passed = False
            print("\n⚠️ 登录失败，跳过后续需要Token的测试")
        else:
            # 测试2.1: 错误密码
            if not self.test_login_wrong_password():
                all_passed = False
            
            # 测试2.2: 不存在的用户
            if not self.test_login_nonexistent_user():
                all_passed = False
            
            # 测试3: 访问保护接口
            if not self.test_access_protected_endpoint():
                all_passed = False
            
            # 测试3.1: 无Token访问
            if not self.test_access_without_token():
                all_passed = False
            
            # 测试3.2: 无效Token访问
            if not self.test_access_with_invalid_token():
                all_passed = False
            
            # 测试4: 刷新Token
            if not self.test_refresh_token():
                all_passed = False
            
            # 测试4.2: 无效Refresh Token
            if not self.test_refresh_with_invalid_token():
                all_passed = False
            
            # 测试5: 旧版登录兼容
            if not self.test_legacy_login_still_works():
                all_passed = False
        
        # 打印测试总结
        print("\n" + "="*70)
        print("测试总结")
        print("="*70)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = sum(1 for _, success, _ in self.test_results if not success)
        
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"总计: {len(self.test_results)}")
        
        if all_passed:
            print("\n✅ 所有测试通过！JWT认证机制实现正确。")
        else:
            print("\n❌ 部分测试失败，请检查实现。")
            print("\n失败的测试:")
            for name, success, msg in self.test_results:
                if not success:
                    print(f"  - {name}: {msg}")
        
        return all_passed


def test_auth_utils():
    """测试auth.py工具函数"""
    print("\n" + "="*70)
    print("测试 auth.py 工具函数")
    print("="*70)
    
    from app.utils.auth import (
        get_password_hash,
        verify_password,
        create_access_token,
        create_refresh_token,
        verify_access_token,
        verify_refresh_token,
        create_tokens
    )
    
    all_passed = True
    
    # 测试密码哈希
    print("\n测试密码哈希...")
    password = "TestPassword123!"
    hashed = get_password_hash(password)
    
    if hashed.startswith("$2b$"):
        print(f"  ✅ 密码哈希格式正确 (bcrypt)")
    else:
        print(f"  ❌ 密码哈希格式错误: {hashed[:20]}...")
        all_passed = False
    
    if verify_password(password, hashed):
        print(f"  ✅ 密码验证成功")
    else:
        print(f"  ❌ 密码验证失败")
        all_passed = False
    
    if not verify_password("WrongPassword", hashed):
        print(f"  ✅ 错误密码正确拒绝")
    else:
        print(f"  ❌ 错误密码应该被拒绝")
        all_passed = False
    
    # 测试Token创建和验证
    print("\n测试Token创建和验证...")
    user_id = 123
    nickname = "test_user"
    
    access_token, refresh_token = create_tokens(user_id, nickname)
    
    if len(access_token.split(".")) == 3:
        print(f"  ✅ Access Token格式正确 (JWT)")
    else:
        print(f"  ❌ Access Token格式错误")
        all_passed = False
    
    if len(refresh_token.split(".")) == 3:
        print(f"  ✅ Refresh Token格式正确 (JWT)")
    else:
        print(f"  ❌ Refresh Token格式错误")
        all_passed = False
    
    # 验证Access Token
    token_data = verify_access_token(access_token)
    if token_data and token_data.user_id == user_id:
        print(f"  ✅ Access Token验证成功，user_id: {token_data.user_id}")
    else:
        print(f"  ❌ Access Token验证失败")
        all_passed = False
    
    # 验证Refresh Token
    token_data = verify_refresh_token(refresh_token)
    if token_data and token_data.user_id == user_id:
        print(f"  ✅ Refresh Token验证成功，user_id: {token_data.user_id}")
    else:
        print(f"  ❌ Refresh Token验证失败")
        all_passed = False
    
    # 验证Token类型检查
    if verify_access_token(refresh_token) is None:
        print(f"  ✅ Refresh Token正确拒绝作为Access Token使用")
    else:
        print(f"  ❌ 应该拒绝Refresh Token作为Access Token使用")
        all_passed = False
    
    if verify_refresh_token(access_token) is None:
        print(f"  ✅ Access Token正确拒绝作为Refresh Token使用")
    else:
        print(f"  ❌ 应该拒绝Access Token作为Refresh Token使用")
        all_passed = False
    
    # 验证无效Token
    if verify_access_token("invalid.token.here") is None:
        print(f"  ✅ 无效Token正确拒绝")
    else:
        print(f"  ❌ 应该拒绝无效Token")
        all_passed = False
    
    if all_passed:
        print("\n✅ auth.py 工具函数测试全部通过！")
    else:
        print("\n❌ auth.py 工具函数测试部分失败！")
    
    return all_passed


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JWT认证机制测试")
    parser.add_argument("--unit", action="store_true", help="只运行单元测试（不需要后端服务）")
    parser.add_argument("--api", action="store_true", help="只运行API测试（需要后端服务）")
    parser.add_argument("--url", type=str, default=BASE_URL, help=f"后端服务URL，默认: {BASE_URL}")
    
    args = parser.parse_args()
    
    results = []
    
    if args.unit or (not args.unit and not args.api):
        # 运行单元测试
        results.append(("单元测试", test_auth_utils()))
    
    if args.api or (not args.unit and not args.api):
        # 运行API测试
        tester = JWTAuthTester(args.url)
        results.append(("API测试", tester.run_all_tests()))
    
    # 最终结果
    print("\n" + "="*70)
    print("最终测试结果")
    print("="*70)
    
    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    if all_passed:
        print("\n🎉 Phase 1 JWT认证机制测试全部通过！")
        exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查实现。")
        exit(1)
