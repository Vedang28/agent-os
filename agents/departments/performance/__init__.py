from agents.departments.performance.graph import build_performance_graph
from agents.departments.performance.perf_optimizer import PerfOptimizer
from agents.departments.performance.perf_profiler import PerfProfiler
from agents.departments.performance.perf_validator import PerfValidator
from agents.registry import list_agents, register

_AGENTS = {
    "performance.perf_profiler": PerfProfiler,
    "performance.perf_optimizer": PerfOptimizer,
    "performance.perf_validator": PerfValidator,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "PerfProfiler",
    "PerfOptimizer",
    "PerfValidator",
    "build_performance_graph",
]
