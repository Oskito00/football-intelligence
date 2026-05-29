"""FastAPI server exposing the read-only Analyst Agent through the chat contract."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from football_intelligence.analyst import AnalystAgent
from football_intelligence.database import DatabaseSetupRequiredError
from football_intelligence.match_detail import MatchDetailNotFound
from football_intelligence.value import DEFAULT_SIGNAL_DAYS

_RECENT_CONTEXT_MESSAGE_LIMIT = 6
_GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_CORS_ALLOWED_ORIGINS = [
    "https://football-predictor-r7ov.onrender.com",
    "http://localhost:3000",
]


class Message(BaseModel):
    """Existing chat request body."""

    text: str


class AnalystAgentAnswer(Protocol):
    """Answer object returned by the Analyst Agent."""

    answer: str


class AnalystAgentLike(Protocol):
    """API-facing Analyst Agent behavior."""

    available_tool_names: Sequence[str]

    def answer_question(self, question: str) -> AnalystAgentAnswer:
        """Answer one Natural-Language Football Question."""


class AnalystChatServiceLike(Protocol):
    """Conversation-aware service used by the FastAPI app."""

    @property
    def available_tool_names(self) -> tuple[str, ...]:
        """Return read-only Analyst Tool names available to API callers."""

    def process_query(self, user_input: str) -> str:
        """Answer one chat request."""

    def reset_conversation(self) -> None:
        """Reset API conversation memory."""

    def get_conversation_stats(self) -> dict[str, Any]:
        """Return current conversation-memory counts."""


class FootballDataStatusLike(Protocol):
    """Status object returned by the Football Data Status service."""

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic API-ready status facts and warnings."""


class FootballDataStatusServiceLike(Protocol):
    """API-facing Football Data Status behavior."""

    def get_status(self) -> FootballDataStatusLike:
        """Return current Football Data Status."""


class PredictionBoardLike(Protocol):
    """Board object returned by the Prediction Board service."""

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic API-ready board data."""


class PredictionBoardServiceLike(Protocol):
    """API-facing Prediction Board behavior."""

    def today(self) -> PredictionBoardLike:
        """Return today's Prediction Board."""


class MarketValueSignalScanLike(Protocol):
    """Signal scan object returned by the Market Value Signal service."""

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic API-ready Market Value Signal data."""


class MarketValueSignalServiceLike(Protocol):
    """API-facing Market Value Signal behavior."""

    def today(self) -> MarketValueSignalScanLike:
        """Return today's Market Value Signals."""

    def next_days(
        self,
        *,
        days: int = DEFAULT_SIGNAL_DAYS,
    ) -> MarketValueSignalScanLike:
        """Return Market Value Signals for the next N days."""


