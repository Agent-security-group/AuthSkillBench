"""Runtime package for the AuthSkillBench workspace scenario."""

__all__ = ["WorkspaceScenarioAPI"]


def __getattr__(name: str):
    if name == "WorkspaceScenarioAPI":
        from .api import WorkspaceScenarioAPI

        return WorkspaceScenarioAPI
    raise AttributeError(name)
