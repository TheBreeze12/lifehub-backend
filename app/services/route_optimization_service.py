"""
路径优化服务 - Phase 22

整合 route_service 和 nsga2_service，生成帕累托最优路径

主要功能：
1. 整合OSM路网数据和NSGA-II多目标优化
2. 生成2-3条帕累托最优路径
3. 为每条路径提供时间、热量消耗、绿化评分

Phase 22 实现
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from app.services.nsga2_service import NSGA2Service, get_nsga2_service
from app.services.route_service import RouteService, get_route_service

# 配置日志
logger = logging.getLogger(__name__)


class RouteOptimizationService:
    """
    路径优化服务
    
    整合NSGA-II多目标优化和OSM路网数据，生成帕累托最优运动路径
    """
    
    # 路径名称模板
    ROUTE_NAMES = {
        'shortest_time': '最短时间',
        'max_calories': '最大消耗', 
        'best_greenery': '最佳绿化',
        'balanced': '平衡方案'
    }
    
    # 默认参数
    DEFAULT_MAX_TIME = 60  # 默认最大时间60分钟
    DEFAULT_WEIGHT = 70.0  # 默认体重70kg
    DEFAULT_EXERCISE_TYPE = 'walking'  # 默认步行
    DEFAULT_N_ROUTES = 3  # 默认返回3条路径
    
    # 运动速度映射（km/h）
    EXERCISE_SPEEDS = {
        'walking': 5.0,
        'brisk_walking': 6.0,
        'jogging': 7.5,
        'running': 10.0,
        'cycling': 18.0,
        'hiking': 4.0,
    }
    
    def __init__(self):
        """初始化路径优化服务"""
        self.nsga2_service = get_nsga2_service()
        self.route_service = get_route_service()
        
    def generate_pareto_routes(
        self,
        start_point: Tuple[float, float],
        target_calories: float,
        max_time_minutes: int = None,
        exercise_type: str = None,
        weight_kg: float = None,
        n_routes: int = None
    ) -> Dict[str, Any]:
        """
        生成帕累托最优路径
        
        Args:
            start_point: 起点坐标 (lat, lng)
            target_calories: 目标热量消耗（kcal）
            max_time_minutes: 最大运动时间（分钟）
            exercise_type: 运动类型
            weight_kg: 用户体重（kg）
            n_routes: 返回路径数量（2-3条）
            
        Returns:
            包含帕累托最优路径的字典
        """
        # 参数默认值
        max_time_minutes = max_time_minutes or self.DEFAULT_MAX_TIME
        exercise_type = exercise_type or self.DEFAULT_EXERCISE_TYPE
        weight_kg = weight_kg or self.DEFAULT_WEIGHT
        n_routes = min(max(n_routes or self.DEFAULT_N_ROUTES, 2), 3)  # 限制2-3条
        
        logger.info(f"生成帕累托路径: start={start_point}, calories={target_calories}, "
                   f"time={max_time_minutes}min, type={exercise_type}")
        
        try:
            # 使用NSGA-II优化生成候选解
            nsga2_result = self.nsga2_service.optimize(
                start_point=start_point,
                target_calories=target_calories,
                max_time_minutes=max_time_minutes,
                exercise_type=exercise_type,
                weight_kg=weight_kg,
                n_generations=30,  # 减少代数以加快速度
                pop_size=30,
                n_waypoints=4
            )
            
            # 从NSGA-II结果中提取帕累托前沿
            solutions = nsga2_result.get('solutions', [])
            
            if not solutions:
                # 如果优化失败，生成默认路径
                logger.warning("NSGA-II优化未产生结果，使用默认路径生成")
                routes = self._generate_default_routes(
                    start_point, target_calories, max_time_minutes, 
                    exercise_type, weight_kg, n_routes
                )
            else:
                # 从帕累托前沿选择代表性路径
                routes = self._select_representative_routes(
                    solutions, start_point, exercise_type, weight_kg, n_routes
                )
            
            # 构建响应
            return {
                'routes': routes,
                'start_point': {
                    'lat': start_point[0],
                    'lng': start_point[1]
                },
                'target_calories': target_calories,
                'max_time_minutes': max_time_minutes,
                'exercise_type': exercise_type,
                'weight_kg': weight_kg,
                'n_routes': len(routes)
            }
            
        except Exception as e:
            logger.error(f"生成帕累托路径失败: {e}")
            # 返回默认路径
            routes = self._generate_default_routes(
                start_point, target_calories, max_time_minutes,
                exercise_type, weight_kg, n_routes
            )
            return {
                'routes': routes,
                'start_point': {
                    'lat': start_point[0],
                    'lng': start_point[1]
                },
                'target_calories': target_calories,
                'max_time_minutes': max_time_minutes,
                'exercise_type': exercise_type,
                'weight_kg': weight_kg,
                'n_routes': len(routes),
                'warning': str(e)
            }
    
    def _select_representative_routes(
        self,
        solutions: List[Dict[str, Any]],
        start_point: Tuple[float, float],
        exercise_type: str,
        weight_kg: float,
        n_routes: int
    ) -> List[Dict[str, Any]]:
        """
        从帕累托前沿选择代表性路径
        
        选择策略：
        1. 最短时间路径
        2. 最大热量消耗路径
        3. 最佳绿化路径（如果需要3条）
        
        Args:
            solutions: NSGA-II优化结果
            start_point: 起点坐标
            exercise_type: 运动类型
            weight_kg: 体重
            n_routes: 需要的路径数量
            
        Returns:
            选中的代表性路径列表
        """
        if not solutions:
            return []
        
        # 计算每个解的各目标值
        evaluated_solutions = []
        for sol in solutions:
            objectives = sol.get('objectives', {})
            evaluated_solutions.append({
                'solution': sol,
                'time': objectives.get('time_minutes', float('inf')),
                'calories': objectives.get('calories_kcal', 0),
                'greenery': objectives.get('greenery_score', 0)
            })
        
        selected_routes = []
        
        # 1. 选择最短时间路径
        shortest_time = min(evaluated_solutions, key=lambda x: x['time'])
        route1 = self._solution_to_route(
            shortest_time['solution'], 
            route_id=1,
            route_name=self.ROUTE_NAMES['shortest_time'],
            start_point=start_point,
            exercise_type=exercise_type
        )
        selected_routes.append(route1)
        
        # 2. 选择最大热量消耗路径
        max_calories = max(evaluated_solutions, key=lambda x: x['calories'])
        if max_calories != shortest_time:
            route2 = self._solution_to_route(
                max_calories['solution'],
                route_id=2,
                route_name=self.ROUTE_NAMES['max_calories'],
                start_point=start_point,
                exercise_type=exercise_type
            )
            selected_routes.append(route2)
        else:
            # 如果最短时间和最大热量是同一个解，选择次优
            remaining = [s for s in evaluated_solutions if s != shortest_time]
            if remaining:
                next_best = max(remaining, key=lambda x: x['calories'])
                route2 = self._solution_to_route(
                    next_best['solution'],
                    route_id=2,
                    route_name=self.ROUTE_NAMES['max_calories'],
                    start_point=start_point,
                    exercise_type=exercise_type
                )
                selected_routes.append(route2)
        
        # 3. 如果需要3条路径，选择最佳绿化路径
        if n_routes >= 3 and len(evaluated_solutions) > 2:
            already_selected = {id(shortest_time), id(max_calories)}
            remaining = [s for s in evaluated_solutions if id(s) not in already_selected]
            
            if remaining:
                best_greenery = max(remaining, key=lambda x: x['greenery'])
                route3 = self._solution_to_route(
                    best_greenery['solution'],
                    route_id=3,
                    route_name=self.ROUTE_NAMES['best_greenery'],
                    start_point=start_point,
                    exercise_type=exercise_type
                )
                selected_routes.append(route3)
            elif len(evaluated_solutions) > 2:
                # 选择任意第三个
                for s in evaluated_solutions:
                    if id(s) not in already_selected:
                        route3 = self._solution_to_route(
                            s['solution'],
                            route_id=3,
                            route_name=self.ROUTE_NAMES['balanced'],
                            start_point=start_point,
                            exercise_type=exercise_type
                        )
                        selected_routes.append(route3)
                        break
        
        # 确保至少有2条路径
        while len(selected_routes) < 2:
            # 生成一条额外的平衡路径
            route_id = len(selected_routes) + 1
            extra_route = self._generate_single_route(
                start_point, 
                exercise_type,
                weight_kg,
                route_id=route_id,
                route_name=self.ROUTE_NAMES['balanced'],
                variation=len(selected_routes) * 0.1  # 添加一些变化
            )
            selected_routes.append(extra_route)
        
        return selected_routes[:n_routes]
    
    def _solution_to_route(
        self,
        solution: Dict[str, Any],
        route_id: int,
        route_name: str,
        start_point: Tuple[float, float],
        exercise_type: str
    ) -> Dict[str, Any]:
        """
        将NSGA-II解转换为路径格式
        
        Args:
            solution: NSGA-II解
            route_id: 路径ID
            route_name: 路径名称
            start_point: 起点
            exercise_type: 运动类型
            
        Returns:
            路径字典
        """
        objectives = solution.get('objectives', {})
        route_data = solution.get('route', {})
        
        # 提取路径点
        waypoints = route_data.get('waypoints', [])
        waypoints_formatted = []
        
        # 添加起点
        waypoints_formatted.append({
            'lat': start_point[0],
            'lng': start_point[1],
            'order': 0,
            'type': 'start'
        })
        
        # 添加中间点
        for i, wp in enumerate(waypoints):
            if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                waypoints_formatted.append({
                    'lat': wp[0],
                    'lng': wp[1],
                    'order': i + 1,
                    'type': 'waypoint'
                })
        
        # 添加终点（回到起点形成环路）
        waypoints_formatted.append({
            'lat': start_point[0],
            'lng': start_point[1],
            'order': len(waypoints_formatted),
            'type': 'end'
        })
        
        # 计算距离（基于路径点）
        distance_meters = self._calculate_route_distance(waypoints_formatted)
        
        return {
            'route_id': route_id,
            'route_name': route_name,
            'time_minutes': round(objectives.get('time_minutes', 30), 1),
            'calories_burn': round(objectives.get('calories_kcal', 100), 1),
            'greenery_score': round(objectives.get('greenery_score', 50), 1),
            'distance_meters': round(distance_meters, 0),
            'waypoints': waypoints_formatted,
            'exercise_type': exercise_type,
            'intensity': round(solution.get('intensity', 0.5), 2)
        }
    
    def _generate_default_routes(
        self,
        start_point: Tuple[float, float],
        target_calories: float,
        max_time_minutes: int,
        exercise_type: str,
        weight_kg: float,
        n_routes: int
    ) -> List[Dict[str, Any]]:
        """
        生成默认路径（当优化失败时使用）
        
        基于简单的启发式规则生成2-3条差异化路径
        """
        routes = []
        
        # 获取运动速度
        speed_kmh = self.EXERCISE_SPEEDS.get(exercise_type, 5.0)
        
        # METs值（简化）
        mets_table = {
            'walking': 3.5,
            'brisk_walking': 4.3,
            'jogging': 7.0,
            'running': 8.0,
            'cycling': 6.0,
            'hiking': 5.3,
        }
        base_mets = mets_table.get(exercise_type, 3.5)
        
        # 路径1: 最短时间（高强度，短时间）
        intensity1 = 0.9
        time1 = min(max_time_minutes * 0.6, 30)
        calories1 = base_mets * intensity1 * weight_kg * (time1 / 60)
        distance1 = speed_kmh * (1 + intensity1 * 0.3) * (time1 / 60) * 1000
        
        routes.append(self._generate_single_route(
            start_point, exercise_type, weight_kg,
            route_id=1,
            route_name=self.ROUTE_NAMES['shortest_time'],
            time_minutes=time1,
            calories_burn=calories1,
            greenery_score=40,  # 短路径绿化一般
            distance_meters=distance1,
            intensity=intensity1
        ))
        
        # 路径2: 最大消耗（长时间，高强度）
        intensity2 = 0.85
        time2 = min(max_time_minutes * 0.95, max_time_minutes)
        calories2 = base_mets * intensity2 * weight_kg * (time2 / 60)
        distance2 = speed_kmh * (1 + intensity2 * 0.3) * (time2 / 60) * 1000
        
        routes.append(self._generate_single_route(
            start_point, exercise_type, weight_kg,
            route_id=2,
            route_name=self.ROUTE_NAMES['max_calories'],
            time_minutes=time2,
            calories_burn=calories2,
            greenery_score=60,  # 长路径可能经过更多绿地
            distance_meters=distance2,
            intensity=intensity2
        ))
        
        # 路径3: 最佳绿化（适中时间，选择绿化路线）
        if n_routes >= 3:
            intensity3 = 0.7
            time3 = min(max_time_minutes * 0.8, max_time_minutes - 10)
            calories3 = base_mets * intensity3 * weight_kg * (time3 / 60)
            distance3 = speed_kmh * (1 + intensity3 * 0.3) * (time3 / 60) * 1000
            
            routes.append(self._generate_single_route(
                start_point, exercise_type, weight_kg,
                route_id=3,
                route_name=self.ROUTE_NAMES['best_greenery'],
                time_minutes=time3,
                calories_burn=calories3,
                greenery_score=85,  # 优先选择绿化路线
                distance_meters=distance3,
                intensity=intensity3
            ))
        
        return routes
    
    def _generate_single_route(
        self,
        start_point: Tuple[float, float],
        exercise_type: str,
        weight_kg: float,
        route_id: int,
        route_name: str,
        time_minutes: float = None,
        calories_burn: float = None,
        greenery_score: float = None,
        distance_meters: float = None,
        intensity: float = 0.7,
        variation: float = 0
    ) -> Dict[str, Any]:
        """
        生成单条路径
        """
        # 计算默认值
        if time_minutes is None:
            time_minutes = 30 + variation * 10
        if calories_burn is None:
            mets = 3.5 * (1 + intensity * 0.3)
            calories_burn = mets * weight_kg * (time_minutes / 60)
        if greenery_score is None:
            greenery_score = 50 + variation * 20
        if distance_meters is None:
            speed_kmh = self.EXERCISE_SPEEDS.get(exercise_type, 5.0)
            distance_meters = speed_kmh * (time_minutes / 60) * 1000
        
        # 生成路径点（在起点周围生成环路）
        waypoints = self._generate_circular_waypoints(
            start_point, 
            distance_meters,
            n_points=4 + int(variation * 2)
        )
        
        return {
            'route_id': route_id,
            'route_name': route_name,
            'time_minutes': round(time_minutes, 1),
            'calories_burn': round(calories_burn, 1),
            'greenery_score': round(greenery_score, 1),
            'distance_meters': round(distance_meters, 0),
            'waypoints': waypoints,
            'exercise_type': exercise_type,
            'intensity': round(intensity, 2)
        }
    
    def _generate_circular_waypoints(
        self,
        start_point: Tuple[float, float],
        total_distance: float,
        n_points: int = 4
    ) -> List[Dict[str, Any]]:
        """
        生成环形路径点
        
        Args:
            start_point: 起点
            total_distance: 总距离（米）
            n_points: 路径点数量
            
        Returns:
            路径点列表
        """
        waypoints = []
        
        # 计算大致半径（假设是圆形路径）
        # 周长 = 2 * pi * r -> r = 周长 / (2 * pi)
        radius_meters = total_distance / (2 * np.pi)
        
        # 转换为经纬度偏移（1度约111km）
        radius_deg = radius_meters / 111000
        
        # 添加起点
        waypoints.append({
            'lat': start_point[0],
            'lng': start_point[1],
            'order': 0,
            'type': 'start'
        })
        
        # 生成环形路径点
        for i in range(n_points):
            angle = 2 * np.pi * i / n_points
            lat = start_point[0] + radius_deg * np.cos(angle)
            lng = start_point[1] + radius_deg * np.sin(angle) / np.cos(np.radians(start_point[0]))
            
            waypoints.append({
                'lat': round(lat, 6),
                'lng': round(lng, 6),
                'order': i + 1,
                'type': 'waypoint'
            })
        
        # 添加终点（回到起点）
        waypoints.append({
            'lat': start_point[0],
            'lng': start_point[1],
            'order': n_points + 1,
            'type': 'end'
        })
        
        return waypoints
    
    def _calculate_route_distance(
        self,
        waypoints: List[Dict[str, Any]]
    ) -> float:
        """
        计算路径总距离
        
        Args:
            waypoints: 路径点列表
            
        Returns:
            总距离（米）
        """
        if len(waypoints) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(waypoints) - 1):
            lat1, lng1 = waypoints[i]['lat'], waypoints[i]['lng']
            lat2, lng2 = waypoints[i + 1]['lat'], waypoints[i + 1]['lng']
            total_distance += self._haversine_distance(lat1, lng1, lat2, lng2)
        
        return total_distance
    
    def _haversine_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        使用Haversine公式计算两点间距离
        
        Returns:
            距离（米）
        """
        R = 6371000  # 地球半径（米）
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lng = np.radians(lng2 - lng1)
        
        a = (np.sin(delta_lat / 2) ** 2 +
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lng / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c


# 单例实例
_route_optimization_service_instance: Optional[RouteOptimizationService] = None


def get_route_optimization_service() -> RouteOptimizationService:
    """获取路径优化服务单例"""
    global _route_optimization_service_instance
    if _route_optimization_service_instance is None:
        _route_optimization_service_instance = RouteOptimizationService()
    return _route_optimization_service_instance
