"""
Lightweight pretty logger for console output with timezone and icons.
"""

from datetime import datetime, timezone, timedelta


def log(msg: str, level: str = "INFO") -> None:
    """
    Logger padronizado para rastreabilidade de execução.
    Formato: [YYYY-MM-DD HH:MM:SS] [LEVEL] Icon Mensagem
    """
    # 1) Emit timestamped log with level icon.
    tz_br = timezone(timedelta(hours=-3))
    timestamp = datetime.now(tz_br).strftime("%Y-%m-%d %H:%M:%S")
    icons = {
        "INFO": "ℹ️",
        "WARN": "⚠️",
        "ERROR": "❌",
        "SUCCESS": "✅",
        "SYSTEM": "⚙️",
        "TOOL": "🛠️",
        "AI": "🤖",
    }
    icon = icons.get(level.upper(), "")
    print(f"[{timestamp}] [{level.upper()}] {icon} {msg}")


def _format_message(msg, args) -> str:
    # 2) Apply printf-style formatting if args were provided.
    if not args:
        return str(msg)
    try:
        return str(msg) % args
    except Exception:
        joined = " ".join(str(item) for item in args)
        return f"{msg} {joined}".strip()


def wrap_logger(logger):
    """
    Redirect common logger calls to pretty log output.
    """
    # 3) Replace logger methods with pretty logger functions.
    def _make(level: str):
        def _log(msg, *args, **kwargs):
            log(_format_message(msg, args), level)
        return _log
    logger.info = _make("INFO")
    logger.warning = _make("WARN")
    logger.error = _make("ERROR")
    logger.exception = _make("ERROR")
    return logger
