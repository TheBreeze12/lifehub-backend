"""
NSGA-II (Non-dominated Sorting Genetic Algorithm II) 多目标优化服务

用于运动路径规划的多目标优化，同时优化：
1. 最短时间 - 最小化运动耗时
2. 最大消耗 - 最大化热量消耗
3. 最多绿化 - 最大化路径沿途绿化/风景评分

基于pymoo库实现NSGA-II算法

Phase 20 实现
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize
from pymoo.core.callback import Callback


class OptimizationHistory(Callback):
    """
    优化历史记录回调
    
    用于跟踪优化过程中的适应度变化，验证算法收敛性
    """
    
    def __init__(self):
        super().__init__()
        self.history = []
        
    def notify(self, algorithm):
        """每代结束时记录"""
        gen = algorithm.n_gen
        pop = algorithm.pop
        
        # 获取当前代的适应度
        F = pop.get("F")
        if F is not None and len(F) > 0:
            avg_fitness = np.mean(F, axis=0)
            best_fitness = np.min(F, axis=0)
            
            self.history.append({
                'generation': gen,
                'avg_fitness': avg_fitness.tolist(),
                'best_fitness': best_fitness.tolist(),
                'pop_size': len(pop)
            })


class RouteOptimizationProblem(Problem):
    """
    路径优化问题定义
    
    定义多目标优化问题的变量、目标和约束
    
    决策变量：
    - 路径点选择（编码为0-1之间的实数）
    - 每段路径的运动强度
    
    优化目标（3个）：
    1. 最小化总时间（分钟）
    2. 最大化热量消耗（kcal） -> 转为最小化负值
    3. 最大化绿化评分（0-100） -> 转为最小化负值
    """
    
    def __init__(
        self,
        n_waypoints: int = 5,
        start_point: Tuple[float, float] = (39.9, 116.4),
        target_calories: float = 300.0,
        max_time_minutes: int = 120,
        exercise_type: str = 'walking',
        weight_kg: float = 70.0,
        **kwargs
    ):
        """
        初始化路径优化问题
        
        Args:
            n_waypoints: 路径点数量
            start_point: 起点坐标 (lat, lng)
            target_calories: 目标热量消耗（kcal）
            max_time_minutes: 最大运动时间（分钟）
            exercise_type: 运动类型
            weight_kg: 用户体重
        """
        self.n_waypoints = n_waypoints
        self.start_point = start_point
        self.target_calories = target_calories
        self.max_time_minutes = max_time_minutes
        self.exercise_type = exercise_type
        self.weight_kg = weight_kg
        
        # 每个路径点有2个变量：x偏移、y偏移（相对于起点的归一化坐标）
        # 加上运动强度变量
        n_var = n_waypoints * 2 + 1  # waypoints + intensity
        
        # 3个目标：时间、热量（负）、绿化（负）
        n_obj = 3
        
        # 变量边界：[0, 1]
        xl = np.zeros(n_var)
        xu = np.ones(n_var)
        
        super().__init__(
            n_var=n_var,
            n_obj=n_obj,
            n_ieq_constr=1,  # 时间约束
            xl=xl,
            xu=xu,
            **kwargs
        )
        
        # METs值映射（简化版，从mets_service借用概念）
        self.mets_table = {
            'walking': 3.5,
            'brisk_walking': 4.3,
            'jogging': 7.0,
            'running': 8.0,
            'cycling': 6.0,
            'hiking': 5.3,
        }
        
        # 模拟绿化评分区域（真实场景从POI数据获取）
        # 这里用随机种子保证可重复性
        np.random.seed(42)
        self.greenery_map = np.random.rand(10, 10) * 100
        np.random.seed(None)
        
    def _evaluate(self, X, out, *args, **kwargs):
        """
        评估种群中所有个体的适应度
        
        Args:
            X: 种群矩阵，每行是一个个体
            out: 输出字典，包含目标函数值和约束违反量
        """
        n_pop = X.shape[0]
        
        # 初始化目标函数值
        F = np.zeros((n_pop, 3))  # 3个目标
        G = np.zeros((n_pop, 1))  # 1个约束
        
        for i in range(n_pop):
            individual = X[i]
            
            # 计算三个目标
            time_obj = self._calc_time(individual)
            calorie_obj = self._calc_calories(individual)
            greenery_obj = self._calc_greenery(individual)
            
            # 目标1：最小化时间
            F[i, 0] = time_obj
            
            # 目标2：最大化热量 -> 最小化负热量
            F[i, 1] = -calorie_obj
            
            # 目标3：最大化绿化 -> 最小化负绿化
            F[i, 2] = -greenery_obj
            
            # 约束：时间不超过最大限制
            G[i, 0] = time_obj - self.max_time_minutes
            
        out["F"] = F
        out["G"] = G
        
    def _calc_time(self, individual: np.ndarray) -> float:
        """
        计算路径总时间（分钟）
        
        基于路径长度和运动速度计算
        """
        # 提取路径点
        waypoints = self._decode_waypoints(individual)
        
        # 运动强度（影响速度）
        intensity = individual[-1]
        
        # 计算总距离（简化：曼哈顿距离 * 比例因子）
        total_distance = 0.0
        prev_point = self.start_point
        
        for wp in waypoints:
            # 简化距离计算（实际应使用地理距离）
            dist = abs(wp[0] - prev_point[0]) + abs(wp[1] - prev_point[1])
            total_distance += dist * 111  # 粗略转换为km（1度约111km）
            prev_point = wp
            
        # 回到起点
        dist = abs(prev_point[0] - self.start_point[0]) + abs(prev_point[1] - self.start_point[1])
        total_distance += dist * 111
        
        # 根据运动类型和强度计算速度（km/h）
        base_speed = self._get_base_speed()
        speed = base_speed * (0.7 + 0.6 * intensity)  # 强度影响速度
        
        # 时间 = 距离 / 速度（转换为分钟）
        if speed > 0:
            time_hours = total_distance / speed
            time_minutes = time_hours * 60
        else:
            time_minutes = 0
            
        return max(1.0, time_minutes)  # 至少1分钟
        
    def _calc_calories(self, individual: np.ndarray) -> float:
        """
        计算热量消耗（kcal）
        
        使用METs公式：消耗 = METs × 体重 × 时间(h)
        """
        time_minutes = self._calc_time(individual)
        intensity = individual[-1]
        
        # 获取基础METs
        base_mets = self.mets_table.get(self.exercise_type, 3.5)
        
        # 强度调整METs
        adjusted_mets = base_mets * (0.8 + 0.4 * intensity)
        
        # 计算热量：METs × 体重(kg) × 时间(h)
        time_hours = time_minutes / 60.0
        calories = adjusted_mets * self.weight_kg * time_hours
        
        return calories
        
    def _calc_greenery(self, individual: np.ndarray) -> float:
        """
        计算路径绿化评分（0-100）
        
        基于路径经过区域的绿化度
        """
        waypoints = self._decode_waypoints(individual)
        
        total_greenery = 0.0
        n_points = len(waypoints) + 1  # 包括起点
        
        # 评估每个路径点的绿化
        for wp in waypoints:
            # 将坐标映射到绿化地图
            grid_x = int(wp[0] * 10) % 10
            grid_y = int(wp[1] * 10) % 10
            total_greenery += self.greenery_map[grid_x, grid_y]
            
        avg_greenery = total_greenery / max(1, len(waypoints))
        return avg_greenery
        
    def _decode_waypoints(self, individual: np.ndarray) -> List[Tuple[float, float]]:
        """
        从个体编码解码路径点
        """
        waypoints = []
        for i in range(self.n_waypoints):
            # 每个路径点由两个变量表示（x, y偏移）
            x_offset = individual[i * 2]
            y_offset = individual[i * 2 + 1]
            
            # 相对于起点的偏移（约±0.01度，约1km范围）
            lat = self.start_point[0] + (x_offset - 0.5) * 0.02
            lng = self.start_point[1] + (y_offset - 0.5) * 0.02
            
            waypoints.append((lat, lng))
            
        return waypoints
        
    def _get_base_speed(self) -> float:
        """
        获取基础运动速度（km/h）
        """
        speed_map = {
            'walking': 4.5,
            'brisk_walking': 6.0,
            'jogging': 7.5,
            'running': 10.0,
            'cycling': 18.0,
            'hiking': 4.0,
        }
        return speed_map.get(self.exercise_type, 4.5)


class NSGA2Service:
    """
    NSGA-II多目标优化服务
    
    提供运动路径的多目标优化功能，同时考虑时间、热量消耗和绿化程度
    """
    
    # 优化目标定义
    OBJECTIVES = [
        {
            'name': 'time',
            'name_cn': '运动时间',
            'direction': 'minimize',
            'unit': '分钟',
            'description': '最小化运动耗时'
        },
        {
            'name': 'calories',
            'name_cn': '热量消耗',
            'direction': 'maximize',
            'unit': 'kcal',
            'description': '最大化热量消耗'
        },
        {
            'name': 'greenery',
            'name_cn': '绿化评分',
            'direction': 'maximize',
            'unit': '分',
            'description': '最大化路径沿途绿化/风景评分'
        }
    ]
    
    def __init__(self):
        """初始化NSGA-II服务"""
        # 尝试导入METs服务
        try:
            from app.services.mets_service import get_mets_service
            self.mets_service = get_mets_service()
        except ImportError:
            self.mets_service = None
            
        # 存储优化目标
        self.objectives = self.OBJECTIVES
        
    def optimize(
        self,
        start_point: Tuple[float, float] = (39.9, 116.4),
        target_calories: float = 300.0,
        max_time_minutes: int = 120,
        exercise_type: str = 'walking',
        weight_kg: float = 70.0,
        n_generations: int = 50,
        pop_size: int = 40,
        n_waypoints: int = 5,
        return_history: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行多目标优化
        
        Args:
            start_point: 起点坐标 (lat, lng)
            target_calories: 目标热量消耗
            max_time_minutes: 最大运动时间
            exercise_type: 运动类型
            weight_kg: 用户体重
            n_generations: 迭代代数
            pop_size: 种群大小
            n_waypoints: 路径点数量
            return_history: 是否返回优化历史
            
        Returns:
            包含帕累托前沿解和相关信息的字典
        """
        # 参数验证
        if start_point is None:
            start_point = (39.9, 116.4)  # 默认北京
            
        if target_calories <= 0:
            return {
                'solutions': [],
                'pareto_front': [],
                'message': '目标热量必须大于0'
            }
            
        # 创建优化问题
        problem = RouteOptimizationProblem(
            n_waypoints=n_waypoints,
            start_point=start_point,
            target_calories=target_calories,
            max_time_minutes=max_time_minutes,
            exercise_type=exercise_type,
            weight_kg=weight_kg
        )
        
        # 配置NSGA-II算法
        algorithm = NSGA2(
            pop_size=pop_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(eta=20),
            eliminate_duplicates=True
        )
        
        # 创建历史记录回调
        history_callback = OptimizationHistory() if return_history else None
        
        # 执行优化
        minimize_kwargs = {
            'problem': problem,
            'algorithm': algorithm,
            'termination': ('n_gen', n_generations),
            'seed': 42,  # 可重复性
            'verbose': False,
        }
        
        # 只有当callback不为None时才添加
        if history_callback is not None:
            minimize_kwargs['callback'] = history_callback
            
        result = minimize(**minimize_kwargs)
        
        # 处理结果
        solutions = self._process_results(result, problem)
        
        response = {
            'solutions': solutions,
            'pareto_front': solutions,  # 同义词
            'n_solutions': len(solutions),
            'objectives': self.OBJECTIVES,
            'parameters': {
                'start_point': start_point,
                'target_calories': target_calories,
                'max_time_minutes': max_time_minutes,
                'exercise_type': exercise_type,
                'n_generations': n_generations,
                'pop_size': pop_size
            }
        }
        
        if return_history and history_callback:
            response['history'] = history_callback.history
            
        return response
        
    def _process_results(
        self,
        result,
        problem: RouteOptimizationProblem
    ) -> List[Dict[str, Any]]:
        """
        处理优化结果
        
        Args:
            result: pymoo优化结果
            problem: 优化问题实例
            
        Returns:
            处理后的解列表
        """
        solutions = []
        
        if result.X is None or len(result.X) == 0:
            return solutions
            
        # 处理每个帕累托前沿解
        X = result.X if result.X.ndim > 1 else result.X.reshape(1, -1)
        F = result.F if result.F.ndim > 1 else result.F.reshape(1, -1)
        
        for i in range(len(X)):
            individual = X[i]
            fitness = F[i]
            
            # 解码路径
            waypoints = problem._decode_waypoints(individual)
            
            # 构建解信息
            solution = {
                'id': i + 1,
                'encoded': individual.tolist(),
                'fitness': fitness.tolist(),
                'objectives': {
                    'time_minutes': fitness[0],
                    'calories_kcal': -fitness[1],  # 恢复正值
                    'greenery_score': -fitness[2]  # 恢复正值
                },
                'route': {
                    'start_point': problem.start_point,
                    'waypoints': waypoints,
                    'n_waypoints': len(waypoints)
                },
                'intensity': individual[-1],
                'exercise_type': problem.exercise_type
            }
            
            solutions.append(solution)
            
        # 按时间排序（用户通常更关心时间）
        solutions.sort(key=lambda x: x['objectives']['time_minutes'])
        
        return solutions
        
    def evaluate_fitness(
        self,
        individual: Union[np.ndarray, List[float]],
        start_point: Tuple[float, float] = (39.9, 116.4),
        exercise_type: str = 'walking',
        weight_kg: float = 70.0,
        max_time_minutes: int = 120
    ) -> Tuple[float, float, float]:
        """
        评估单个个体的适应度
        
        Args:
            individual: 个体编码
            start_point: 起点坐标
            exercise_type: 运动类型
            weight_kg: 体重
            max_time_minutes: 最大时间
            
        Returns:
            (时间, 热量, 绿化) 三元组
        """
        if isinstance(individual, list):
            individual = np.array(individual)
            
        # 确定路径点数量
        n_waypoints = (len(individual) - 1) // 2
        
        # 创建问题实例用于评估
        problem = RouteOptimizationProblem(
            n_waypoints=n_waypoints,
            start_point=start_point,
            exercise_type=exercise_type,
            weight_kg=weight_kg,
            max_time_minutes=max_time_minutes
        )
        
        # 计算各目标
        time_val = problem._calc_time(individual)
        calories_val = problem._calc_calories(individual)
        greenery_val = problem._calc_greenery(individual)
        
        return (time_val, calories_val, greenery_val)
        
    def encode_individual(self, route_plan: Dict[str, Any]) -> np.ndarray:
        """
        将路径方案编码为个体
        
        Args:
            route_plan: 路径方案字典
            
        Returns:
            编码后的个体（numpy数组）
        """
        waypoints = route_plan.get('waypoints', [])
        intensity = route_plan.get('intensity', 0.5)
        
        if not waypoints:
            # 默认5个路径点
            return np.random.rand(11)  # 5*2 + 1
            
        # 编码路径点
        n_waypoints = len(waypoints)
        individual = np.zeros(n_waypoints * 2 + 1)
        
        # 获取起点（用于归一化）
        start = route_plan.get('start_point', (39.9, 116.4))
        
        for i, wp in enumerate(waypoints):
            # 归一化到[0, 1]范围
            x_norm = (wp[0] - start[0]) / 0.02 + 0.5
            y_norm = (wp[1] - start[1]) / 0.02 + 0.5
            
            individual[i * 2] = np.clip(x_norm, 0, 1)
            individual[i * 2 + 1] = np.clip(y_norm, 0, 1)
            
        # 强度
        individual[-1] = intensity
        
        return individual
        
    def decode_individual(
        self,
        individual: Union[np.ndarray, List[float]],
        start_point: Tuple[float, float] = (39.9, 116.4)
    ) -> Dict[str, Any]:
        """
        将个体解码为路径方案
        
        Args:
            individual: 编码的个体
            start_point: 起点坐标
            
        Returns:
            路径方案字典
        """
        if isinstance(individual, list):
            individual = np.array(individual)
            
        n_waypoints = (len(individual) - 1) // 2
        
        # 解码路径点
        waypoints = []
        for i in range(n_waypoints):
            x_offset = individual[i * 2]
            y_offset = individual[i * 2 + 1]
            
            lat = start_point[0] + (x_offset - 0.5) * 0.02
            lng = start_point[1] + (y_offset - 0.5) * 0.02
            
            waypoints.append((lat, lng))
            
        return {
            'start_point': start_point,
            'waypoints': waypoints,
            'intensity': individual[-1],
            'n_waypoints': n_waypoints
        }
        
    def get_pareto_front(
        self,
        solutions: List[Union[np.ndarray, List[float]]],
        start_point: Tuple[float, float] = (39.9, 116.4),
        exercise_type: str = 'walking',
        weight_kg: float = 70.0
    ) -> List[np.ndarray]:
        """
        从一组解中提取帕累托前沿
        
        Args:
            solutions: 解列表
            start_point: 起点
            exercise_type: 运动类型
            weight_kg: 体重
            
        Returns:
            帕累托前沿解列表
        """
        if not solutions:
            return []
            
        # 计算每个解的适应度
        fitness_list = []
        for sol in solutions:
            if isinstance(sol, list):
                sol = np.array(sol)
            fitness = self.evaluate_fitness(
                sol, start_point, exercise_type, weight_kg
            )
            # 转换为最小化形式：时间最小化，热量和绿化取负
            fitness_list.append((fitness[0], -fitness[1], -fitness[2]))
            
        fitness_array = np.array(fitness_list)
        
        # 非支配排序
        pareto_indices = self._non_dominated_sort(fitness_array)
        
        return [solutions[i] for i in pareto_indices]
        
    def _non_dominated_sort(self, fitness: np.ndarray) -> List[int]:
        """
        非支配排序，返回第一层（帕累托前沿）的索引
        
        Args:
            fitness: 适应度矩阵
            
        Returns:
            帕累托前沿解的索引列表
        """
        n = len(fitness)
        dominated_count = np.zeros(n, dtype=int)
        
        # 计算每个解被支配的次数
        for i in range(n):
            for j in range(n):
                if i != j:
                    if self._dominates(fitness[j], fitness[i]):
                        dominated_count[i] += 1
                        
        # 返回不被任何解支配的解（帕累托前沿）
        return [i for i in range(n) if dominated_count[i] == 0]
        
    def _dominates(self, f1: np.ndarray, f2: np.ndarray) -> bool:
        """
        判断f1是否支配f2（最小化问题）
        
        f1支配f2当且仅当：f1在所有目标上都不差于f2，且至少在一个目标上严格更好
        """
        better_in_at_least_one = False
        for i in range(len(f1)):
            if f1[i] > f2[i]:
                return False
            if f1[i] < f2[i]:
                better_in_at_least_one = True
        return better_in_at_least_one
        
    def _calculate_calories(
        self,
        exercise_type: str,
        duration_minutes: int,
        weight_kg: float
    ) -> float:
        """
        计算热量消耗（使用METs服务或内置计算）
        
        Args:
            exercise_type: 运动类型
            duration_minutes: 时长（分钟）
            weight_kg: 体重（kg）
            
        Returns:
            热量消耗（kcal）
        """
        if self.mets_service:
            return self.mets_service.calculate_calories(
                exercise_type, weight_kg, duration_minutes
            )
        else:
            # 内置简化计算
            mets_table = {
                'walking': 3.5,
                'brisk_walking': 4.3,
                'jogging': 7.0,
                'running': 8.0,
                'cycling': 6.0,
            }
            mets = mets_table.get(exercise_type, 3.5)
            return mets * weight_kg * (duration_minutes / 60.0)


# 单例实例
_nsga2_service_instance: Optional[NSGA2Service] = None


def get_nsga2_service() -> NSGA2Service:
    """获取NSGA-II服务单例"""
    global _nsga2_service_instance
    if _nsga2_service_instance is None:
        _nsga2_service_instance = NSGA2Service()
    return _nsga2_service_instance
