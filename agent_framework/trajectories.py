from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_trajectory_files(trajectories: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for trajectory in trajectories:
        trajectory_id = str(trajectory.get("trajectory_id") or trajectory["case_id"])
        output_path = output_dir / f"{trajectory_id}.trajectory.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(trajectory, f, indent=2, sort_keys=False)
            f.write("\n")
