#region Imports
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from src.aggregation.daily_stats import AggregatedStats, DailyStats
#endregion


#region Data Classes


@dataclass
class DailyTotal:
    """Aggregated usage metrics for a single day."""

    date: str
    total_prompts: int = 0
    total_responses: int = 0
    total_sessions: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class ModelTotal:
    """Aggregated usage metrics for a single model."""

    model: str
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class ProjectTotal:
    """Aggregated usage metrics for a project/folder."""

    folder: str
    total_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class UsageSummary:
    """
    Aggregated usage summary across all devices.

    Attributes:
        totals: Overall totals across entire history
        daily: Aggregated metrics per day
        models: Aggregated metrics per model
        projects: Aggregated metrics per project/folder
    """

    totals: DailyTotal
    daily: Dict[str, DailyTotal]
    models: Dict[str, ModelTotal]
    projects: Dict[str, ProjectTotal]

    @property
    def start_date(self) -> str | None:
        return min(self.daily.keys()) if self.daily else None

    @property
    def end_date(self) -> str | None:
        return max(self.daily.keys()) if self.daily else None

    def to_aggregated_stats(self) -> AggregatedStats:
        """Convert summary daily totals to AggregatedStats for dashboard usage."""
        daily_stats: Dict[str, DailyStats] = {}

        for date, total in self.daily.items():
            daily_stats[date] = DailyStats(
                date=date,
                total_prompts=total.total_prompts,
                total_responses=total.total_responses,
                total_sessions=total.total_sessions,
                total_tokens=total.total_tokens,
                input_tokens=total.input_tokens,
                output_tokens=total.output_tokens,
                cache_creation_tokens=total.cache_creation_tokens,
                cache_read_tokens=total.cache_read_tokens,
                models=set(),  # Not tracked in summary
                folders=set(),  # Not tracked in summary
            )

        overall = self.totals

        overall_stats = DailyStats(
            date="all",
            total_prompts=overall.total_prompts,
            total_responses=overall.total_responses,
            total_sessions=overall.total_sessions,
            total_tokens=overall.total_tokens,
            input_tokens=overall.input_tokens,
            output_tokens=overall.output_tokens,
            cache_creation_tokens=overall.cache_creation_tokens,
            cache_read_tokens=overall.cache_read_tokens,
            models=set(),
            folders=set(),
        )

        return AggregatedStats(
            daily_stats=daily_stats,
            overall_totals=overall_stats,
        )


#endregion

