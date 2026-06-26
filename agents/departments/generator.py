import os
from pathlib import Path


TEMPLATE_FILES = {
    "__init__.py": """from .graph import Graph\nfrom .proposer import Proposer\nfrom .worker import Worker\nfrom .critic import Critic\n\n# Register module-level helpers here if needed\n""",
    "graph.py": """class Graph:\n    \"\"\"Department graph stub for new departments.\n\"\"\"\n\n    def __init__(self):\n        self.name = "<name>"\n\n    def routes(self):\n        return []\n""",
    "proposer.py": """class Proposer:\n    name = "<name>.proposer"\n\n    async def run(self, state):\n        return {"draft": f\"Proposal for: {state.get('request')}\"}\n""",
    "worker.py": """class Worker:\n    name = "<name>.worker"\n\n    async def run(self, state):\n        return {"result": f\"Work result for: {state.get('request')}\"}\n""",
    "critic.py": """class Critic:\n    name = "<name>.critic"\n\n    async def run(self, state):\n        return {"critique": {"reason": "Looks good"}}\n""",
}


def create_department(name: str, base_path: str | Path = None) -> Path:
    """Create a new department scaffold under `agents/departments/<name>`.

    Returns the Path to the created department directory.
    """
    if base_path is None:
        base_path = Path(__file__).resolve().parent
    else:
        base_path = Path(base_path)

    dept_dir = base_path / name
    dept_dir.mkdir(parents=True, exist_ok=True)

    for fname, tpl in TEMPLATE_FILES.items():
        content = tpl.replace("<name>", name)
        file_path = dept_dir / fname
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")

    # touch __pycache__ via import safety
    (dept_dir / "__pycache__").mkdir(exist_ok=True)

    return dept_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a new department scaffold")
    parser.add_argument("name", help="department name (snake_case)")
    parser.add_argument("--base", help="base path for departments", default=None)
    args = parser.parse_args()

    out = create_department(args.name, base_path=args.base)
    print(f"Created department at: {out}")
