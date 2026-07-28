"""Publish the trained DDQN-ALNS weights to a Hugging Face model repo.

The solver service bundles a copy of the weights in its image, but pulls from
the Hub at boot when ``VRPTW_HF_MODEL_REPO`` is set. Publishing here is what
lets a retrained checkpoint reach production without rebuilding and
redeploying the container.

    python scripts/publish_model_hf.py --repo oggishi/vrptw-ddqn-alns

Requires an authenticated `hf` session (`hf auth login`) or ``HF_TOKEN``.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (source, path within the model repo). The DR checkpoint is the one the solver
# loads by default; the others are published for reproducibility.
ARTIFACTS: list[tuple[Path, str]] = [
    (ROOT / "rl_alns_dr_v15.safetensors", "rl_alns_dr_v15.safetensors"),
    (ROOT / "docs" / "model" / "rl_alns_transfer.safetensors", "rl_alns_transfer.safetensors"),
    (ROOT / "docs" / "model" / "gnn_edge_predictor.pt", "gnn_edge_predictor.pt"),
]

CARD = """---
license: mit
tags:
  - reinforcement-learning
  - operations-research
  - vehicle-routing
  - vrptw
library_name: safetensors
---

# DDQN-ALNS weights for VRPTW

Trained controller weights for the hybrid DDQN-ALNS solver in
[VRPTW-Research-Optimization](https://github.com/Thundercok/VRPTW-Research-Optimization).
The network selects destroy/repair operators and acceptance behaviour inside an
Adaptive Large Neighbourhood Search over the Vehicle Routing Problem with Time
Windows.

## Files

| File | Role |
| ---- | ---- |
| `rl_alns_dr_v15.safetensors` | Domain-randomization checkpoint. Loaded by default. |
| `rl_alns_transfer.safetensors` | Transfer-learning checkpoint (Solomon RC classes). |
| `gnn_edge_predictor.pt` | Edge-scoring GNN used for repair heatmap guidance. |

## Results

Under independent cold starts, the hybrid reaches the same minimum vehicle-count
floor as the ALNS baseline but hits it in 100% of runs versus 30-70% for the
baseline, and cuts total distance by 1.75%-4.07% at matched vehicle count on
Solomon and 200-customer Homberger instances. At 400 customers the vehicle-count
edge is small and only significant on two of three instances tested
(`c2_4_1` p=0.0078, `r2_4_1` p=0.0156; `rc2_4_1` p=0.3750).

## Usage

These are controller weights for a specific solver, not a standalone model. The
production service downloads them at boot:

```python
from huggingface_hub import hf_hub_download

path = hf_hub_download("{repo}", "rl_alns_dr_v15.safetensors")
```

See `solver_service/app.py` in the repository for the full loading path.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Target model repo id, e.g. oggishi/vrptw-ddqn-alns")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    from huggingface_hub import HfApi

    present = [(src, rel) for src, rel in ARTIFACTS if src.exists()]
    if not present:
        raise SystemExit("No weight files found; nothing to publish.")

    with tempfile.TemporaryDirectory(prefix="vrptw-model-") as tmp:
        staging = Path(tmp)
        for source, rel in present:
            target = staging / rel
            target.write_bytes(source.read_bytes())
            print(f"  + {rel} ({source.stat().st_size / 1024:.0f} KB)")
        for source, rel in ARTIFACTS:
            if not source.exists():
                print(f"  - skipped (absent) {rel}")

        (staging / "README.md").write_text(CARD.replace("{repo}", args.repo), encoding="utf-8")

        api = HfApi()
        api.create_repo(repo_id=args.repo, repo_type="model", private=args.private, exist_ok=True)
        api.upload_folder(
            folder_path=str(staging),
            repo_id=args.repo,
            repo_type="model",
            commit_message="Publish DDQN-ALNS controller weights",
        )

    print(f"Published: https://huggingface.co/{args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
