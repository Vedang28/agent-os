from langgraph.graph import END, START, StateGraph

from core.state import AgentState


def pass_through(state: AgentState) -> dict:
    return {"approved": True}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("pass_through", pass_through)
    graph.add_edge(START, "pass_through")
    graph.add_edge("pass_through", END)
    return graph.compile()


if __name__ == "__main__":
    compiled = build_graph()
    result = compiled.invoke({"request": "hello"})
    print(result)
