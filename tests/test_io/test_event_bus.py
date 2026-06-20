import asyncio

import pytest

from io_layer.event_bus import (
    DEPARTMENT_ACTIVE,
    TASK_COMPLETE,
    AgentEvent,
    EventBus,
    get_event_bus,
    publish_event,
    reset_event_bus,
)


@pytest.fixture(autouse=True)
def _clean_bus():
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber():
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe(handler)
    event = AgentEvent(type="test", timestamp="t1", data={"key": "value"})
    await bus.publish(event)

    assert len(received) == 1
    assert received[0].type == "test"
    assert received[0].data == {"key": "value"}


@pytest.mark.asyncio
async def test_multiple_subscribers():
    bus = EventBus()
    r1, r2 = [], []

    async def h1(event: AgentEvent):
        r1.append(event)

    async def h2(event: AgentEvent):
        r2.append(event)

    bus.subscribe(h1)
    bus.subscribe(h2)

    event = AgentEvent(type="multi", timestamp="t1", data={})
    await bus.publish(event)

    assert len(r1) == 1
    assert len(r2) == 1


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe(handler)
    bus.unsubscribe(handler)

    event = AgentEvent(type="gone", timestamp="t1", data={})
    await bus.publish(event)

    assert len(received) == 0


@pytest.mark.asyncio
async def test_publish_without_subscribers():
    bus = EventBus()
    event = AgentEvent(type="orphan", timestamp="t1", data={})
    await bus.publish(event)


@pytest.mark.asyncio
async def test_bad_subscriber_does_not_break_bus():
    bus = EventBus()
    good_received = []

    async def bad_handler(event: AgentEvent):
        raise RuntimeError("boom")

    async def good_handler(event: AgentEvent):
        good_received.append(event)

    bus.subscribe(bad_handler)
    bus.subscribe(good_handler)

    event = AgentEvent(type="resilient", timestamp="t1", data={})
    await bus.publish(event)

    assert len(good_received) == 1


@pytest.mark.asyncio
async def test_publish_event_convenience():
    received = []
    bus = get_event_bus()

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe(handler)
    await publish_event(DEPARTMENT_ACTIVE, department="engineering")

    assert len(received) == 1
    assert received[0].type == DEPARTMENT_ACTIVE
    assert received[0].data["department"] == "engineering"
    assert received[0].timestamp


@pytest.mark.asyncio
async def test_event_type_constants():
    assert DEPARTMENT_ACTIVE == "department_active"
    assert TASK_COMPLETE == "task_complete"


@pytest.mark.asyncio
async def test_get_event_bus_singleton():
    b1 = get_event_bus()
    b2 = get_event_bus()
    assert b1 is b2
