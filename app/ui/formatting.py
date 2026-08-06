from __future__ import annotations

from datetime import datetime, timedelta, timezone

# 前端统一按本地时区（Asia/Shanghai）展示时间。
LOCAL_TZ = timezone(timedelta(hours=8))


def format_time(value: str | None) -> str:
    """把 UTC ISO 字符串格式化为本地时间 YYYY-MM-DD HH:MM:SS。

    兼容带 Z 与带 +00:00 的两种写法；无时区信息时按 UTC 处理；
    解析失败时回退原值，空值返回“-”。
    """
    if not value:
        return "-"
    try:
        text = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return value
