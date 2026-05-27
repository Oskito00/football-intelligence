"""Read-only Analyst Agent home for natural-language football questions.

The v1 Analyst Agent uses curated Analyst Tools for read-only data access.
Compatibility exports keep legacy chatbot imports available during migration.
"""

from football_intelligence._compat import LegacyExport, make_legacy_getattr
from football_intelligence.analyst.agent import (
    AnalystAgent,
    AnalystAgentResponse,
    AnalystToolCall,
)
from football_intelligence.analyst.tools import (
    ANALYST_TOOL_DEFINITIONS,
    AnalystFootballTools,
    AnalystToolDefinition,
)

_LEGACY_EXPORTS = {
    "LegacyAnalystAgent": LegacyExport("chatbot.core.chatbot", "FootballChatbot"),
    "LegacyFunctionDispatcher": LegacyExport(
        "chatbot.core.function_dispatcher",
        "FunctionDispatcher",
    ),
    "LegacyMemoryManager": LegacyExport("chatbot.core.memory_manager", "MemoryManager"),
}

__all__ = [
    "ANALYST_TOOL_DEFINITIONS",
    "AnalystAgent",
    "AnalystAgentResponse",
    "AnalystFootballTools",
    "AnalystToolCall",
    "AnalystToolDefinition",
    *list(_LEGACY_EXPORTS),
]
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
