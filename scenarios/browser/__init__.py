"""Executable browser scenario for AuthSkillBench sample generation."""

__all__ = ["BrowserScenarioAPI"]


def __getattr__(name: str):
    if name == "BrowserScenarioAPI":
        from .app.api import BrowserScenarioAPI

        return BrowserScenarioAPI
    raise AttributeError(name)