from __future__ import annotations
import os
import sys
from pathlib import Path
import uvicorn

def main() -> None:
    root = Path(__file__).resolve().parent
    backend_dir = root / "src" / "backend"
    if not backend_dir.exists():
        raise SystemExit("Cannot find backend directory at src/backend")

    # Allow importing src/backend/main.py as module "main".
    sys.path.insert(0, str(backend_dir))
    os.chdir(root)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=[str(root / "src")])

if __name__ == "__main__":
    main()