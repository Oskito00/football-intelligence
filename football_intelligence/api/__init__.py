"""API home for exposing Football Intelligence Agent capabilities."""

from football_intelligence._compat import LegacyExport, resolve_legacy_export

_LEGACY_EXPORTS = {
    "legacy_chat_api_app": LegacyExport("chatbot.api", "app"),
}

__all__ = list(_LEGACY_EXPORTS)


def __getattr__(name: str):
    return resolve_legacy_export(_LEGACY_EXPORTS, name)
