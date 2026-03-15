"""
Dedicated executors for ActionRegistry.
Each module exposes an executor function: (step, task, context) -> (ok, output, error, verified).
"""
from task_engine.executors.analyze_executor import analyze_executor
from task_engine.executors.plan_executor import plan_executor
from task_engine.executors.read_executor import read_executor
from task_engine.executors.safe_local_executor import safe_local_executor

__all__ = [
    "analyze_executor",
    "plan_executor",
    "read_executor",
    "safe_local_executor",
]
