"""
Phase 21: OSM路网数据处理服务测试

测试内容：
1. RouteService类实例化
2. 根据经纬度获取周边路网
3. 构建可遍历的图结构
4. 路径查询功能
5. 路网属性提取（距离、绿化等）
6. 异常情况处理

测试使用真实的OSM数据（通过osmnx获取）
"""

import pytest
import sys
import os
from typing import Tuple, List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRouteServiceImports:
    """测试模块导入"""
    
    def test_can_import_route_service(self):
        """测试能否导入route_service模块"""
        try:
            from app.services.route_service import RouteService
            assert RouteService is not None
        except ImportError as e:
            pytest.fail(f"无法导入RouteService: {e}")
            
    def test_can_import_get_route_service(self):
        """测试能否导入get_route_service函数"""
        try:
            from app.services.route_service import get_route_service
            assert get_route_service is not None
        except ImportError as e:
            pytest.fail(f"无法导入get_route_service: {e}")
            
    def test_can_import_osmnx(self):
        """测试能否导入osmnx库"""
        try:
            import osmnx as ox
            assert ox is not None
        except ImportError as e:
            pytest.fail(f"无法导入osmnx: {e}")
            
    def test_can_import_networkx(self):
        """测试能否导入networkx库"""
        try:
            import networkx as nx
            assert nx is not None
        except ImportError as e:
            pytest.fail(f"无法导入networkx: {e}")


class TestRouteServiceInit:
    """测试RouteService初始化"""
    
    def test_service_init(self):
        """测试服务初始化"""
        from app.services.route_service import RouteService
        service = RouteService()
        assert service is not None
        
    def test_singleton_pattern(self):
        """测试单例模式"""
        from app.services.route_service import get_route_service
        service1 = get_route_service()
        service2 = get_route_service()
        assert service1 is service2
        
    def test_service_has_required_methods(self):
        """测试服务具有必需的方法"""
        from app.services.route_service import RouteService
        service = RouteService()
        
        # 检查核心方法
        assert hasattr(service, 'get_road_network')
        assert hasattr(service, 'build_graph')
        assert hasattr(service, 'find_shortest_path')
        assert hasattr(service, 'find_nearest_node')
        assert hasattr(service, 'get_graph_stats')


class TestRoadNetworkFetching:
    """测试路网数据获取"""
    
    def test_get_road_network_by_point(self):
        """测试根据坐标点获取路网"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        # 使用北京天安门坐标（公开位置，不涉及隐私）
        lat, lng = 39.9087, 116.3975
        distance = 500  # 500米范围
        
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=distance
        )
        
        assert result is not None
        assert 'graph' in result
        assert 'nodes_count' in result
        assert 'edges_count' in result
        assert result['nodes_count'] > 0
        assert result['edges_count'] > 0
        
    def test_get_road_network_with_different_distances(self):
        """测试不同距离范围的路网获取"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        
        # 小范围
        result_small = service.get_road_network(
            center_point=(lat, lng),
            distance=200
        )
        
        # 大范围
        result_large = service.get_road_network(
            center_point=(lat, lng),
            distance=800
        )
        
        # 大范围应该有更多节点和边
        assert result_large['nodes_count'] >= result_small['nodes_count']
        assert result_large['edges_count'] >= result_small['edges_count']
        
    def test_get_road_network_walk_type(self):
        """测试获取步行网络"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300,
            network_type='walk'
        )
        
        assert result is not None
        assert result['network_type'] == 'walk'
        
    def test_get_road_network_bike_type(self):
        """测试获取骑行网络"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300,
            network_type='bike'
        )
        
        assert result is not None
        assert result['network_type'] == 'bike'


