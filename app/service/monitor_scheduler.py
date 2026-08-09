from __future__ import annotations

import asyncio
import logging

from sqlmodel import Session

from app.config import Settings
from app.dao import account_dao
from app.db import get_engine
from app.models import Account
from app.service import monitor_service

_INTERVAL_SECONDS = 120
_MAX_CONCURRENCY = 5
logger = logging.getLogger(__name__)


class MonitorScheduler:
    """负责账号监控轮次、开关唤醒和应用关闭清理。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task[None] | None = None
        self._wake = asyncio.Event()
        self._stop = asyncio.Event()
        self._round_running = False

    async def start(self) -> None:
        """启动唯一后台任务。"""
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="aimux-monitor")

    async def stop(self) -> None:
        """取消后台任务并等待其退出。"""
        self._stop.set()
        self._wake.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def update_settings(self, settings: Settings) -> None:
        """替换运行时设置并立即唤醒调度器。"""
        self.settings = settings
        self._wake.set()

    async def _run(self) -> None:
        """执行立即检查与可唤醒的周期等待。"""
        while not self._stop.is_set():
            if not self.settings.monitoring_enabled:
                self._wake.clear()
                await self._wait_for_signal()
                continue
            if not self._round_running:
                self._round_running = True
                try:
                    await self.run_round()
                finally:
                    self._round_running = False
            else:
                logger.info("监控轮次仍在执行，跳过本次调度 tick")
            if not self.settings.monitoring_enabled:
                continue
            if self._wake.is_set():
                self._wake.clear()
                continue
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wait_for_signal(), timeout=_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                continue

    async def _wait_for_signal(self) -> None:
        """等待开关变更或停止信号。"""
        wake_task = asyncio.create_task(self._wake.wait())
        stop_task = asyncio.create_task(self._stop.wait())
        try:
            await asyncio.wait([wake_task, stop_task], return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in (wake_task, stop_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(wake_task, stop_task, return_exceptions=True)

    async def run_round(self) -> None:
        """读取当前启用账号并以最多五个并发执行一轮。"""
        with Session(get_engine()) as session:
            accounts, _ = account_dao.list_accounts(session, limit=10_000, status="active")
            targets = [(account, monitor_service.default_model(session, account.type)) for account in accounts]
        semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

        async def check(target: tuple[Account, str | None]) -> None:
            account, model = target
            async with semaphore:
                if model is None:
                    result = monitor_service.MonitorResult(
                        None, 0, False, None, "monitor_model_unavailable", "该协议没有测试默认模型"
                    )
                else:
                    result = await monitor_service.ping_account(account, model, self.settings)
                with Session(get_engine()) as session:
                    current = account_dao.get(session, account.id)
                    if current is not None:
                        monitor_service.save_result(session, current, result)

        await asyncio.gather(*(check(target) for target in targets))
