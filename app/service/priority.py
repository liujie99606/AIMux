from __future__ import annotations

PRIORITY_MIN: int = 0
PRIORITY_MAX: int = 9
MONITOR_PRIORITY_MAX: int = 6
DEFAULT_PRIORITY: int = 5


def after_test_success(priority: int) -> int:
    """测试成功后最多提升到 9。"""
    return min(PRIORITY_MAX, priority + 3)


def after_test_failure(priority: int) -> int:
    """测试失败后降一级，最低保留为 0。"""
    return max(PRIORITY_MIN, priority - 1)


def after_request_failure(priority: int) -> int:
    """真实请求失败后降一级，最低保留为 0。"""
    return max(PRIORITY_MIN, priority - 1)


def after_request_success(priority: int) -> int:
    """真实请求成功后提升一级，最高限制为 9。"""
    return min(PRIORITY_MAX, priority + 1)


def after_monitor_success(priority: int) -> int:
    """监控成功后提升一级，最高限制为 6。"""
    return min(MONITOR_PRIORITY_MAX, priority + 1)


def after_monitor_failure(priority: int) -> int:
    """监控失败后降低一级，最低保留为 0。"""
    return max(PRIORITY_MIN, priority - 1)


def super_priority() -> int:
    """返回超级优先对应的固定最高优先级。"""
    return PRIORITY_MAX
