from __future__ import annotations

import copy
import re
import unittest
from pathlib import Path

from scenarios.email.app.benchmark import list_cases, load_case
from scenarios.email.app.live_report import build_live_run_report
from scenarios.email.app.trajectory_samples import (
    _candidate_invocation_for_trajectory,
    candidate_records_from_trajectory_paths,
    iter_trajectory_paths,
    read_trajectory,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_TRAJECTORIES_DIR = ROOT / "scenarios" / "email" / "outputs" / "live_trajectories"
ATTACHMENT_TRAJECTORY = (
    LIVE_TRAJECTORIES_DIR / "email_scenario_attachment_substitution_001.deepseek_chat_completions.trajectory.json"
)


class EmailScenarioSmokeTests(unittest.TestCase):
    def _live_trajectory_paths(self) -> list[Path]:
        if not LIVE_TRAJECTORIES_DIR.exists():
            self.skipTest(f"live trajectories not found: {LIVE_TRAJECTORIES_DIR}")
        paths = iter_trajectory_paths([LIVE_TRAJECTORIES_DIR])
        if len(paths) < 10:
            self.skipTest(f"expected current live trajectory set, found {len(paths)} file(s)")
        return paths

    def test_case_catalog_has_expected_runtime_contexts(self) -> None:
        cases = list_cases()
        self.assertEqual(10, len(cases))

        case = load_case("email_scenario_attachment_substitution_001")
        self.assertEqual("send_email", case["task"]["operation"])
        self.assertEqual("adversarial_untrusted", case["threat_type"])
        self.assertNotIn("candidate_invocation", case)

    def test_attachment_trajectory_derives_send_candidate(self) -> None:
        if not ATTACHMENT_TRAJECTORY.exists():
            self.skipTest(f"trajectory not found: {ATTACHMENT_TRAJECTORY}")

        trajectory = copy.deepcopy(read_trajectory(ATTACHMENT_TRAJECTORY))
        trajectory["candidate_invocation"] = None
        candidate = _candidate_invocation_for_trajectory(trajectory)

        self.assertIsNotNone(candidate)
        self.assertEqual("gmail.users.messages.send", candidate["skill"])
        selection = trajectory["runtime_metadata"]["candidate_selection"]
        self.assertIn("task.operation:send_email", selection["selected_reasons"])

    def test_live_trajectory_materialization_counts(self) -> None:
        records, skipped = candidate_records_from_trajectory_paths(self._live_trajectory_paths())

        self.assertEqual(7, len(records))
        self.assertEqual(3, len(skipped))
        by_case = {record["case_id"]: record for record in records}
        self.assertEqual(
            "gmail.users.messages.send",
            by_case["email_scenario_attachment_substitution_001"]["candidate_invocation"]["skill"],
        )

    def test_live_report_contains_all_cases(self) -> None:
        paths = self._live_trajectory_paths()
        trajectories = [read_trajectory(path) for path in paths]
        records, skipped = candidate_records_from_trajectory_paths(paths)

        report = build_live_run_report(trajectories, records, skipped)

        self.assertIn("- Trajectories: `10`", report)
        self.assertIn("- Candidate records: `7`", report)
        self.assertIn("- Skipped trajectories: `3`", report)
        self.assertEqual(10, len(re.findall(r"^### `email_scenario_", report, flags=re.MULTILINE)))
        self.assertIn("### `email_scenario_attachment_substitution_001`", report)
        self.assertIn("- Candidate: `gmail.users.messages.send`", report)


if __name__ == "__main__":
    unittest.main()
