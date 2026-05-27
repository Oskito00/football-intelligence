"""Read-only Analyst Agent home for natural-language football questions.

Compatibility exports point at the legacy chatbot orchestrator until Analyst
Agent internals are migrated into this package.
"""

from football_intelligence._compat import LegacyExport, make_legacy_getattr

_LEGACY_EXPORTS = {
    "LegacyAnalystAgent": LegacyExport("chatbot.core.chatbot", "FootballChatbot"),
    "LegacyFunctionDispatcher": LegacyExport(
        "chatbot.core.function_dispatcher",
        "FunctionDispatcher",
    ),
    "LegacyMemoryManager": LegacyExport("chatbot.core.memory_manager", "MemoryManager"),
}

__all__ = list(_LEGACY_EXPORTS)
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
