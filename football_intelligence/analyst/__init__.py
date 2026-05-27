"""Read-only Analyst Agent home for natural-language football questions.

Compatibility exports point at the legacy chatbot orchestrator until Analyst
Agent internals are migrated into this package.
"""

from football_intelligence._compat import LegacyExport, resolve_legacy_export

_LEGACY_EXPORTS = {
    "LegacyAnalystAgent": LegacyExport("chatbot.core.chatbot", "FootballChatbot"),
    "LegacyFunctionDispatcher": LegacyExport(
        "chatbot.core.function_dispatcher",
        "FunctionDispatcher",
    ),
    "LegacyMemoryManager": LegacyExport("chatbot.core.memory_manager", "MemoryManager"),
}

__all__ = list(_LEGACY_EXPORTS)


def __getattr__(name: str):
    return resolve_legacy_export(_LEGACY_EXPORTS, name)