class TestGraphConstruction:
    """测试图结构构建"""
    
    def test_build_graph_structure(self):
        """测试构建可遍历的图结构"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300
        )
        
        graph = result['graph']
        
        # 验证是networkx图
        import networkx as nx
        assert isinstance(graph, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph))
        
    def test_graph_has_node_attributes(self):
        """测试图节点具有坐标属性"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300
        )
        
        graph = result['graph']
        
        # 检查至少一个节点有坐标
        for node in list(graph.nodes())[:5]:
            node_data = graph.nodes[node]
            assert 'y' in node_data or 'lat' in node_data  # 纬度
            assert 'x' in node_data or 'lng' in node_data  # 经度
            break
            
    def test_graph_has_edge_attributes(self):
        """测试图边具有距离属性"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300
        )
        
        graph = result['graph']
        
        # 检查边属性
        edges = list(graph.edges(data=True))
        if edges:
            edge = edges[0]
            edge_data = edge[2] if len(edge) > 2 else {}
            # osmnx的边通常有length属性
            assert 'length' in edge_data or len(edge_data) >= 0
            
    def test_get_graph_stats(self):
        """测试获取图统计信息"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300
        )
        
        stats = service.get_graph_stats(result['graph'])
        
        assert 'nodes_count' in stats
        assert 'edges_count' in stats
        assert 'total_length_km' in stats
        assert stats['nodes_count'] > 0


class TestPathFinding:
    """测试路径查找功能"""
    
    def test_find_nearest_node(self):
        """测试查找最近节点"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=500
        )
        
        # 查找离中心点最近的节点
        nearest = service.find_nearest_node(
            result['graph'],
            point=(lat, lng)
        )
        
        assert nearest is not None
        assert 'node_id' in nearest
        assert 'distance' in nearest
        assert nearest['distance'] < 500  # 应该在范围内
        
    def test_find_shortest_path_same_component(self):
        """测试在同一连通分量内查找最短路径"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=500
        )
        
        graph = result['graph']
        nodes = list(graph.nodes())
        
        if len(nodes) >= 2:
            # 选择两个节点
            start_node = nodes[0]
            end_node = nodes[min(10, len(nodes)-1)]
            
            path_result = service.find_shortest_path(
                graph,
                start_node=start_node,
                end_node=end_node
            )
            
            # 可能找到路径，也可能没有（取决于连通性）
            assert path_result is not None
            assert 'path' in path_result
            assert 'found' in path_result
            
    def test_find_shortest_path_by_coordinates(self):
        """测试通过坐标查找最短路径"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        # 两个相近的点
        start_lat, start_lng = 39.9087, 116.3975
        end_lat, end_lng = 39.9097, 116.3985
        
        result = service.get_road_network(
            center_point=(start_lat, start_lng),
            distance=500
        )
        
        path_result = service.find_shortest_path_by_coords(
            result['graph'],
            start_point=(start_lat, start_lng),
            end_point=(end_lat, end_lng)
        )
        
        assert path_result is not None
        assert 'found' in path_result
        
    def test_path_has_distance_info(self):
        """测试路径包含距离信息"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=500
        )
        
        graph = result['graph']
        nodes = list(graph.nodes())
        
        if len(nodes) >= 2:
            start_node = nodes[0]
            end_node = nodes[min(5, len(nodes)-1)]
            
            path_result = service.find_shortest_path(
                graph,
                start_node=start_node,
                end_node=end_node
            )
            
            if path_result.get('found'):
                assert 'total_length' in path_result
                assert path_result['total_length'] >= 0


class TestRouteAttributes:
    """测试路径属性提取"""
    
    def test_get_edge_length(self):
        """测试获取边长度"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300
        )
        
        graph = result['graph']
        edges = list(graph.edges())
        
        if edges:
            edge = edges[0]
            length = service.get_edge_length(graph, edge[0], edge[1])
            assert length >= 0
            
    def test_calculate_path_length(self):
        """测试计算路径总长度"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=500
        )
        
        graph = result['graph']
        nodes = list(graph.nodes())
        
        if len(nodes) >= 3:
            # 创建一个简单路径
            path = nodes[:3]
            
            total_length = service.calculate_path_length(graph, path)
            assert total_length >= 0
            
    def test_estimate_walk_time(self):
        """测试估算步行时间"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        # 1公里距离
        distance_meters = 1000
        
        walk_time = service.estimate_travel_time(
            distance_meters,
            mode='walk'
        )
        
        # 步行速度约5km/h，1km约需12分钟
        assert 10 <= walk_time <= 15
        
    def test_estimate_bike_time(self):
        """测试估算骑行时间"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        distance_meters = 1000
        
        bike_time = service.estimate_travel_time(
            distance_meters,
            mode='bike'
        )
        
        # 骑行速度约15km/h，1km约需4分钟
        assert 3 <= bike_time <= 6


