from __future__ import annotations

import os
import sys
from pathlib import Path
import uvicorn

def load_env(env_path: Path) -> None:
    """Lightweight .env loader to configure settings without external dependencies."""
    if not env_path.exists():
        return
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ.setdefault(key, val)
    except Exception:
        pass

def main() -> None:
    root = Path(__file__).resolve().parent
    src_dir = root / "src"
    
    if not src_dir.exists():
        raise SystemExit("Error: Cannot find 'src' directory. Please run from the project root.")

    # Load environment variables from .env
    load_env(root / ".env")

    # Read configuration from environment with fallback defaults
    host = os.environ.get("HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "8000"))
    except ValueError:
        port = 8000
    
    # Reload in development mode, default to True for local running
    reload_env = os.environ.get("RELOAD", "true").lower() in ("true", "1", "yes")
    
    # Insert 'src' directory into sys.path to allow clean namespaced imports
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Keep working directory at root for relative model weights and Solomon dataset paths
    os.chdir(root)

    print(f"Starting NAMI Routing Engine on http://{host}:{port} (reload={reload_env})")
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload_env,
        reload_dirs=[str(src_dir)] if reload_env else None,
        log_level="info"
    )

if __name__ == "__main__":
    main()