"""표준 로깅 설정. 모든 계층은 이 모듈의 get_logger()를 사용한다."""
import logging
import sys
from pathlib import Path

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    # storage/app.log 파일 핸들러 (웹 관리자 로그 뷰어 연동)
    handlers = [handler]
    try:
        storage_dir = Path(__file__).resolve().parent.parent.parent / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        log_file = storage_dir / "app.log"
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    except Exception:
        pass

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers = handlers
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
