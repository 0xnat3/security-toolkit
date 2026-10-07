"""Single source of truth for port names and risk notes."""
from typing import NamedTuple


class PortInfo(NamedTuple):
    service: str
    risk: str | None = None  # None = nothing notable about the port itself


PORTS: dict[int, PortInfo] = {
    20: PortInfo("FTP-Data", "FTP data channel, traffic is unencrypted"),
    21: PortInfo("FTP", "Unencrypted file transfer"),
    22: PortInfo("SSH", "Remote access: confirm it is intended and hardened"),
    23: PortInfo("Telnet", "Unencrypted remote access"),
    25: PortInfo("SMTP", "Mail server: open relay and spam risk"),
    53: PortInfo("DNS", "Open resolvers can be abused for amplification attacks"),
    80: PortInfo("HTTP", "Unencrypted web traffic"),
    110: PortInfo("POP3", "Unencrypted mail retrieval"),
    119: PortInfo("NNTP"),
    123: PortInfo("NTP"),
    135: PortInfo("MS RPC", "Windows RPC: common attack surface"),
    139: PortInfo("NetBIOS-SSN", "Windows file sharing: should not be exposed"),
    143: PortInfo("IMAP", "Unencrypted mail retrieval"),
    161: PortInfo("SNMP", "Often left with default community strings"),
    389: PortInfo("LDAP", "Directory service, unencrypted by default"),
    443: PortInfo("HTTPS"),
    445: PortInfo("SMB", "File sharing: ransomware and worm vector"),
    587: PortInfo("SMTP-Submission"),
    636: PortInfo("LDAPS"),
    1433: PortInfo("MSSQL", "Database exposed to the network"),
    1521: PortInfo("OracleDB", "Database exposed to the network"),
    3306: PortInfo("MySQL", "Database exposed to the network"),
    3389: PortInfo("RDP", "Remote desktop: frequent brute-force target"),
    5432: PortInfo("PostgreSQL", "Database exposed to the network"),
    5900: PortInfo("VNC", "Remote desktop access, often weakly protected"),
    6379: PortInfo("Redis", "Database exposed to the network"),
    8080: PortInfo("HTTP-Alt", "Alternate web port, often an admin panel or proxy"),
    8443: PortInfo("HTTPS-Alt"),
    27017: PortInfo("MongoDB", "Database exposed to the network"),
}

_UNKNOWN = PortInfo("Unknown")


def service_name(port: int) -> str:
    return PORTS.get(port, _UNKNOWN).service


def risk_note(port: int) -> str | None:
    return PORTS.get(port, _UNKNOWN).risk