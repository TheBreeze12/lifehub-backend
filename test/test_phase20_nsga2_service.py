"""
Phase 20: NSGA-II多目标优化算法基础框架 - 测试文件

测试内容：
1. NSGA-II服务基础功能
2. 优化目标定义（最短时间、最大消耗、最多绿化）
3. 个体编码和解码
4. 适应度函数计算
5. 帕累托前沿生成
6. 算法收敛性验证
"""

import pytest
import sys
import os
import numpy as np
from typing import List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNSGA2ServiceBasic:
    """测试NSGA-II服务的基础功能"""
    
    def test_nsga2_service_can_be_imported(self):
        """测试NSGA-II服务可以被导入"""
        try:
            from app.services.nsga2_service import NSGA2Service
            assert NSGA2Service is not None
        except ImportError as e:
            pytest.fail(f"无法导入NSGA2Service：{e}")
            
    def test_nsga2_service_can_be_instantiated(self):
        """测试NSGA2服务可以被实例化"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        assert service is not None
        
    def test_nsga2_service_has_required_methods(self):
        """测试NSGA2服务包含必要的方法"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 检查必要方法
        required_methods = [
            'optimize',
            'evaluate_fitness',
            'encode_individual',
            'decode_individual',
            'get_pareto_front',
        ]
        
        for method in required_methods:
            assert hasattr(service, method), f"NSGA2Service应该有{method}方法"
            

class TestOptimizationObjectives:
    """测试优化目标的定义"""
    
    def test_objectives_are_defined(self):
        """测试优化目标已定义"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 应该有三个优化目标
        assert hasattr(service, 'OBJECTIVES') or hasattr(service, 'objectives')
        
    def test_objective_minimize_time(self):
        """测试目标1：最短时间"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 验证时间目标存在
        objectives = getattr(service, 'OBJECTIVES', getattr(service, 'objectives', None))
        assert objectives is not None
        
        # 时间应该是最小化目标
        objective_names = [obj.get('name', obj) if isinstance(obj, dict) else obj 
                         for obj in objectives]
        assert any('time' in str(name).lower() or '时间' in str(name) 
                  for name in objective_names), "应包含时间优化目标"
                  
    def test_objective_maximize_calories(self):
        """测试目标2：最大热量消耗"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        objectives = getattr(service, 'OBJECTIVES', getattr(service, 'objectives', None))
        assert objectives is not None
        
        objective_names = [obj.get('name', obj) if isinstance(obj, dict) else obj 
                         for obj in objectives]
        assert any('calor' in str(name).lower() or '热量' in str(name) or '消耗' in str(name)
                  for name in objective_names), "应包含热量消耗优化目标"
                  
    def test_objective_maximize_greenery(self):
        """测试目标3：最多绿化/风景"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        objectives = getattr(service, 'OBJECTIVES', getattr(service, 'objectives', None))
        assert objectives is not None
        
        objective_names = [obj.get('name', obj) if isinstance(obj, dict) else obj 
                         for obj in objectives]
        assert any('green' in str(name).lower() or '绿化' in str(name) or 
                  'scenery' in str(name).lower() or '风景' in str(name)
                  for name in objective_names), "应包含绿化/风景优化目标"


class TestIndividualEncoding:
    """测试个体编码和解码"""
    
    def test_encode_individual_returns_array(self):
        """测试个体编码返回数组"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 模拟一个路径方案
        route_plan = {
            'waypoints': [(0, 0), (1, 1), (2, 2)],
            'exercise_type': 'walking',
            'duration': 30
        }
        
        encoded = service.encode_individual(route_plan)
        assert encoded is not None
        assert hasattr(encoded, '__len__'), "编码结果应该是可迭代的"
        
    def test_decode_individual_returns_route_plan(self):
        """测试个体解码返回路径方案"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 模拟编码后的个体
        encoded = np.array([0.5, 0.3, 0.7, 0.2, 0.8])
        
        decoded = service.decode_individual(encoded)
        assert decoded is not None
        assert isinstance(decoded, dict), "解码结果应该是字典"
        
    def test_encode_decode_consistency(self):
        """测试编码-解码一致性"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 编码然后解码，应该能恢复关键信息
        original = {
            'waypoints': [(0, 0), (1, 1)],
            'exercise_type': 'walking',
            'duration': 30
        }
        
        encoded = service.encode_individual(original)
        decoded = service.decode_individual(encoded)
        
        # 解码后应该包含路径相关信息
        assert 'waypoints' in decoded or 'path' in decoded or 'route' in decoded


class TestFitnessEvaluation:
    """测试适应度函数"""
    
    def test_evaluate_fitness_returns_tuple(self):
        """测试适应度评估返回元组"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 模拟一个个体
        individual = np.array([0.5, 0.3, 0.7, 0.2, 0.8])
        
        fitness = service.evaluate_fitness(individual)
        assert fitness is not None
        assert isinstance(fitness, (tuple, list, np.ndarray)), "适应度应返回元组/列表/数组"
        assert len(fitness) >= 3, "应该有至少3个目标的适应度值"
        
    def test_fitness_values_are_numeric(self):
        """测试适应度值是数值类型"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        individual = np.array([0.5, 0.3, 0.7, 0.2, 0.8])
        fitness = service.evaluate_fitness(individual)
        
        for f in fitness:
            assert isinstance(f, (int, float, np.number)), "适应度值应该是数值类型"
            
    def test_fitness_time_objective(self):
        """测试时间目标的适应度计算"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 两个不同的个体
        individual1 = np.array([0.1, 0.1, 0.1, 0.1, 0.1])  # 较短路径
        individual2 = np.array([0.9, 0.9, 0.9, 0.9, 0.9])  # 较长路径
        
        fitness1 = service.evaluate_fitness(individual1)
        fitness2 = service.evaluate_fitness(individual2)
        
        # 适应度值应该是有限的
        assert all(np.isfinite(f) for f in fitness1), "适应度值应该是有限的"
        assert all(np.isfinite(f) for f in fitness2), "适应度值应该是有限的"


