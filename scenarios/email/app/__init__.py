"""Runtime package for the AuthSkillBench email scenario."""

__all__ = ["EmailScenarioAPI"]


def __getattr__(name: str):
    if name == "EmailScenarioAPI":
        from .api import EmailScenarioAPI

        return EmailScenarioAPI
    raise AttributeError(name)
