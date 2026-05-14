"""Executable email sandbox for AuthSkillBench sample generation."""

__all__ = ["EmailSandboxAPI"]


def __getattr__(name: str):
    if name == "EmailSandboxAPI":
        from .app.api import EmailSandboxAPI

        return EmailSandboxAPI
    raise AttributeError(name)
