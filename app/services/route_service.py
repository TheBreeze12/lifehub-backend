"""
OSM路网数据处理服务

使用osmnx和networkx处理OpenStreetMap路网数据，为运动路径规划提供基础设施

主要功能：
1. 根据经纬度获取周边路网
2. 构建可遍历的图结构
3. 路径查找（最短路径）
4. 路网属性提取

Phase 21 实现
"""

import os
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入osmnx和networkx
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    logger.warning("osmnx或networkx未安装，路网功能将受限")


class RouteService:
    """
    OSM路网数据处理服务
    
    提供基于OpenStreetMap的路网数据获取、图构建和路径查找功能
    """
    
    # 默认配置
    DEFAULT_DISTANCE = 500  # 默认搜索范围（米）
    DEFAULT_NETWORK_TYPE = 'walk'  # 默认网络类型（步行）
    
    # 支持的网络类型
    NETWORK_TYPES = ['walk', 'bike', 'drive', 'all']
    
    # 不同运动模式的速度（km/h）
    TRAVEL_SPEEDS = {
        'walk': 5.0,      # 步行速度
        'bike': 15.0,     # 骑行速度
        'run': 8.0,       # 跑步速度
        'drive': 40.0,    # 驾车速度
    }
    
    def __init__(self):
        """初始化路网服务"""
        self._cache: Dict[str, Any] = {}
        self._cache_enabled = True
        
        # 配置osmnx（如果可用）
        if OSMNX_AVAILABLE:
            # 设置osmnx配置
            ox.settings.use_cache = True
            ox.settings.log_console = False
            ox.settings.timeout = 30
            
    def _generate_cache_key(
        self,
        center_point: Tuple[float, float],
        distance: int,
        network_type: str
    ) -> str:
        """
        生成缓存键
        
        Args:
            center_point: 中心点坐标 (lat, lng)
            distance: 搜索范围（米）
            network_type: 网络类型
            
        Returns:
            缓存键字符串
        """
        key_str = f"{center_point[0]:.4f}_{center_point[1]:.4f}_{distance}_{network_type}"
        return hashlib.md5(key_str.encode()).hexdigest()
        
    def _validate_coordinates(self, lat: float, lng: float) -> bool:
        """
        验证坐标有效性
        
        Args:
            lat: 纬度
            lng: 经度
            
        Returns:
            坐标是否有效
        """
        return -90 <= lat <= 90 and -180 <= lng <= 180
        
    def get_road_network(
        self,
        center_point: Tuple[float, float],
        distance: int = None,
        network_type: str = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取指定位置周边的路网数据
        
        Args:
            center_point: 中心点坐标 (lat, lng)
            distance: 搜索范围（米），默认500米
            network_type: 网络类型 (walk/bike/drive/all)，默认walk
            use_cache: 是否使用缓存
            
        Returns:
            包含图结构和统计信息的字典
        """
        if not OSMNX_AVAILABLE:
            return {
                'error': 'osmnx库未安装',
                'graph': None,
                'nodes_count': 0,
                'edges_count': 0
            }
            
        # 参数默认值
        distance = distance or self.DEFAULT_DISTANCE
        network_type = network_type or self.DEFAULT_NETWORK_TYPE
        
        # 验证坐标
        lat, lng = center_point
        if not self._validate_coordinates(lat, lng):
            return {
                'error': f'无效的坐标: lat={lat}, lng={lng}',
                'graph': None,
                'nodes_count': 0,
                'edges_count': 0
            }
            
        # 验证网络类型
        if network_type not in self.NETWORK_TYPES:
            network_type = self.DEFAULT_NETWORK_TYPE
            
        # 检查缓存
        cache_key = self._generate_cache_key(center_point, distance, network_type)
        if use_cache and self._cache_enabled and cache_key in self._cache:
            logger.debug(f"使用缓存的路网数据: {cache_key}")
            return self._cache[cache_key]
            
        try:
            # 使用osmnx获取路网
            logger.info(f"获取路网数据: center={center_point}, distance={distance}, type={network_type}")
            
            graph = ox.graph_from_point(
                center_point,
                dist=distance,
                network_type=network_type,
                simplify=True
            )
            
            # 为边添加长度属性（如果没有的话）
            graph = ox.distance.add_edge_lengths(graph)
            
            # 构建结果
            result = {
                'graph': graph,
                'nodes_count': graph.number_of_nodes(),
                'edges_count': graph.number_of_edges(),
                'center_point': center_point,
                'distance': distance,
                'network_type': network_type,
                'error': None
            }
            
            # 存入缓存
            if use_cache and self._cache_enabled:
                self._cache[cache_key] = result
                
            return result
            
        except Exception as e:
            logger.error(f"获取路网失败: {e}")
            return {
                'error': str(e),
                'graph': nx.MultiDiGraph() if OSMNX_AVAILABLE else None,
                'nodes_count': 0,
                'edges_count': 0,
                'center_point': center_point,
                'distance': distance,
                'network_type': network_type
            }
            
    def build_graph(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Any:
        """
        从节点和边列表构建图
        
        Args:
            nodes: 节点列表，每个节点包含id, lat, lng
            edges: 边列表，每条边包含source, target, length
            
        Returns:
            networkx图对象
        """
        if not OSMNX_AVAILABLE:
            return None
            
        graph = nx.MultiDiGraph()
        
        # 添加节点
        for node in nodes:
            node_id = node.get('id')
            graph.add_node(
                node_id,
                y=node.get('lat'),
                x=node.get('lng'),
                **{k: v for k, v in node.items() if k not in ['id', 'lat', 'lng']}
            )
            
        # 添加边
        for edge in edges:
            graph.add_edge(
                edge.get('source'),
                edge.get('target'),
                length=edge.get('length', 0),
                **{k: v for k, v in edge.items() if k not in ['source', 'target', 'length']}
            )
            
        return graph
        
    def find_nearest_node(
        self,
        graph: Any,
        point: Tuple[float, float]
    ) -> Dict[str, Any]:
        """
        查找距离给定点最近的节点
        
        Args:
            graph: networkx图对象
            point: 坐标点 (lat, lng)
            
        Returns:
            包含node_id和distance的字典
        """
        if not OSMNX_AVAILABLE or graph is None:
            return {'node_id': None, 'distance': float('inf'), 'error': '图不可用'}
            
        if graph.number_of_nodes() == 0:
            return {'node_id': None, 'distance': float('inf'), 'error': '图中无节点'}
            
        try:
            lat, lng = point
            
            # 使用osmnx的最近节点查找
            nearest_node = ox.distance.nearest_nodes(graph, lng, lat)
            
            # 计算距离
            node_data = graph.nodes[nearest_node]
            node_lat = node_data.get('y', 0)
            node_lng = node_data.get('x', 0)
            
            # 使用简化的距离计算（米）
            distance = self._haversine_distance(lat, lng, node_lat, node_lng)
            
            return {
                'node_id': nearest_node,
                'distance': distance,
                'lat': node_lat,
                'lng': node_lng,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"查找最近节点失败: {e}")
            return {'node_id': None, 'distance': float('inf'), 'error': str(e)}
            
    def find_shortest_path(
        self,
        graph: Any,
        start_node: Any,
        end_node: Any,
        weight: str = 'length'
    ) -> Dict[str, Any]:
        """
        查找两个节点之间的最短路径
        
        Args:
            graph: networkx图对象
            start_node: 起始节点ID
            end_node: 结束节点ID
            weight: 权重属性名
            
        Returns:
            包含路径和长度的字典
        """
        if not OSMNX_AVAILABLE or graph is None:
            return {'found': False, 'path': [], 'total_length': 0, 'error': '图不可用'}
            
        # 检查节点是否存在
        if start_node not in graph.nodes or end_node not in graph.nodes:
            return {
                'found': False,
                'path': [],
                'total_length': 0,
                'error': '起点或终点节点不存在'
            }
            
        try:
            # 使用Dijkstra算法查找最短路径
            path = nx.shortest_path(graph, start_node, end_node, weight=weight)
            
            # 计算路径总长度
            total_length = self.calculate_path_length(graph, path)
            
            # 获取路径坐标
            path_coords = []
            for node in path:
                node_data = graph.nodes[node]
                path_coords.append({
                    'node_id': node,
                    'lat': node_data.get('y'),
                    'lng': node_data.get('x')
                })
                
            return {
                'found': True,
                'path': path,
                'path_coords': path_coords,
                'total_length': total_length,
                'nodes_count': len(path),
                'error': None
            }
            
        except nx.NetworkXNoPath:
            return {
                'found': False,
                'path': [],
                'total_length': 0,
                'error': '两点之间无可达路径'
            }
        except Exception as e:
            logger.error(f"查找最短路径失败: {e}")
            return {
                'found': False,
                'path': [],
                'total_length': 0,
                'error': str(e)
            }
            
    def find_shortest_path_by_coords(
        self,
        graph: Any,
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        weight: str = 'length'
    ) -> Dict[str, Any]:
        """
        通过坐标查找最短路径
        
        Args:
            graph: networkx图对象
            start_point: 起点坐标 (lat, lng)
            end_point: 终点坐标 (lat, lng)
            weight: 权重属性名
            
        Returns:
            包含路径和长度的字典
        """
        # 查找最近节点
        start_nearest = self.find_nearest_node(graph, start_point)
        end_nearest = self.find_nearest_node(graph, end_point)
        
        if start_nearest.get('error') or end_nearest.get('error'):
            return {
                'found': False,
                'path': [],
                'total_length': 0,
                'error': start_nearest.get('error') or end_nearest.get('error')
            }
            
        # 查找路径
        result = self.find_shortest_path(
            graph,
            start_nearest['node_id'],
            end_nearest['node_id'],
            weight
        )
        
        # 添加起终点信息
        result['start_point'] = start_point
        result['end_point'] = end_point
        result['start_node_distance'] = start_nearest['distance']
        result['end_node_distance'] = end_nearest['distance']
        
        return result
        
    def get_edge_length(
        self,
        graph: Any,
        node1: Any,
        node2: Any
    ) -> float:
        """
        获取两个节点之间边的长度
        
        Args:
            graph: networkx图对象
            node1: 节点1 ID
            node2: 节点2 ID
            
        Returns:
            边长度（米）
        """
        if not OSMNX_AVAILABLE or graph is None:
            return 0.0
            
        try:
            # MultiDiGraph可能有多条边
            if graph.has_edge(node1, node2):
                edge_data = graph.get_edge_data(node1, node2)
                if edge_data:
                    # 取第一条边的长度
                    if isinstance(edge_data, dict) and 0 in edge_data:
                        return edge_data[0].get('length', 0)
                    return edge_data.get('length', 0)
            return 0.0
        except Exception:
            return 0.0
            
    def calculate_path_length(
        self,
        graph: Any,
        path: List[Any]
    ) -> float:
        """
        计算路径总长度
        
        Args:
            graph: networkx图对象
            path: 节点ID列表
            
        Returns:
            路径总长度（米）
        """
        if not path or len(path) < 2:
            return 0.0
            
        total_length = 0.0
        for i in range(len(path) - 1):
            total_length += self.get_edge_length(graph, path[i], path[i + 1])
            
        return total_length
        
    def estimate_travel_time(
        self,
        distance_meters: float,
        mode: str = 'walk'
    ) -> float:
        """
        估算旅行时间
        
        Args:
            distance_meters: 距离（米）
            mode: 出行方式 (walk/bike/run/drive)
            
        Returns:
            预计时间（分钟）
        """
        speed_kmh = self.TRAVEL_SPEEDS.get(mode, self.TRAVEL_SPEEDS['walk'])
        
        # 转换为分钟
        distance_km = distance_meters / 1000.0
        time_hours = distance_km / speed_kmh
        time_minutes = time_hours * 60
        
        return round(time_minutes, 1)
        
    def get_graph_stats(self, graph: Any) -> Dict[str, Any]:
        """
        获取图的统计信息
        
        Args:
            graph: networkx图对象
            
        Returns:
            统计信息字典
        """
        if not OSMNX_AVAILABLE or graph is None:
            return {
                'nodes_count': 0,
                'edges_count': 0,
                'total_length_km': 0,
                'error': '图不可用'
            }
            
        nodes_count = graph.number_of_nodes()
        edges_count = graph.number_of_edges()
        
        # 计算总长度
        total_length = 0.0
        for u, v, data in graph.edges(data=True):
            total_length += data.get('length', 0)
            
        return {
            'nodes_count': nodes_count,
            'edges_count': edges_count,
            'total_length_km': round(total_length / 1000, 2),
            'total_length_m': round(total_length, 1)
        }
        
    def get_nodes_as_waypoints(
        self,
        graph: Any,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取图中的节点作为可能的路径点
        
        Args:
            graph: networkx图对象
            limit: 最大返回数量
            
        Returns:
            路径点列表
        """
        if not OSMNX_AVAILABLE or graph is None:
            return []
            
        waypoints = []
        for i, (node_id, data) in enumerate(graph.nodes(data=True)):
            if i >= limit:
                break
                
            waypoints.append({
                'node_id': node_id,
                'lat': data.get('y'),
                'lng': data.get('x'),
                'street_count': data.get('street_count', 0)
            })
            
        return waypoints
        
    def _haversine_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        使用Haversine公式计算两点间距离
        
        Args:
            lat1, lng1: 点1坐标
            lat2, lng2: 点2坐标
            
        Returns:
            距离（米）
        """
        import math
        
        R = 6371000  # 地球半径（米）
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
        
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        logger.info("路网缓存已清除")


# 单例实例
_route_service_instance: Optional[RouteService] = None


def get_route_service() -> RouteService:
    """获取路网服务单例"""
    global _route_service_instance
    if _route_service_instance is None:
        _route_service_instance = RouteService()
    return _route_service_instance
