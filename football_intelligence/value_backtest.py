"""Value Backtest simulation for historical football Predictions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Literal, Protocol


VALUE_BACKTEST_TITLE = "Value Backtest"
DEFAULT_STARTING_BANKROLL = 100.0
DEFAULT_ODDS_MODE = "best"
OUTCOME_PROBABILITIES = (
    ("Home Win", "prob_home_win"),
    ("Draw", "prob_draw"),
    ("Away Win", "prob_away_win"),
)
RETAINED_PREDICTION_WARNING = (
    "This Value Backtest uses the retained Prediction per Completed Match and "
    "may not include all historical prediction revisions."
)
LOOSE_PREDICTION_TIMING_WARNING = (
    "Late or missing retained Prediction timestamps were allowed, so this "
    "Value Backtest is less trustworthy."
)
SKIPPED_MATCH_REASONS = (
    "missing_prediction",
    "missing_odds",
    "late_prediction",
    "missing_result",
)


class ValueBacktestQueries(Protocol):
    """Read-only facts required for a Value Backtest."""

    def get_value_backtest_matches(self) -> list[dict[str, Any]]:
        """Return Completed Matches, retained Predictions, and historical odds."""


@dataclass(frozen=True)
class ValueBacktestConfig:
    """Configuration for the first Value Backtest strategy."""

    starting_bankroll: float = DEFAULT_STARTING_BANKROLL
    kelly_multiplier: float = 1.0
    min_expected_value: float = 0.0
    odds_mode: Literal["best", "average"] = DEFAULT_ODDS_MODE
    strict_pre_kickoff_odds: bool = True
    strict_prediction_timing: bool = True

    def validate(self) -> None:
        if self.starting_bankroll <= 0:
            raise ValueError("starting bankroll must be greater than 0")
        if self.kelly_multiplier <= 0:
            raise ValueError("Kelly multiplier must be greater than 0")
        if self.odds_mode not in {"best", "average"}:
            raise ValueError("Backtest Odds Mode must be 'best' or 'average'")


@dataclass(frozen=True)
class ValueBacktestResult:
    """Structured Value Backtest result for CLI and future API consumers."""

    config: ValueBacktestConfig
    final_bankroll: float
    eligible_match_count: int
    paper_bets: Sequence[Mapping[str, Any]]
    skipped_matches: Mapping[str, int]
    max_drawdown: float
    bankroll_peak: float | None = None
    bankroll_trough: float | None = None

    def to_dict(self) -> dict[str, Any]:
        bankroll_peak = (
            self.final_bankroll if self.bankroll_peak is None else self.bankroll_peak
        )
        bankroll_trough = (
            self.final_bankroll if self.bankroll_trough is None else self.bankroll_trough
        )
        return {
            "title": VALUE_BACKTEST_TITLE,
            "headline": (
                f"{self.config.starting_bankroll:.2f} became "
                f"{self.final_bankroll:.2f}"
            ),
            "configuration": {
                "starting_bankroll": _round_money(self.config.starting_bankroll),
                "kelly_multiplier": self.config.kelly_multiplier,
                "min_expected_value": self.config.min_expected_value,
                "odds_mode": self.config.odds_mode,
                "strict_pre_kickoff_odds": self.config.strict_pre_kickoff_odds,
                "strict_prediction_timing": self.config.strict_prediction_timing,
            },
            "summary": _summarize_result(
                config=self.config,
                final_bankroll=self.final_bankroll,
                eligible_match_count=self.eligible_match_count,
                paper_bets=self.paper_bets,
                max_drawdown=self.max_drawdown,
                bankroll_peak=bankroll_peak,
                bankroll_trough=bankroll_trough,
            ),
            "skipped_matches": _skipped_match_counts(self.skipped_matches),
            "paper_bets": [dict(bet) for bet in self.paper_bets],
            "warnings": _warnings_for_config(self.config),
        }


class ValueBacktestService:
    """Run the default Value Backtest from a read-only query boundary."""

    def __init__(self, queries: ValueBacktestQueries):
        self._queries = queries

    @classmethod
    def from_config(cls) -> "ValueBacktestService":
        """Build the default service from configured read-only database access."""
        from football_intelligence.database.football import ReadOnlyFootballQueries

        return cls(ReadOnlyFootballQueries.from_config())

    def run(
        self,
        config: ValueBacktestConfig | None = None,
    ) -> ValueBacktestResult:
        """Run a Value Backtest using retained historical data."""
        config = config or ValueBacktestConfig()
        return run_value_backtest(self._queries.get_value_backtest_matches(), config)


def run_value_backtest(
    matches: Sequence[Mapping[str, Any]],
    config: ValueBacktestConfig | None = None,
) -> ValueBacktestResult:
    """Simulate Paper Stakes over Completed Matches in kickoff order."""
    config = config or ValueBacktestConfig()
    config.validate()

    bankroll = float(config.starting_bankroll)
    peak_bankroll = bankroll
    trough_bankroll = bankroll
    max_drawdown = 0.0
    eligible_match_count = 0
    paper_bets: list[dict[str, Any]] = []
    skipped_matches: Counter[str] = Counter()

    for match in sorted(matches, key=_match_sort_key):
        kickoff = _as_datetime(match.get("start_time"))
        if not _has_backtestable_result(match, kickoff):
            skipped_matches["missing_result"] += 1
            continue

        prediction = _prediction_for(match)
        if prediction is None:
            skipped_matches["missing_prediction"] += 1
            continue

        if config.strict_prediction_timing and _prediction_is_late_or_untimed(
            prediction,
            kickoff,
        ):
            skipped_matches["late_prediction"] += 1
            continue

        selected_odds = _select_odds(match, kickoff=kickoff, config=config)
        if not selected_odds:
            skipped_matches["missing_odds"] += 1
            continue

        eligible_match_count += 1
        match_bets = _qualifying_paper_bets(
            match,
            prediction=prediction,
            selected_odds=selected_odds,
            bankroll=bankroll,
            config=config,
        )
        if not match_bets:
            continue

        match_profit_loss = _settle_match_bets(match, match_bets)
        bankroll_after_match = bankroll + match_profit_loss
        for bet in match_bets:
            bet["bankroll_after_settlement"] = _round_money(bankroll_after_match)
        paper_bets.extend(match_bets)

        bankroll = bankroll_after_match
        peak_bankroll = max(peak_bankroll, bankroll)
        trough_bankroll = min(trough_bankroll, bankroll)
        if peak_bankroll > 0:
            max_drawdown = max(max_drawdown, (peak_bankroll - bankroll) / peak_bankroll)

    return ValueBacktestResult(
        config=config,
        final_bankroll=bankroll,
        eligible_match_count=eligible_match_count,
        paper_bets=paper_bets,
        skipped_matches=skipped_matches,
        max_drawdown=max_drawdown,
        bankroll_peak=peak_bankroll,
        bankroll_trough=trough_bankroll,
    )


def _summarize_result(
    *,
    config: ValueBacktestConfig,
    final_bankroll: float,
    eligible_match_count: int,
    paper_bets: Sequence[Mapping[str, Any]],
    max_drawdown: float,
    bankroll_peak: float,
    bankroll_trough: float,
) -> dict[str, Any]:
    wins = sum(1 for bet in paper_bets if bet["result"] == "win")
    losses = sum(1 for bet in paper_bets if bet["result"] == "loss")
    paper_bet_count = len(paper_bets)
    profit_loss = final_bankroll - config.starting_bankroll
    return {
        "starting_bankroll": _round_money(config.starting_bankroll),
        "final_bankroll": _round_money(final_bankroll),
        "profit_loss": _round_money(profit_loss),
        "roi": _round_ratio(profit_loss / config.starting_bankroll),
        "bankroll_peak": _round_money(bankroll_peak),
        "bankroll_trough": _round_money(bankroll_trough),
        "eligible_match_count": eligible_match_count,
        "paper_bet_count": paper_bet_count,
        "wins": wins,
        "losses": losses,
        "hit_rate": _round_ratio(wins / paper_bet_count) if paper_bet_count else 0.0,
        "max_drawdown": _round_ratio(max_drawdown),
        "average_odds": _round_ratio(_average(paper_bets, "odds")),
        "average_expected_value": _round_ratio(
            _average(paper_bets, "expected_value")
        ),
    }


def _skipped_match_counts(skipped_matches: Mapping[str, int]) -> dict[str, int]:
    counts = {
        reason: int(skipped_matches.get(reason, 0))
        for reason in SKIPPED_MATCH_REASONS
    }
    for reason, count in skipped_matches.items():
        if reason not in counts:
            counts[reason] = int(count)
    return counts


def _warnings_for_config(config: ValueBacktestConfig) -> list[dict[str, str]]:
    warnings = [
        {
            "code": "retained_predictions",
            "message": RETAINED_PREDICTION_WARNING,
        }
    ]
    if not config.strict_prediction_timing:
        warnings.append(
            {
                "code": "late_or_missing_prediction_timestamps_allowed",
                "message": LOOSE_PREDICTION_TIMING_WARNING,
            }
        )
    return warnings


def _has_backtestable_result(
    match: Mapping[str, Any],
    kickoff: datetime | None,
) -> bool:
    return (
        kickoff is not None
        and match.get("home_score") is not None
        and match.get("away_score") is not None
    )


def _prediction_is_late_or_untimed(
    prediction: Mapping[str, Any],
    kickoff: datetime,
) -> bool:
    prediction_date = _as_datetime(prediction.get("prediction_date"))
    return prediction_date is None or not _at_or_before(prediction_date, kickoff)


def _select_odds(
    match: Mapping[str, Any],
    *,
    kickoff: datetime,
    config: ValueBacktestConfig,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for odds in match.get("odds", []) or []:
        outcome = _normalize_outcome(odds.get("outcome") or odds.get("bet_value"))
        odds_value = _float_or_none(odds.get("odds_value"))
        if outcome is None or odds_value is None or odds_value <= 1:
            continue
        retrieved_at = _as_datetime(odds.get("retrieved_at"))
        if config.strict_pre_kickoff_odds and (
            retrieved_at is None or not _at_or_before(retrieved_at, kickoff)
        ):
            continue
        grouped.setdefault(outcome, []).append(
            {
                "outcome": outcome,
                "odds_value": odds_value,
                "bookmaker_name": odds.get("bookmaker_name"),
                "bookmaker_id": odds.get("bookmaker_id"),
                "retrieved_at": retrieved_at,
            }
        )

    selected: dict[str, dict[str, Any]] = {}
    for outcome, outcome_odds in grouped.items():
        if config.odds_mode == "average":
            selected[outcome] = _average_odds_row(outcome_odds)
        else:
            selected[outcome] = _best_odds_row(outcome_odds)
    return selected


def _average_odds_row(outcome_odds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    average_odds = sum(row["odds_value"] for row in outcome_odds) / len(outcome_odds)
    retrieved_times = [
        row["retrieved_at"] for row in outcome_odds if row["retrieved_at"]
    ]
    return {
        "odds_value": average_odds,
        "bookmaker_name": f"Average of {len(outcome_odds)} prices",
        "bookmaker_id": None,
        "retrieved_at": max(retrieved_times) if retrieved_times else None,
    }


def _best_odds_row(outcome_odds: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return max(outcome_odds, key=lambda row: row["odds_value"])


def _qualifying_paper_bets(
    match: Mapping[str, Any],
    *,
    prediction: Mapping[str, Any],
    selected_odds: Mapping[str, Mapping[str, Any]],
    bankroll: float,
    config: ValueBacktestConfig,
) -> list[dict[str, Any]]:
    bets: list[dict[str, Any]] = []
    for outcome, probability_key in OUTCOME_PROBABILITIES:
        bet = _qualifying_paper_bet(
            match,
            outcome=outcome,
            probability_key=probability_key,
            prediction=prediction,
            selected_odds=selected_odds,
            bankroll=bankroll,
            config=config,
        )
        if bet is not None:
            bets.append(bet)

    return bets


def _qualifying_paper_bet(
    match: Mapping[str, Any],
    *,
    outcome: str,
    probability_key: str,
    prediction: Mapping[str, Any],
    selected_odds: Mapping[str, Mapping[str, Any]],
    bankroll: float,
    config: ValueBacktestConfig,
) -> dict[str, Any] | None:
    odds = selected_odds.get(outcome)
    if odds is None:
        return None

    model_probability = _float_or_none(prediction.get(probability_key))
    if model_probability is None:
        return None

    odds_value = float(odds["odds_value"])
    expected_value = (model_probability * odds_value) - 1
    kelly_fraction = _kelly_fraction(model_probability, odds_value)
    if expected_value <= config.min_expected_value or kelly_fraction <= 0:
        return None

    stake = bankroll * kelly_fraction * config.kelly_multiplier
    return {
        "match_id": int(match["match_id"]),
        "start_time": _isoformat(match.get("start_time")),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "outcome": outcome,
        "model_probability": _round_ratio(model_probability),
        "implied_probability": _round_ratio(1 / odds_value),
        "odds": _round_ratio(odds_value),
        "expected_value": _round_ratio(expected_value),
        "kelly_fraction": _round_ratio(kelly_fraction),
        "stake": _round_money(stake),
        "bankroll_before_match": _round_money(bankroll),
        "bankroll_before_settlement": _round_money(bankroll),
        "bookmaker": odds.get("bookmaker_name"),
    }


def _settle_match_bets(
    match: Mapping[str, Any],
    match_bets: Sequence[dict[str, Any]],
) -> float:
    actual_outcome = _actual_outcome(match)
    match_profit_loss = 0.0
    for bet in match_bets:
        is_win = bet["outcome"] == actual_outcome
        profit_loss = bet["stake"] * (bet["odds"] - 1) if is_win else -bet["stake"]
        match_profit_loss += profit_loss
        bet.update(
            {
                "actual_outcome": actual_outcome,
                "result": "win" if is_win else "loss",
                "profit_loss": _round_money(profit_loss),
            }
        )

    return match_profit_loss


def _prediction_for(match: Mapping[str, Any]) -> Mapping[str, Any] | None:
    prediction = match.get("prediction")
    if prediction:
        return prediction
    if any(
        match.get(probability_key) is not None
        for _, probability_key in OUTCOME_PROBABILITIES
    ):
        return {
            "prediction_date": match.get("prediction_date"),
            "prob_home_win": match.get("prob_home_win"),
            "prob_draw": match.get("prob_draw"),
            "prob_away_win": match.get("prob_away_win"),
        }
    return None


def _actual_outcome(match: Mapping[str, Any]) -> str:
    home_score = int(match["home_score"])
    away_score = int(match["away_score"])
    if home_score > away_score:
        return "Home Win"
    if home_score < away_score:
        return "Away Win"
    return "Draw"


def _kelly_fraction(model_probability: float, odds_value: float) -> float:
    net_odds = odds_value - 1
    lose_probability = 1 - model_probability
    return ((net_odds * model_probability) - lose_probability) / net_odds


def _match_sort_key(match: Mapping[str, Any]) -> tuple[datetime, int]:
    kickoff = _as_datetime(match.get("start_time")) or datetime.max
    return kickoff, int(match.get("match_id") or 0)


def _normalize_outcome(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).lower().strip()
    if normalized in {"home", "1", "home win"} or normalized.startswith("home "):
        return "Home Win"
    if normalized in {"draw", "x", "tie"} or "draw" in normalized:
        return "Draw"
    if normalized in {"away", "2", "away win"} or normalized.startswith("away "):
        return "Away Win"
    return str(value).title()


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _at_or_before(left: datetime, right: datetime) -> bool:
    try:
        return left <= right
    except TypeError:
        return left.replace(tzinfo=None) <= right.replace(tzinfo=None)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _isoformat(value: Any) -> str | None:
    dt = _as_datetime(value)
    if dt is not None:
        return dt.isoformat()
    return str(value) if value is not None else None


def _average(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return sum(values) / len(values) if values else 0.0


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _round_ratio(value: float) -> float:
    return round(float(value), 4)
