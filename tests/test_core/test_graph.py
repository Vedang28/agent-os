from core.graph import build_graph


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_graph_runs_end_to_end():
    graph = build_graph()
    result = graph.invoke({"request": "test"})
    assert result["approved"] is True
    assert result["request"] == "test"
