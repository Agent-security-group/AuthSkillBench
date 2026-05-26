"""Executable email scenario for AuthSkillBench sample generation."""

__all__ = ["EmailScenarioAPI"]


def __getattr__(name: str):
    if name == "EmailScenarioAPI":
        from .app.api import EmailScenarioAPI

        return EmailScenarioAPI
    raise AttributeError(name)
