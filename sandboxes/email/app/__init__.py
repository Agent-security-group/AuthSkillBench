"""Runtime package for the AuthSkillBench email sandbox."""

__all__ = ["EmailSandboxAPI"]


def __getattr__(name: str):
    if name == "EmailSandboxAPI":
        from .api import EmailSandboxAPI

        return EmailSandboxAPI
    raise AttributeError(name)
