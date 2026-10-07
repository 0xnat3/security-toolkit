"""What each report contains. The URL's report_type is only ever used as a key into REPORTS."""
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Column:
    header: str
    key: str
    weight: float = 1.0  # relative width in the PDF
    fmt: Callable[[Any], Any] | None = None


@dataclass(frozen=True)
class Report:
    title: str
    filename: str
    columns: tuple[Column, ...]


def _when(value):
    return str(value).replace("T", " ").rstrip("Z")  # 2026-10-07T08:51:16Z -> 2026-10-07 08:51:16


def _upper(value):
    return str(value).upper()


WHEN = Column("When (UTC)", "created_at", 1.3, _when)

REPORTS = {
    "port_scans": Report(
        "Port scans",
        "port-scans",
        (
            WHEN,
            Column("Host", "host", 1.5),
            Column("Address", "ip", 1.1),
            Column("Ports", "port_range", 0.8),
            Column("Open", "open_count", 0.6),
            Column("Open ports", "open_ports", 2.2),
        ),
    ),
    "audits": Report(
        "System audits",
        "system-audits",
        (
            WHEN,
            Column("System", "system", 1.2),
            Column("CPU (%)", "cpu_percent", 0.7),
            Column("RAM (%)", "ram_percent", 0.7),
            Column("RAM (GB)", "ram_gb", 0.7),
            Column("Uptime", "uptime", 1.2),
        ),
    ),
    "integrity_baselines": Report(
        "Integrity baselines",
        "integrity-baselines",
        (
            WHEN,
            Column("Folder", "directory", 4.0),
            Column("Algorithm", "algorithm", 0.9, _upper),
            Column("Files", "file_count", 0.6),
        ),
    ),
    "network_logs": Report(
        "Network samples",
        "network-logs",
        (
            WHEN,
            Column("Upload (KB/s)", "upload_kb_s", 1.0),
            Column("Download (KB/s)", "download_kb_s", 1.0),
        ),
    ),
}