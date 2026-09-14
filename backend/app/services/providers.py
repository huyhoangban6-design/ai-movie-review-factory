from typing import Optional

from app.schemas.research import (
    ANGLE_PERSONAS,
    Angle,
    AnglesOutput,
    MovieResearchOutput,
    OpportunityScoreOutput,
    ResearchedSource,
)
from app.services.base import AngleProvider, OpportunityProvider, ResearchProvider

# Trọng số phase 2 (được calibrate lại ở Phase 7 bằng analytics).
WEIGHTS = {
    "demand": 0.25,
    "trend": 0.20,
    "audience_fit": 0.15,
    "evergreen": 0.15,
    "competition": 0.15,
    "difficulty": 0.10,
}


def weighted_opportunity_score(s: OpportunityScoreOutput) -> float:
    return round(
        max(
            0.0,
            min(
                100.0,
                s.demand * WEIGHTS["demand"]
                + s.trend * WEIGHTS["trend"]
                + s.audience_fit * WEIGHTS["audience_fit"]
                + s.evergreen * WEIGHTS["evergreen"]
                + s.competition * WEIGHTS["competition"]
                + s.difficulty * WEIGHTS["difficulty"],
            ),
        ),
        1,
    )


class OfflineResearchProvider(ResearchProvider):
    name = "offline"

    def research(self, title: str, year: int | None, genres: list[str]) -> MovieResearchOutput:
        return MovieResearchOutput(
            title=title,
            year=year,
            genres=genres,
            director=None,
            synopsis=None,
            summary="(offline research) Dữ liệu mẫu do provider offline tạo để test pipeline.",
            facts=["(offline) Chưa có nguồn thật — dự kiến bật TMDB/web search ở provider thật."],
            themes=["(offline)"],
            sources=[
                ResearchedSource(
                    source_type="offline",
                    source_url=None,
                    publisher="movie-review-factory/offline",
                    summary="Placeholder provenance cho Phase 2.",
                )
            ],
        )


class OfflineOpportunityProvider(OpportunityProvider):
    name = "offline"

    def score(self, movie: object) -> OpportunityScoreOutput:
        year = getattr(movie, "year", None)
        demand = 55.0 if year is not None and year >= 2015 else 48.0
        competition = 42.0
        trend = 38.0 if year is not None and year >= 2018 else 30.0
        audience_fit = 57.0
        evergreen = 66.0 if year is not None and year <= 2000 else 52.0
        difficulty = 35.0
        s = OpportunityScoreOutput(
            overall=0.0,
            demand=demand,
            competition=competition,
            trend=trend,
            audience_fit=audience_fit,
            evergreen=evergreen,
            difficulty=difficulty,
            confidence=0.5,
            rationale="(offline) Điểm mẫu heuristic. Cần provider thật để có confidence cao.",
        )
        s.overall = weighted_opportunity_score(s)
        return s


class OfflineAngleProvider(AngleProvider):
    name = "offline"

    def angles(self, movie: object) -> AnglesOutput:
        title = getattr(movie, "title", "Phim")
        year = getattr(movie, "year", None)
        persona_pool = [p for p in ANGLE_PERSONAS if p.label != "list"]
        selected = persona_pool[:6]
        out: list[Angle] = []
        tag = f"{year}" if year else ""
        for i, p in enumerate(selected, start=1):
            out.append(
                Angle(
                    angle_type=p.label,
                    title=p.title_fmt.format(title=title, n=i),
                    summary=p.summary_fmt.format(title=title, n=i),
                    hook=p.hook_fmt.format(title=title, n=i),
                    rationale=f"{p.rationale_fmt.format(title=title, n=i)} (offline, tag {tag or 'n/a'})",
                )
            )
        return AnglesOutput(angles=out)