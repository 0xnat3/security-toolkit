"""System audit and network throughput sampling. Pure logic."""
import platform
import time
from datetime import datetime, timedelta

import psutil


def system_info() -> dict:
    memory = psutil.virtual_memory()
    boot = psutil.boot_time()
    cores = psutil.cpu_count(logical=True)
    return {
        "os": platform.system() or "Unknown",
        "release": platform.release() or "Unknown",
        "cpu": platform.processor() or f"{cores} logical cores",
        "cpu_cores": cores,
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_gb": round(memory.total / 1024**3, 2),
        "ram_percent": memory.percent,
        "boot_time": datetime.fromtimestamp(boot).strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": str(timedelta(seconds=int(time.time() - boot))),
    }


def network_speed(sample_seconds: float = 1.0) -> dict:
    """Average upload/download in KB/s over a short sample window."""
    sample_seconds = max(0.2, min(float(sample_seconds), 5.0))
    before = psutil.net_io_counters()
    start = time.monotonic()
    time.sleep(sample_seconds)
    after = psutil.net_io_counters()
    elapsed = time.monotonic() - start
    return {
        "upload_kb_s": round((after.bytes_sent - before.bytes_sent) / 1024 / elapsed, 2),
        "download_kb_s": round((after.bytes_recv - before.bytes_recv) / 1024 / elapsed, 2),
    }