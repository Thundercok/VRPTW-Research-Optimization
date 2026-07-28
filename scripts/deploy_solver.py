"""Stage and deploy the solver service to Google Cloud Run.

The service needs the research package, the backend modules it reuses, the
Solomon instances and the transfer weights — but not the frontend, the docs, the
benchmark logs, node_modules, or the 13 MB Gehring-Homberger set. Uploading the
repository as-is would push all of that into every build context, so this
assembles a minimal staging tree from the sources of truth and deploys that.

    python scripts/deploy_solver.py --project august-lamp-499804-h3

Requires an authenticated `gcloud` session with Cloud Run and Cloud Build
enabled on the project.
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (source, destination-relative-to-build-context)
COPY_TREES: list[tuple[Path, str]] = [
    (ROOT / "src" / "vrptw", "src/vrptw"),
    (ROOT / "src" / "backend", "src/backend"),
    (ROOT / "data" / "Solomon", "data/Solomon"),
]

COPY_FILES: list[tuple[Path, str]] = [
    (ROOT / "solver_service" / "app.py", "app.py"),
    (ROOT / "solver_service" / "Dockerfile", "Dockerfile"),
    (ROOT / "solver_service" / "requirements.txt", "requirements.txt"),
    (ROOT / "rl_alns_dr_v15.safetensors", "rl_alns_dr_v15.safetensors"),
]

# Present only after a transfer-learning / GNN run.
OPTIONAL_FILES: list[tuple[Path, str]] = [
    (ROOT / "docs" / "model" / "rl_alns_transfer.safetensors", "docs/model/rl_alns_transfer.safetensors"),
    (ROOT / "docs" / "model" / "gnn_edge_predictor.pt", "docs/model/gnn_edge_predictor.pt"),
]

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "*.log")


def build_staging(dest: Path) -> None:
    for source, rel in COPY_TREES:
        if not source.exists():
            raise SystemExit(f"Missing required source tree: {source}")
        shutil.copytree(source, dest / rel, ignore=IGNORE)

    for source, rel in COPY_FILES:
        if not source.exists():
            raise SystemExit(f"Missing required file: {source}")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for source, rel in OPTIONAL_FILES:
        if source.exists():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"  + optional {rel}")
        else:
            print(f"  - skipped (absent) {rel}")


def run(cmd: list[str]) -> str:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=os.name == "nt")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        print(result.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(f"Command failed with exit code {result.returncode}")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Google Cloud project id")
    parser.add_argument("--service", default="vrptw-solver", help="Cloud Run service name")
    parser.add_argument("--region", default="asia-southeast1", help="Cloud Run region")
    parser.add_argument("--memory", default="4Gi")
    parser.add_argument("--cpu", default="2")
    # A solve fans out over a ProcessPoolExecutor and saturates every core it is
    # given, so overlapping requests on one instance only make each slower.
    parser.add_argument("--concurrency", default="2")
    parser.add_argument("--max-instances", default="2")
    parser.add_argument("--timeout", default="900", help="Request timeout in seconds")
    parser.add_argument("--token", default=None, help="SOLVER_API_TOKEN value; generated when omitted")
    parser.add_argument("--hf-model-repo", default=None, help="Hugging Face model repo to pull weights from at boot")
    parser.add_argument("--stage-only", action="store_true")
    parser.add_argument("--stage-dir", default=None)
    args = parser.parse_args()

    staging_root = Path(args.stage_dir) if args.stage_dir else Path(tempfile.mkdtemp(prefix="vrptw-solver-"))
    staging = staging_root / "context"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    print(f"Staging into {staging}")
    build_staging(staging)
    total_mb = sum(p.stat().st_size for p in staging.rglob("*") if p.is_file()) / (1024 * 1024)
    print(f"Staged {total_mb:.1f} MB")

    if args.stage_only:
        print("--stage-only set; not deploying.")
        return 0

    token = args.token or os.getenv("SOLVER_API_TOKEN") or secrets.token_urlsafe(32)
    env_vars = [f"SOLVER_API_TOKEN={token}"]
    if args.hf_model_repo:
        env_vars.append(f"VRPTW_HF_MODEL_REPO={args.hf_model_repo}")

    run(
        [
            "gcloud",
            "run",
            "deploy",
            args.service,
            f"--source={staging}",
            f"--project={args.project}",
            f"--region={args.region}",
            f"--memory={args.memory}",
            f"--cpu={args.cpu}",
            f"--concurrency={args.concurrency}",
            f"--max-instances={args.max_instances}",
            f"--timeout={args.timeout}",
            # Scale to zero between solves; the free tier is measured in
            # instance-seconds, so an idle instance is pure cost.
            "--min-instances=0",
            # Torch import dominates cold start; the boost keeps it off the
            # first request's critical path.
            "--cpu-boost",
            "--allow-unauthenticated",
            f"--set-env-vars={','.join(env_vars)}",
            "--quiet",
        ]
    )

    url = run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            args.service,
            f"--project={args.project}",
            f"--region={args.region}",
            "--format=value(status.url)",
        ]
    )

    print()
    print("Deployed.")
    print(f"  SOLVER_REMOTE_URL = {url}")
    print(f"  SOLVER_API_TOKEN  = {token}")
    print("Set both on the Render service so the API forwards solves here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