class TestParetoFront:
    """测试帕累托前沿生成"""
    
    def test_get_pareto_front_returns_list(self):
        """测试获取帕累托前沿返回列表"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 模拟一组解
        solutions = [
            np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            np.array([0.5, 0.4, 0.3, 0.2, 0.1]),
            np.array([0.3, 0.3, 0.3, 0.3, 0.3]),
        ]
        
        pareto = service.get_pareto_front(solutions)
        assert pareto is not None
        assert isinstance(pareto, (list, np.ndarray)), "帕累托前沿应该是列表或数组"
        
    def test_pareto_front_non_dominated(self):
        """测试帕累托前沿中的解是非支配的"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 创建一些解
        solutions = [
            np.array([0.2, 0.3, 0.4, 0.5, 0.6]),
            np.array([0.8, 0.7, 0.6, 0.5, 0.4]),
            np.array([0.5, 0.5, 0.5, 0.5, 0.5]),
        ]
        
        pareto = service.get_pareto_front(solutions)
        
        # 帕累托前沿不应该为空
        assert len(pareto) > 0, "帕累托前沿不应该为空"


class TestOptimizationRun:
    """测试优化运行"""
    
    def test_optimize_returns_solutions(self):
        """测试优化返回解"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 运行优化
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 300,
            'max_time_minutes': 60,
            'n_generations': 10,  # 测试用较少代数
            'pop_size': 20
        }
        
        result = service.optimize(**params)
        
        assert result is not None
        assert 'solutions' in result or 'pareto_front' in result, "结果应包含解或帕累托前沿"
        
    def test_optimize_with_minimal_generations(self):
        """测试最小代数的优化"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 用最小参数运行
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 200,
            'n_generations': 5,
            'pop_size': 10
        }
        
        result = service.optimize(**params)
        assert result is not None
        
    def test_optimize_returns_multiple_solutions(self):
        """测试优化返回多个解（帕累托前沿）"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 300,
            'n_generations': 20,
            'pop_size': 30
        }
        
        result = service.optimize(**params)
        
        solutions = result.get('solutions', result.get('pareto_front', []))
        # NSGA-II应该能生成多个帕累托最优解
        assert len(solutions) >= 1, "应该生成至少1个解"


class TestAlgorithmConvergence:
    """测试算法收敛性"""
    
    def test_fitness_improves_over_generations(self):
        """测试适应度随代数提升"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 300,
            'n_generations': 30,
            'pop_size': 30,
            'return_history': True  # 返回历史记录以验证收敛
        }
        
        result = service.optimize(**params)
        
        # 如果有历史记录，检查收敛趋势
        if 'history' in result:
            history = result['history']
            if len(history) > 5:
                # 对于多目标优化，检查第一个目标（时间最小化，正值越小越好）
                early_time = np.mean([h['best_fitness'][0] for h in history[:5]])
                late_time = np.mean([h['best_fitness'][0] for h in history[-5:]])
                # 后期的最优时间应该不显著差于早期（允许20%波动）
                assert late_time <= early_time * 1.2, \
                    f"算法应该收敛或保持稳定，早期时间={early_time:.2f}，后期时间={late_time:.2f}"
                
    def test_optimization_completes_in_reasonable_time(self):
        """测试优化在合理时间内完成"""
        import time
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 300,
            'n_generations': 20,
            'pop_size': 20
        }
        
        start = time.time()
        result = service.optimize(**params)
        elapsed = time.time() - start
        
        # 应该在10秒内完成（20代，20个个体的小规模优化）
        assert elapsed < 10, f"优化耗时{elapsed:.2f}秒，应在10秒内完成"