class MatchDetailLike(Protocol):
    """Match detail object returned by the match detail service."""

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic API-ready match detail."""


class MatchDetailServiceLike(Protocol):
    """API-facing match detail behavior."""

    def get_match_detail(self, match_id: int) -> MatchDetailLike:
        """Return match detail for one match."""


class AnalystChatService:
    """Conversation-aware API service backed by the read-only Analyst Agent."""

    def __init__(self, agent: AnalystAgentLike):
        self._agent = agent
        self.reset_conversation()

    @classmethod
    def from_config(cls) -> "AnalystChatService":
        """Build the default API chat service from configured Analyst Agent dependencies."""
        return cls(AnalystAgent.from_config(_configured_chat_llm()))

    @property
    def available_tool_names(self) -> tuple[str, ...]:
        """Expose the curated read-only tools available to the API-backed agent."""
        return tuple(self._agent.available_tool_names)

    def process_query(self, user_input: str) -> str:
        """Answer a chat request while preserving lightweight conversation memory."""
        question = self._question_with_context(user_input)

        try:
            agent_response = self._agent.answer_question(question)
            answer = str(agent_response.answer)
        except Exception as exc:
            answer = f"I encountered an error processing your request: {exc}"

        self.conversation_memory["messages"].append(
            {"role": "user", "content": user_input}
        )
        self.conversation_memory["messages"].append(
            {"role": "assistant", "content": answer}
        )
        return answer

    def reset_conversation(self) -> None:
        """Reset API conversation memory without changing external response shape."""
        self.conversation_memory = {
            "messages": [],
            "context": {},
            "session_started": datetime.now().isoformat(),
        }

    def get_conversation_stats(self) -> dict[str, Any]:
        """Return current conversation-memory counts."""
        messages = self.conversation_memory.get("messages", [])
        return {
            "total_messages": len(messages),
            "user_messages": _count_messages_by_role(messages, "user"),
            "assistant_messages": _count_messages_by_role(messages, "assistant"),
            "session_started": self.conversation_memory.get("session_started"),
        }

    def _question_with_context(self, user_input: str) -> str:
        messages = self.conversation_memory.get("messages", [])
        if not messages:
            return user_input

        recent_messages = messages[-_RECENT_CONTEXT_MESSAGE_LIMIT:]
        context_lines = [
            f"{message['role'].title()}: {message['content']}"
            for message in recent_messages
        ]
        context_block = "\n".join(context_lines)
        return (
            "Recent conversation context:\n"
            f"{context_block}\n\n"
            f"Current question: {user_input}"
        )


class LazyAnalystChatService:
    """Lazy default service so importing the ASGI app does not touch LLM config."""

    def __init__(self):
        self._service: AnalystChatService | None = None

    @property
    def available_tool_names(self) -> tuple[str, ...]:
        return self._get_service().available_tool_names

    def process_query(self, user_input: str) -> str:
        return self._get_service().process_query(user_input)

    def reset_conversation(self) -> None:
        if self._service is not None:
            self._service.reset_conversation()

    def get_conversation_stats(self) -> dict[str, Any]:
        return self._get_service().get_conversation_stats()

    def _get_service(self) -> AnalystChatService:
        if self._service is None:
            self._service = AnalystChatService.from_config()
        return self._service


class LazyFootballDataStatusService:
    """Lazy default status service so importing the ASGI app does not touch DB config."""

    def __init__(self):
        self._service: FootballDataStatusServiceLike | None = None

    def get_status(self) -> FootballDataStatusLike:
        return self._get_service().get_status()

    def _get_service(self) -> FootballDataStatusServiceLike:
        if self._service is None:
            from football_intelligence.status import FootballDataStatusService

            self._service = FootballDataStatusService.from_config()
        return self._service


class LazyPredictionBoardService:
    """Lazy default board service so importing the ASGI app does not touch DB config."""

    def __init__(self):
        self._service: PredictionBoardServiceLike | None = None

    def today(self) -> PredictionBoardLike:
        return self._get_service().today()

    def _get_service(self) -> PredictionBoardServiceLike:
        if self._service is None:
            from football_intelligence.board import PredictionBoardService

            self._service = PredictionBoardService.from_config()
        return self._service


class LazyMarketValueSignalService:
    """Lazy default value service so importing the ASGI app does not touch DB config."""

    def __init__(self):
        self._service: MarketValueSignalServiceLike | None = None

    def today(self) -> MarketValueSignalScanLike:
        return self._get_service().today()

    def next_days(
        self,
        *,
        days: int = DEFAULT_SIGNAL_DAYS,
    ) -> MarketValueSignalScanLike:
        return self._get_service().next_days(days=days)

    def _get_service(self) -> MarketValueSignalServiceLike:
        if self._service is None:
            from football_intelligence.value import MarketValueSignalService

            self._service = MarketValueSignalService.from_config()
        return self._service


class LazyMatchDetailService:
    """Lazy default match detail service so importing the ASGI app does not touch DB config."""

    def __init__(self):
        self._service: MatchDetailServiceLike | None = None

    def get_match_detail(self, match_id: int) -> MatchDetailLike:
        return self._get_service().get_match_detail(match_id)

    def _get_service(self) -> MatchDetailServiceLike:
        if self._service is None:
            from football_intelligence.match_detail import MatchDetailService

            self._service = MatchDetailService.from_config()
        return self._service


class GroqChatRunnable:
    """Groq chat completion adapter used by the LangChain RunnableLambda."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._api_url = _GROQ_CHAT_COMPLETIONS_URL
        self._model = os.getenv("GROQ_MODEL", _DEFAULT_GROQ_MODEL)

    def invoke(self, prompt_value: Any) -> str:
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY is required for the Analyst Agent API")

        response = requests.post(
            self._api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            json={
                "model": self._model,
                "messages": _prompt_messages(prompt_value),
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])


