"""
ResearchGraph 单元测试

重点：
  1. add_node/add_edge 基本功能
  2. 无环校验 (环检测)
  3. 端口类型匹配校验
  4. 拓扑排序正确性
  5. 同层并行分组 (execution_plan)
  6. 指纹稳定性
  7. DAG View 可视化
"""
from __future__ import annotations

import pytest

from quantlab.research import (
    Edge,
    GraphError,
    ResearchGraph,
)
from quantlab.research.builtin import (
    Alpha014Node,
    CloseNode,
    HighNode,
    LowNode,
    ReturnNode,
    RSINode,
)


class TestGraphConstruction:
    def test_add_node(self):
        g = ResearchGraph(name="t1")
        g.add_node(CloseNode())
        assert len(g.nodes()) == 1
        assert "close" in g.node_ids()

    def test_duplicate_node_raises(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        with pytest.raises(GraphError, match="duplicate"):
            g.add_node(CloseNode())

    def test_add_edge(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_edge("close", "close", "return", "close")
        assert len(g.edges()) == 1

    def test_edge_unknown_source_raises(self):
        g = ResearchGraph()
        g.add_node(ReturnNode())
        with pytest.raises(GraphError, match="source node not found"):
            g.add_edge("ghost", "close", "return", "close")


class TestCycleDetection:
    def test_self_loop_raises(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_edge("close", "close", "close", "frame")  # self-loop
        with pytest.raises(GraphError, match="cycle"):
            g.compile()

    def test_two_node_cycle_raises(self):
        g = ResearchGraph()
        # 借用两个有相同端口的节点制造环
        g.add_node(CloseNode())
        g.add_node(HighNode())
        g.add_edge("close", "close", "high", "frame")
        g.add_edge("high", "high", "close", "frame")
        with pytest.raises(GraphError, match="cycle"):
            g.compile()


class TestPortTypeCheck:
    def test_type_mismatch_raises(self):
        """目前 builtin 节点所有端口都是 FRAME 类型，类型匹配通过。
        这里测试 port 找不到的情况。"""
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode())
        # 错误端口名
        with pytest.raises(GraphError, match="port"):
            g.add_edge("close", "nonexistent", "return", "close")
            g.compile()

    def test_unknown_input_port_raises(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode())
        g.add_edge("close", "close", "return", "ghost_port")
        with pytest.raises(GraphError, match="input port"):
            g.compile()


class TestTopoSort:
    def test_linear_chain(self):
        """close -> return -> rsi 的线性链。"""
        g = ResearchGraph(name="chain")
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        # RSI 需要 close 输入，可消费 return 输出吗？不能，因为 return 输出名是 "return"
        # 实际：close -> return (close 端口)
        g.add_edge("close", "close", "return", "close")
        compiled = g.compile()
        assert compiled.topo_order == ["close", "return"]
        assert compiled.node_count == 2
        assert compiled.edge_count == 1

    def test_parallel_layers(self):
        """close 和 high 两个独立 DataNode 应在同一层。"""
        g = ResearchGraph(name="parallel")
        g.add_node(CloseNode())
        g.add_node(HighNode())
        compiled = g.compile()
        # 两个独立节点应分到同一层
        assert len(compiled.execution_plan) == 1
        assert set(compiled.execution_plan[0]) == {"close", "high"}

    def test_sequential_layers(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode())
        g.add_edge("close", "close", "return", "close")
        compiled = g.compile()
        assert len(compiled.execution_plan) == 2
        assert compiled.execution_plan[0] == ["close"]
        assert compiled.execution_plan[1] == ["return"]


class TestFingerprint:
    def test_stability(self):
        g1 = ResearchGraph().add_node(CloseNode()).add_node(ReturnNode(period=1))
        g1.add_edge("close", "close", "return", "close")
        g2 = ResearchGraph().add_node(CloseNode()).add_node(ReturnNode(period=1))
        g2.add_edge("close", "close", "return", "close")
        assert g1.fingerprint() == g2.fingerprint()

    def test_differs_by_params(self):
        g1 = ResearchGraph().add_node(ReturnNode(period=1))
        g2 = ResearchGraph().add_node(ReturnNode(period=5))
        assert g1.fingerprint() != g2.fingerprint()


class TestDAGView:
    def test_to_dag_view(self):
        g = ResearchGraph(name="v1")
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_edge("close", "close", "return", "close")
        view = g.to_dag_view()
        assert len(view.nodes) == 2
        assert len(view.edges) == 1
        assert len(view.layers) == 2
        assert view.layers[0] == ["close"]
        assert view.layers[1] == ["return"]
        # 节点 dict 包含基本信息
        node_ids = [n["id"] for n in view.nodes]
        assert "close" in node_ids
        assert "return" in node_ids


class TestAlpha014Graph:
    """Alpha014 直接消费 frame，不需多步链。"""

    def test_compile(self):
        g = ResearchGraph(name="alpha014")
        g.add_node(Alpha014Node())
        compiled = g.compile()
        assert compiled.topo_order == ["alpha014"]
        assert len(compiled.execution_plan) == 1