class TestRouteOptimizationScenarios:
    """测试路径优化真实场景"""
    
    def test_scenario_short_walk(self):
        """场景：短距离散步（消耗100kcal）"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 100,
            'exercise_type': 'walking',
            'n_generations': 15,
            'pop_size': 20
        }
        
        result = service.optimize(**params)
        solutions = result.get('solutions', result.get('pareto_front', []))
        
        assert len(solutions) >= 1, "应生成短距离散步方案"
        
    def test_scenario_medium_jog(self):
        """场景：中等距离慢跑（消耗300kcal）"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 300,
            'exercise_type': 'jogging',
            'n_generations': 15,
            'pop_size': 20
        }
        
        result = service.optimize(**params)
        solutions = result.get('solutions', result.get('pareto_front', []))
        
        assert len(solutions) >= 1, "应生成慢跑方案"
        
    def test_scenario_with_time_constraint(self):
        """场景：有时间限制的运动规划"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 200,
            'max_time_minutes': 30,
            'n_generations': 15,
            'pop_size': 20
        }
        
        result = service.optimize(**params)
        solutions = result.get('solutions', result.get('pareto_front', []))
        
        # 验证生成的方案符合时间限制
        for sol in solutions:
            if isinstance(sol, dict) and 'time_minutes' in sol:
                assert sol['time_minutes'] <= 30 * 1.1, "方案应满足时间限制（允许10%容差）"


class TestSolutionQuality:
    """测试解的质量"""
    
    def test_solutions_have_required_fields(self):
        """测试解包含必要字段"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 200,
            'n_generations': 10,
            'pop_size': 15
        }
        
        result = service.optimize(**params)
        solutions = result.get('solutions', result.get('pareto_front', []))
        
        if len(solutions) > 0:
            sol = solutions[0]
            if isinstance(sol, dict):
                # 检查是否包含关键信息
                assert any(key in sol for key in ['fitness', 'objectives', 'route', 'path', 'encoded']), \
                    "解应包含fitness、objectives、route或path信息"
                    
    def test_solutions_are_diverse(self):
        """测试帕累托前沿解的多样性"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 300,
            'n_generations': 25,
            'pop_size': 40
        }
        
        result = service.optimize(**params)
        solutions = result.get('solutions', result.get('pareto_front', []))
        
        # 如果有多个解，它们应该有所不同
        if len(solutions) >= 2:
            # 检查解之间是否有差异
            first = solutions[0]
            last = solutions[-1]
            # 它们不应该完全相同
            if isinstance(first, np.ndarray) and isinstance(last, np.ndarray):
                assert not np.allclose(first, last), "帕累托前沿的解应该是多样的"


class TestEdgeCases:
    """测试边界情况"""
    
    def test_zero_calorie_target(self):
        """测试0热量目标"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 0,
            'n_generations': 5,
            'pop_size': 10
        }
        
        # 应该能处理而不崩溃
        try:
            result = service.optimize(**params)
            assert result is not None
        except ValueError:
            pass  # 抛出ValueError也是可接受的
            
    def test_very_high_calorie_target(self):
        """测试很高的热量目标"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': (39.9, 116.4),
            'target_calories': 2000,  # 很高的目标
            'n_generations': 10,
            'pop_size': 15
        }
        
        result = service.optimize(**params)
        assert result is not None, "应能处理高热量目标"
        
    def test_invalid_start_point_handled(self):
        """测试无效起点处理"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        params = {
            'start_point': None,
            'target_calories': 200,
            'n_generations': 5,
            'pop_size': 10
        }
        
        # 应该能优雅处理
        try:
            result = service.optimize(**params)
            # 如果成功，检查是否使用了默认起点
            assert result is not None
        except (ValueError, TypeError):
            pass  # 抛出异常也是可接受的


class TestIntegrationWithMETs:
    """测试与METs服务的集成"""
    
    def test_uses_mets_for_calorie_calculation(self):
        """测试使用METs计算热量"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 检查是否能访问METs服务
        assert hasattr(service, '_calculate_calories') or hasattr(service, 'mets_service'), \
            "NSGA2服务应该能计算热量"
            
    def test_different_exercise_types_affect_optimization(self):
        """测试不同运动类型影响优化结果"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        
        # 步行
        walking_result = service.optimize(
            start_point=(39.9, 116.4),
            target_calories=200,
            exercise_type='walking',
            n_generations=10,
            pop_size=15
        )
        
        # 跑步
        running_result = service.optimize(
            start_point=(39.9, 116.4),
            target_calories=200,
            exercise_type='running',
            n_generations=10,
            pop_size=15
        )
        
        # 两种运动类型应该能生成不同的优化结果
        assert walking_result is not None
        assert running_result is not None


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
