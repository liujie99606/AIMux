PRIORITY_MIN = 0
PRIORITY_MAX = 9
DEFAULT_PRIORITY = 5


def after_test_success(priority: int) -> int:
    """测试成功后最多提升到 9。"""
    return min(PRIORITY_MAX, priority + 3)


def after_test_failure(priority: int) -> int:
    """测试失败后降一级，最低保留为 0。"""
    return max(PRIORITY_MIN, priority - 1)


def after_request_failure(priority: int) -> int:
    """真实请求失败后降一级，最低保留为 0。"""
    return max(PRIORITY_MIN, priority - 1)


def super_priority() -> int:
    """返回超级优先对应的固定最高优先级。"""
    return PRIORITY_MAX
