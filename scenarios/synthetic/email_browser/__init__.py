"""Synthetic Email + Browser scenario."""

__all__ = ["EmailBrowserSyntheticAPI"]


def __getattr__(name: str):
    if name == "EmailBrowserSyntheticAPI":
        from .app.api import EmailBrowserSyntheticAPI

        return EmailBrowserSyntheticAPI
    raise AttributeError(name)

