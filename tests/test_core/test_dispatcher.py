from core.dispatcher import assign_lane


def test_instant_hello():
    result = assign_lane({"request": "hello"})
    assert result["lane"] == "instant"


def test_instant_hi():
    result = assign_lane({"request": "hi"})
    assert result["lane"] == "instant"


def test_instant_hey_there():
    result = assign_lane({"request": "hey there"})
    assert result["lane"] == "instant"


def test_instant_what_time():
    result = assign_lane({"request": "what time is it"})
    assert result["lane"] == "instant"


def test_deep_build_api():
    result = assign_lane({"request": "build a REST API for user management"})
    assert result["lane"] == "deep"


def test_deep_design_architecture():
    result = assign_lane({"request": "design the authentication architecture"})
    assert result["lane"] == "deep"


def test_deep_long_request():
    result = assign_lane({"request": " ".join(["word"] * 20)})
    assert result["lane"] == "deep"


def test_fast_default():
    result = assign_lane({"request": "what is the capital of France"})
    assert result["lane"] == "fast"


def test_empty_request():
    result = assign_lane({"request": ""})
    assert result["lane"] in ("instant", "fast", "deep")


def test_missing_request():
    result = assign_lane({})
    assert result["lane"] in ("instant", "fast", "deep")
