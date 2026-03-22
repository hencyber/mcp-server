"""
System Monitor - MCP Server

MCP-server som ger verktyg för att övervaka systemet.
Agenter kan använda dessa verktyg för att kolla CPU, minne, disk osv.

Kör med: python server.py
"""

import asyncio
import platform
import datetime
import os

import psutil
from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field


mcp = FastMCP("System Monitor")


# --- Verktyg ---


@mcp.tool()
def get_cpu_usage(
    interval: Annotated[
        float,
        Field(
            description="Mätintervall i sekunder, t.ex. 1.0",
            ge=0.1,
            le=5.0,
        ),
    ] = 1.0,
) -> str:
    """Mät CPU-användning i procent under ett kort intervall."""
    total = psutil.cpu_percent(interval=interval)
    per_core = psutil.cpu_percent(interval=0, percpu=True)
    cores_str = ", ".join(f"Kärna {i}: {p}%" for i, p in enumerate(per_core))
    return (
        f"CPU-användning (totalt): {total}%\n"
        f"Antal kärnor: {psutil.cpu_count()}\n"
        f"Per kärna: {cores_str}"
    )


@mcp.tool()
def get_memory_info() -> str:
    """Hämta information om RAM-minne: totalt, använt, ledigt och procentuell användning."""
    mem = psutil.virtual_memory()
    return (
        f"RAM totalt: {mem.total / (1024**3):.1f} GB\n"
        f"RAM använt: {mem.used / (1024**3):.1f} GB\n"
        f"RAM ledigt: {mem.available / (1024**3):.1f} GB\n"
        f"Användning: {mem.percent}%"
    )


@mcp.tool()
def get_disk_usage(
    path: Annotated[
        str,
        Field(description="Sökväg att kontrollera diskutrymme för, t.ex. '/'"),
    ] = "/",
) -> str:
    """Hämta diskanvändning för en angiven sökväg."""
    try:
        usage = psutil.disk_usage(path)
        return (
            f"Disk ({path}):\n"
            f"  Totalt: {usage.total / (1024**3):.1f} GB\n"
            f"  Använt: {usage.used / (1024**3):.1f} GB\n"
            f"  Ledigt: {usage.free / (1024**3):.1f} GB\n"
            f"  Användning: {usage.percent}%"
        )
    except FileNotFoundError:
        return f"Fel: Sökvägen '{path}' hittades inte."


@mcp.tool()
def get_network_info() -> str:
    """Hämta nätverksstatistik: totalt skickad och mottagen data."""
    net = psutil.net_io_counters()
    return (
        f"Nätverk:\n"
        f"  Skickat: {net.bytes_sent / (1024**2):.1f} MB\n"
        f"  Mottaget: {net.bytes_recv / (1024**2):.1f} MB\n"
        f"  Paket skickade: {net.packets_sent}\n"
        f"  Paket mottagna: {net.packets_recv}"
    )


@mcp.tool()
def list_top_processes(
    sort_by: Annotated[
        str,
        Field(
            description="Sortera efter 'cpu' eller 'memory'",
        ),
    ] = "cpu",
    count: Annotated[
        int,
        Field(
            description="Antal processer att visa, t.ex. 5",
            ge=1,
            le=20,
        ),
    ] = 5,
) -> str:
    """Lista de processer som använder mest CPU eller minne."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    key = "cpu_percent" if sort_by.lower() == "cpu" else "memory_percent"
    procs.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)

    lines = [f"Topp {count} processer (sorterat på {sort_by}):"]
    for i, p in enumerate(procs[:count], 1):
        lines.append(
            f"  {i}. {p['name']} (PID {p['pid']}) – "
            f"CPU: {p.get('cpu_percent', 0):.1f}%, "
            f"Minne: {p.get('memory_percent', 0):.1f}%"
        )
    return "\n".join(lines)


@mcp.tool()
def get_system_uptime() -> str:
    """Hämta hur länge systemet har varit igång sedan senaste omstart."""
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    now = datetime.datetime.now()
    uptime = now - boot_time

    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    return (
        f"System: {platform.node()}\n"
        f"OS: {platform.system()} {platform.release()}\n"
        f"Startades: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Uptime: {hours}h {minutes}m {seconds}s"
    )


@mcp.tool()
def search_logs(
    keyword: Annotated[
        str,
        Field(description="Nyckelord att söka efter i loggfilen"),
    ],
    log_file: Annotated[
        str,
        Field(
            description="Sökväg till loggfil, t.ex. '/var/log/syslog'",
        ),
    ] = "/var/log/syslog",
    max_lines: Annotated[
        int,
        Field(
            description="Max antal matchande rader att returnera",
            ge=1,
            le=50,
        ),
    ] = 10,
) -> str:
    """Sök efter ett nyckelord i en systemloggfil och returnera matchande rader."""
    if not os.path.isfile(log_file):
        return f"Fel: Loggfilen '{log_file}' hittades inte."

    try:
        matches = []
        with open(log_file, "r", errors="ignore") as f:
            for line in f:
                if keyword.lower() in line.lower():
                    matches.append(line.strip())
                    if len(matches) >= max_lines:
                        break

        if not matches:
            return f"Inga träffar för '{keyword}' i {log_file}"

        header = f"Hittade {len(matches)} träffar för '{keyword}' i {log_file}:\n"
        return header + "\n".join(matches)
    except PermissionError:
        return f"Fel: Behörighet saknas för att läsa '{log_file}'."


# Starta servern
if __name__ == "__main__":
    asyncio.run(
        mcp.run_http_async(
            host="0.0.0.0",
            port=8001,
            log_level="warning",
        )
    )
