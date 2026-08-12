from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

_ACTIVE_TASKS: set[object] = set()


class _TaskSignals(QObject):
    """在线程任务与所属页面之间传递结果。"""

    succeeded = Signal(int, object)
    failed = Signal(int, object)
    finished = Signal(object)


class _Task(QRunnable):
    """在线程池中执行一个无 UI 副作用的查询函数。"""

    def __init__(self, request_id: int, query: Callable[[], Any]) -> None:
        super().__init__()
        self.request_id = request_id
        self.query = query
        self.signals = _TaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.succeeded.emit(self.request_id, self.query())
        except Exception as exc:
            self.signals.failed.emit(self.request_id, exc)
        finally:
            self.signals.finished.emit(self)


class _TaskRegistry(QObject):
    """在主线程收到最终信号后释放已结束任务。"""

    @Slot(object)
    def release(self, task: object) -> None:
        _ACTIVE_TASKS.discard(task)


_TASK_REGISTRY = _TaskRegistry()


class BackgroundLoader(QObject):
    """异步执行页面查询，只转发最新一次请求的结果。"""

    loaded = Signal(object)
    failed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._latest_request_id = 0

    def load(self, query: Callable[[], Any]) -> None:
        """将查询提交到全局线程池，旧请求结果自动丢弃。"""
        self._latest_request_id += 1
        task = _Task(self._latest_request_id, query)
        task.signals.succeeded.connect(self._on_succeeded)
        task.signals.failed.connect(self._on_failed)
        task.signals.finished.connect(_TASK_REGISTRY.release)
        _ACTIVE_TASKS.add(task)
        QThreadPool.globalInstance().start(task)

    @Slot(int, object)
    def _on_succeeded(self, request_id: int, result: object) -> None:
        if request_id == self._latest_request_id:
            self.loaded.emit(result)

    @Slot(int, object)
    def _on_failed(self, request_id: int, error: object) -> None:
        if request_id == self._latest_request_id:
            self.failed.emit(error)
