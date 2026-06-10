from langgraph.checkpoint.memory import MemorySaver

from core.checkpointer import get_checkpointer, reset_checkpointer


def setup_function():
    reset_checkpointer()


def test_returns_memory_saver():
    cp = get_checkpointer()
    assert isinstance(cp, MemorySaver)


def test_singleton():
    cp1 = get_checkpointer()
    cp2 = get_checkpointer()
    assert cp1 is cp2


def test_reset_creates_new():
    cp1 = get_checkpointer()
    reset_checkpointer()
    cp2 = get_checkpointer()
    assert cp1 is not cp2
