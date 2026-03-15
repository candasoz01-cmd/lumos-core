"""
Görev motoru: görev kaydı, adım durumları, yürütme mantığı.
KandoLumos kısıtlı otonom çalışma omurgası.

Core observation layer: Task, TaskPriority, TaskQueue, ObservationTaskEngine
(signals from system_monitor → triggers → Task → TaskQueue). Device layer:
DeviceTaskEngine extends ObservationTaskEngine with device_guard / device_action_policy.
"""
from task_engine.models import Task, TaskPriority
from task_engine.queue import TaskQueue
from task_engine.observation_engine import ObservationTaskEngine
from task_engine.engine import (
    TaskRecord,
    TaskStep,
    TaskStore,
    TaskEngine,
    STEP_PENDING,
    STEP_RUNNING,
    STEP_COMPLETED,
    STEP_ERROR,
    STEP_STOPPED,
    STEP_RESULT_VERIFIED,
    STEP_RESULT_PARTIAL,
    STEP_RESULT_SIMULATION,
    STEP_RESULT_UNVERIFIABLE,
    STEP_RESULT_ERROR,
    TASK_PENDING,
    TASK_RUNNING,
    TASK_COMPLETED,
    TASK_PARTIAL,
    TASK_DOGRULANAMADI,
    TASK_ERROR,
    TASK_STOPPED,
    TASK_SIMULATION,
    compute_task_stats,
    format_task_stats_line,
    find_recent_similar_task,
)
from task_engine.profiles import (
    PROFILE_RAPOR,
    PROFILE_GUVENLI_YURUT,
    PROFILE_KISITLI_OTONOM,
    ALL_PROFILES,
    get_profile_display_name,
    SECURITY_BOUNDARY_DESCRIPTION,
)
from task_engine.device_tasks import DeviceTaskEngine

# Backward compatibility: DeviceTask is the same as Task.
DeviceTask = Task

__all__ = [
    "Task",
    "TaskPriority",
    "TaskQueue",
    "ObservationTaskEngine",
    "TaskRecord",
    "TaskStep",
    "TaskStore",
    "TaskEngine",
    "STEP_PENDING",
    "STEP_RUNNING",
    "STEP_COMPLETED",
    "STEP_ERROR",
    "STEP_STOPPED",
    "STEP_RESULT_VERIFIED",
    "STEP_RESULT_PARTIAL",
    "STEP_RESULT_SIMULATION",
    "STEP_RESULT_UNVERIFIABLE",
    "STEP_RESULT_ERROR",
    "TASK_PENDING",
    "TASK_RUNNING",
    "TASK_COMPLETED",
    "TASK_PARTIAL",
    "TASK_DOGRULANAMADI",
    "TASK_ERROR",
    "TASK_STOPPED",
    "TASK_SIMULATION",
    "compute_task_stats",
    "format_task_stats_line",
    "find_recent_similar_task",
    "PROFILE_RAPOR",
    "PROFILE_GUVENLI_YURUT",
    "PROFILE_KISITLI_OTONOM",
    "ALL_PROFILES",
    "get_profile_display_name",
    "SECURITY_BOUNDARY_DESCRIPTION",
    "DeviceTask",
    "DeviceTaskEngine",
]
