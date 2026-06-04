from core.state import AgentState


def test_agent_state_empty():
    state = AgentState()
    assert isinstance(state, dict)
    assert len(state) == 0


def test_agent_state_with_fields():
    state = AgentState(request="hello", approved=False, revisions=0)
    assert state["request"] == "hello"
    assert state["approved"] is False
    assert state["revisions"] == 0


def test_agent_state_partial():
    state = AgentState(request="test")
    assert "request" in state
    assert "lane" not in state
    assert "approved" not in state
