"""Runtime API for the synthetic Coding + Workspace scenario."""

__all__ = ["CodingWorkspaceSyntheticAPI"]


def __getattr__(name: str):
    if name == "CodingWorkspaceSyntheticAPI":
        from .api import CodingWorkspaceSyntheticAPI

        return CodingWorkspaceSyntheticAPI
    raise AttributeError(name)

