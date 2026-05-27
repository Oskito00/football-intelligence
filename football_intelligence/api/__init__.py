"""API home for exposing Football Intelligence Agent capabilities."""

from football_intelligence._compat import LegacyExport, make_legacy_getattr

_LEGACY_EXPORTS = {
    "legacy_chat_api_app": LegacyExport("chatbot.api", "app"),
}

__all__ = list(_LEGACY_EXPORTS)
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
