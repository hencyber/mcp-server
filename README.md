# System Monitor - MCP Server

MCP-server som exponerar verktyg för systemövervakning.
Använder FastMCP och psutil.

## Verktyg

Servern har 7 verktyg:

- `get_cpu_usage` - mäter CPU-användning
- `get_memory_info` - visar RAM-info
- `get_disk_usage` - kollar diskutrymme
- `get_network_info` - nätverksstatistik
- `list_top_processes` - topprocesser
- `get_system_uptime` - hur länge systemet kört
- `search_logs` - söker i loggfiler

Alla verktyg använder `Annotated` och `Field` för argument.

## Starta

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Startar på `http://localhost:8001`.