def create_app(
    chat_service: AnalystChatServiceLike | None = None,
    status_service: FootballDataStatusServiceLike | None = None,
    board_service: PredictionBoardServiceLike | None = None,
    value_service: MarketValueSignalServiceLike | None = None,
    match_detail_service: MatchDetailServiceLike | None = None,
) -> FastAPI:
    """Create the FastAPI app while preserving the existing external contract."""
    service = chat_service if chat_service is not None else LazyAnalystChatService()
    football_status = (
        status_service
        if status_service is not None
        else LazyFootballDataStatusService()
    )
    prediction_board = (
        board_service if board_service is not None else LazyPredictionBoardService()
    )
    market_value_signals = (
        value_service if value_service is not None else LazyMarketValueSignalService()
    )
    match_detail = (
        match_detail_service
        if match_detail_service is not None
        else LazyMatchDetailService()
    )
    api_app = FastAPI()

    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api_app.post("/api/chat")
    async def chat(message: Message) -> dict[str, str]:
        try:
            response = service.process_query(message.text)
            return {"response": response}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api_app.post("/api/reset")
    async def reset_conversation() -> dict[str, str]:
        try:
            service.reset_conversation()
            return {"message": "Conversation reset successfully"}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api_app.get("/api/status")
    async def status() -> dict[str, Any]:
        try:
            return football_status.get_status().to_dict()
        except DatabaseSetupRequiredError as exc:
            raise _setup_required_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api_app.get("/api/board/today")
    async def today_prediction_board() -> dict[str, Any]:
        try:
            return prediction_board.today().to_dict()
        except DatabaseSetupRequiredError as exc:
            raise _setup_required_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api_app.get("/api/value-signals")
    async def value_signals(
        today: bool = False,
        days: int = DEFAULT_SIGNAL_DAYS,
    ) -> dict[str, Any]:
        try:
            if today:
                return market_value_signals.today().to_dict()
            return market_value_signals.next_days(days=days).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DatabaseSetupRequiredError as exc:
            raise _setup_required_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api_app.get("/api/matches/{match_id}")
    async def match_detail_by_id(match_id: int) -> dict[str, Any]:
        try:
            return match_detail.get_match_detail(match_id).to_dict()
        except MatchDetailNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DatabaseSetupRequiredError as exc:
            raise _setup_required_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api_app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "message": "Football Predictor API",
            "endpoints": {
                "chat": "/api/chat",
                "reset": "/api/reset",
                "status": "/api/status",
                "today_prediction_board": "/api/board/today",
                "value_signals": "/api/value-signals",
                "match_detail": "/api/matches/{match_id}",
                "docs": "/docs",
            },
        }

    api_app.state.analyst_chat_service = service
    api_app.state.football_data_status_service = football_status
    api_app.state.prediction_board_service = prediction_board
    api_app.state.market_value_signal_service = market_value_signals
    api_app.state.match_detail_service = match_detail
    return api_app


def _configured_chat_llm() -> Any:
    from langchain_core.runnables import RunnableLambda

    return RunnableLambda(GroqChatRunnable().invoke)


def _count_messages_by_role(messages: Sequence[dict[str, Any]], role: str) -> int:
    return sum(1 for message in messages if message["role"] == role)


def _setup_required_http_exception(exc: DatabaseSetupRequiredError) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": exc.code,
            "message": str(exc),
            "setup_command": exc.setup_command,
        },
    )


def _prompt_messages(prompt_value: Any) -> list[dict[str, str]]:
    if hasattr(prompt_value, "to_messages"):
        messages = prompt_value.to_messages()
    else:
        messages = getattr(prompt_value, "messages", prompt_value)

    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]

    return [
        {
            "role": _groq_message_role(message),
            "content": str(getattr(message, "content", message)),
        }
        for message in messages
    ]


def _groq_message_role(message: Any) -> str:
    role = getattr(message, "type", "user")
    if role == "human":
        return "user"
    if role == "ai":
        return "assistant"
    return str(role)


app = create_app()
