# -*- coding: utf-8 -*-
"""Browser 3-variant live agent runner.

Mirrors the Email scenario's ``run_live_agent.py`` entry point shown in
slide 06 of the AuthSkillBench presentation.  One command expands the
contrast group into three independent sandboxed cases.  The API key lives
in ``.env`` and is NEVER echoed to the terminal.

Usage (from the ``authskillbench-main`` directory)::

    python -m scenarios.browser.scripts.run_live_agent \\
        --case browser_3x_portal_search \\
        --temperature 0 --max-turns 6 \\
        --output-dir outputs/browser_3x_live/live/trajectories \\
        --candidate-records-output outputs/browser_3x_live/live/candidate_records.jsonl \\
        --skip-report outputs/browser_3x_live/live/skipped.json

Or, for the zero-cost replay preset::

    python -m scenarios.browser.scripts.run_live_agent --mode replay
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from _experiment_3x import (  # noqa: E402  (ROOT patched above)
    _build_case,
    _filtered_tool_specs,
    _live_client,
    THREAT_VARIANTS,
)


def _load_env(env_path):
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except ImportError:
    _load_env(ROOT / ".env")


def run_case(case, max_turns, traj_dir, temperature=0.0):
    """Run a single case through the live ToolCallingAgentRunner.

    The API key is read from ``DEEPSEEK_API_KEY`` / ``OPENAI_API_KEY`` in
    the environment (never printed).  Returns the trajectory payload
    plus candidate invocation.
    """
    from agent_framework import (
        ToolCallingAgentRunner,
        openai_tools_from_specs,
    )
    from scenarios.browser.app.agent_runner import build_initial_messages
    from scenarios.browser.app.api import BrowserScenarioAPI, DEFAULT_STATE_PATH
    from scenarios.browser.app.candidate_selection import (
        select_candidate_invocation,
    )
    from scenarios.browser.app.mock_web_server import ScenarioWebServer
    import shutil

    # --- Fresh sandbox ------------------------------------------------------
    ScenarioWebServer.shutdown_all()
    from _experiment_3x import _register_experiment_mock_domains
    _register_experiment_mock_domains()

    state_dir = ROOT / "outputs" / "states_3x" / case["case_id"]
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    if state_path.exists():
        state_path.unlink()
    shutil.copy2(str(DEFAULT_STATE_PATH), str(state_path))

    api = BrowserScenarioAPI(state_path=state_path, apply_side_effects=False)
    api.scenario.apply_threat_profile(case.get("threat_profile"))

    # --- Live LLM run ------------------------------------------------------
    client = _live_client()
    client.temperature = temperature
    msgs = build_initial_messages(case)
    tools = openai_tools_from_specs(_filtered_tool_specs())
    runner = ToolCallingAgentRunner(
        client=client, tools=tools, invoke_tool=api.invoke,
        max_turns=max_turns,
    )
    steps, final_message, _conversation = runner.run(msgs)

    # --- Scoring + verdict (mirror _experiment_3x scoring) ----------------
    from _experiment_3x import (
        _contextual_risk,
        _threat_context_description,
    )
    snap = _threat_context_description(case.get("threat_profile"))
    score, verdict, flags, _, _ = _contextual_risk(
        steps, snap, case.get("user_authorization")
    )

    traj_id = case["case_id"].replace("controlled_3x__", "") + ".live"
    trajectory = {
        "schema_version": "authskillbench.browser_trajectory.v1",
        "trajectory_id": traj_id,
        "case_id": case["case_id"],
        "contrast_group_id": "3x_controlled_experiment",
        "skill_under_test": case.get("skill_under_test", ""),
        "source": client.model,
        "model": client.model,
        "temperature": temperature,
        "case": case,
        "task": case.get("task", {}),
        "threat_profile": case.get("threat_profile", {}),
        "steps": steps,
        "score": score,
        "verdict": verdict,
        "flags": flags,
        "final_message": final_message,
    }

    traj_dir.mkdir(parents=True, exist_ok=True)
    traj_path = traj_dir / (traj_id + ".trajectory.json")
    traj_path.write_text(json.dumps(trajectory, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    candidate_inv, selection_meta = select_candidate_invocation(
        case, steps, _filtered_tool_specs())

    return trajectory, candidate_inv, selection_meta


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="run_live_agent",
        description="AuthSkillBench Browser: run the 3-variant contrast "
                    "group through a live LLM.")
    p.add_argument("--case", default="browser_3x_portal_search",
                   help="Contrast group id (informational label only)")
    p.add_argument("--mode", choices=["live", "replay"], default="live",
                   help="Use replay for zero-cost local sanity check.")
    p.add_argument("--temperature", type=float, default=0.0,
                   help="LLM sampling temperature (default 0 for reproducibility)")
    p.add_argument("--max-turns", type=int, default=6,
                   help="Max tool-call loops per case")
    p.add_argument("--output-dir", required=False,
                   default=None,
                   help="Directory for individual trajectory JSON files")
    p.add_argument("--candidate-records-output", required=False,
                   default=None,
                   help="Path to write browser_candidate_records.jsonl")
    p.add_argument("--skip-report", required=False,
                   default=None,
                   help="Path to write browser_skipped.json")
    args = p.parse_args(argv)

    model = (os.environ.get("DEEPSEEK_MODEL")
             or os.environ.get("OPENAI_MODEL")
             or "deepseek-v4-flash")

    run_root = ROOT / "outputs" / "browser_3x_live" / args.mode
    traj_dir = Path(args.output_dir) if args.output_dir else run_root / "trajectories"
    cand_path = (Path(args.candidate_records_output)
                 if args.candidate_records_output
                 else run_root / "candidate_records" / "browser_candidate_records.jsonl")
    skip_path = (Path(args.skip_report)
                 if args.skip_report
                 else run_root / "candidate_records" / "browser_skipped.json")
    for d in (traj_dir, cand_path.parent, skip_path.parent):
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 86)
    print("  bench \u2014 run_live_agent  (Browser scenario)")
    print("=" * 86)
    print("  case       :", args.case)
    print("  mode       :", args.mode)
    if args.mode == "live":
        print("  model      :", model)
        print("  temperature:", args.temperature)
    print("  max_turns  :", args.max_turns)
    print("  output     :", traj_dir)
    print("  candidate  :", cand_path)
    print("  skipped    :", skip_path)
    print()

    if args.mode == "replay":
        # Delegate to _experiment_3x replay mode which already writes
        # the same output artifacts.
        from _experiment_3x import _mode_replay
        _mode_replay(show_safe_comparison=True)
        return 0

    cand_lines: list[str] = []
    skipped: list[dict] = []

    HORIZ = "=" * 86
    for vname, threat in THREAT_VARIANTS:
        case = _build_case(vname, threat)
        print(HORIZ)
        print("  VARIANT:", vname)
        print(HORIZ)
        print("  task_type :", case["task"].get("task_type", ""))
        print("  operation :", case["task"].get("operation", ""))
        user_auth = case.get("user_authorization") or {}
        print("  user_auth : scope=" + str(user_auth.get("scope", ""))
              + "  disallowed=" + str(user_auth.get("disallowed", [])))
        threat_type = (case.get("threat_profile") or {}).get("threat_type", "")
        print("  threat    : Type=" + threat_type
              + "  Profile="
              + str((case.get("threat_profile") or {})
                    .get("threat_profile_id", "")))
        print("-" * 86)
        trajectory, candidate_inv, selection_meta = run_case(
            case, args.max_turns, traj_dir, temperature=args.temperature)
        traj_id = trajectory["trajectory_id"]
        if candidate_inv is None:
            skipped.append({
                "trajectory_id": traj_id,
                "case_id": case["case_id"],
                "reason": selection_meta.get(
                    "strategy", "no_consequential_tool_call"),
                "candidate_tool_names": selection_meta.get(
                    "candidate_tool_names", []),
            })
            print("  candidate : (skipped - "
                  + skipped[-1]["reason"] + ")")
        else:
            cand_lines.append(json.dumps({
                "case_id": case["case_id"],
                "trajectory_id": traj_id,
                "contrast_group_id": "3x_controlled_experiment",
                "skill_under_test": case.get("skill_under_test", ""),
                "threat_profile_id": (case.get("threat_profile", {})
                                      .get("threat_profile_id", "")),
                "threat_type": (case.get("threat_profile", {})
                                .get("threat_type", "")),
                "candidate_invocation": candidate_inv,
                "runtime_metadata": {
                    "mode": "live",
                    "score": trajectory["score"],
                    "verdict": trajectory["verdict"],
                    "flags": trajectory["flags"],
                    "candidate_selection": selection_meta,
                    "temperature": args.temperature,
                    "model": model,
                },
            }, ensure_ascii=False, sort_keys=True))
            print("  candidate :", candidate_inv.get("skill", ""),
                  "-> score=", trajectory["score"],
                  " verdict=", trajectory["verdict"])
        print()

    cand_path.write_text(
        "\n".join(cand_lines) + ("\n" if cand_lines else ""),
        encoding="utf-8")
    skip_path.write_text(
        json.dumps(skipped, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print(HORIZ)
    print("  SUMMARY")
    print(HORIZ)
    fmt = "  {:<16} {:>8}  {:<18} {}"
    print(fmt.format("VARIANT", "SCORE", "VERDICT", "FLAGS"))
    print("  " + "-" * 82)
    cand_by_id = {json.loads(line)["trajectory_id"]: json.loads(line)
                  for line in cand_lines}
    for vname, _ in THREAT_VARIANTS:
        traj_path = traj_dir / (vname + ".live.trajectory.json")
        if not traj_path.exists():
            print(fmt.format(vname, "-", "(missing)", ""))
            continue
        traj = json.loads(traj_path.read_text(encoding="utf-8"))
        print(fmt.format(
            vname, traj["score"], traj["verdict"],
            " | ".join(traj.get("flags", []))))
    print()
    print("  candidate_records :", len(cand_lines), "records")
    print("  skipped           :", len(skipped), "record(s)")
    print("  trajectories      :",
          len(list(traj_dir.glob("*.trajectory.json"))), "file(s)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
