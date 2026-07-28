"""Runtime package for the AuthSkillBench browser scenario."""

__all__ = [
    "BrowserScenarioAPI",
    "BROWSER_CANDIDATE_SELECTION_POLICY",
    "DEFAULT_TRAJECTORIES_DIR",
    "run_live_agent_case",
    "run_live_agent_cases",
    "write_live_trajectories",
]


def __getattr__(name: str):
    if name == "BrowserScenarioAPI":
        from .api import BrowserScenarioAPI
        return BrowserScenarioAPI
    if name == "BROWSER_CANDIDATE_SELECTION_POLICY":
        from .candidate_selection import BROWSER_CANDIDATE_SELECTION_POLICY
        return BROWSER_CANDIDATE_SELECTION_POLICY
    if name == "DEFAULT_TRAJECTORIES_DIR":
        from .trajectory import DEFAULT_TRAJECTORIES_DIR
        return DEFAULT_TRAJECTORIES_DIR
    if name == "run_live_agent_case":
        from .agent_runner import run_live_agent_case
        return run_live_agent_case
    if name == "run_live_agent_cases":
        from .agent_runner import run_live_agent_cases
        return run_live_agent_cases
    if name == "write_live_trajectories":
        from .agent_runner import write_live_trajectories
        return write_live_trajectories
    raise AttributeError(name)