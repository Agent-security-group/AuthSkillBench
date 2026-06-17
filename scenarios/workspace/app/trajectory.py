from __future__ import annotations

from pathlib import Path

from agent_framework import write_trajectory_files


DEFAULT_TRAJECTORIES_DIR = Path(__file__).resolve().parents[1] / "outputs" / "trajectories"

__all__ = ["DEFAULT_TRAJECTORIES_DIR", "write_trajectory_files"]
