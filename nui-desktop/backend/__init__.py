"""CosmicTera NUI Desktop — Local Backend Service Package.

Provides the local-first Python backend for CosmicTera NUI Desktop on macOS:
- SQLite storage, Keychain secret adapter, and automatic secret redaction (`storage.py`)
- 15-category, 6-mode Granular Permission & Authorization Engine (`permissions.py`)
- Pluggable Intelligence Providers (`NativeNUIProvider`, `OllamaProvider`, `OptionalExternalProvider`) (`providers.py`)
- Tool Registry & Task Orchestrator across Files, Coding, Git, Web/Browser, API, CosmicTera Subsystems, and Hardware (`tools.py`, `orchestrator.py`)
- Localhost HTTP + SSE API Server (`127.0.0.1:8848`) (`server.py`)
"""

__version__ = "1.0.0"