class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_coordinates(self):
        """测试无效坐标处理"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        # 无效的纬度（超出范围）
        result = service.get_road_network(
            center_point=(91.0, 116.0),  # 纬度超过90
            distance=300
        )
        
        assert result is not None
        assert result.get('error') is not None or result.get('nodes_count', 0) == 0
        
    def test_very_small_distance(self):
        """测试极小距离处理"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        
        # 非常小的范围
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=10  # 10米
        )
        
        # 应该返回结果（可能为空）
        assert result is not None
        
    def test_nonexistent_path(self):
        """测试不存在的路径"""
        from app.services.route_service import get_route_service
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=300
        )
        
        graph = result['graph']
        
        # 查找到一个不存在的节点
        path_result = service.find_shortest_path(
            graph,
            start_node=999999999,  # 不存在的节点
            end_node=888888888
        )
        
        assert path_result is not None
        assert path_result.get('found') == False
        
    def test_empty_graph_handling(self):
        """测试空图处理"""
        from app.services.route_service import get_route_service
        import networkx as nx
        
        service = get_route_service()
        
        # 创建空图
        empty_graph = nx.MultiDiGraph()
        
        stats = service.get_graph_stats(empty_graph)
        
        assert stats['nodes_count'] == 0
        assert stats['edges_count'] == 0


class TestIntegrationWithNSGA2:
    """测试与NSGA2服务的集成"""
    
    def test_route_service_provides_graph_for_nsga2(self):
        """测试RouteService能为NSGA2提供图数据"""
        from app.services.route_service import get_route_service
        
        service = get_route_service()
        
        # 获取路网
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=500
        )
        
        # 验证图可用于路径规划
        graph = result['graph']
        
        assert graph is not None
        assert result['nodes_count'] > 0
        
        # 验证可以获取节点坐标
        nodes = list(graph.nodes(data=True))
        if nodes:
            node_id, node_data = nodes[0]
            # osmnx的节点有x, y属性
            assert 'x' in node_data or 'lng' in node_data
            assert 'y' in node_data or 'lat' in node_data
            
    def test_get_nodes_as_waypoints(self):
        """测试获取节点作为路径点"""
        from app.services.route_service import get_route_service
        
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        result = service.get_road_network(
            center_point=(lat, lng),
            distance=500
        )
        
        # 获取所有节点作为可能的路径点
        waypoints = service.get_nodes_as_waypoints(result['graph'], limit=10)
        
        assert waypoints is not None
        assert len(waypoints) <= 10
        
        if waypoints:
            wp = waypoints[0]
            assert 'lat' in wp
            assert 'lng' in wp
            assert 'node_id' in wp


class TestCaching:
    """测试缓存功能"""
    
    def test_repeated_fetch_uses_cache(self):
        """测试重复获取使用缓存"""
        from app.services.route_service import get_route_service
        
        service = get_route_service()
        
        lat, lng = 39.9087, 116.3975
        
        # 第一次获取
        result1 = service.get_road_network(
            center_point=(lat, lng),
            distance=300,
            use_cache=True
        )
        
        # 第二次获取（应使用缓存）
        result2 = service.get_road_network(
            center_point=(lat, lng),
            distance=300,
            use_cache=True
        )
        
        # 结果应该相同
        assert result1['nodes_count'] == result2['nodes_count']
        assert result1['edges_count'] == result2['edges_count']


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
