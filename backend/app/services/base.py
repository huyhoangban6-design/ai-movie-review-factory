from typing import Protocol

from app.schemas.research import AnglesOutput, MovieResearchOutput, OpportunityScoreOutput


class ResearchProvider(Protocol):
    name: str = "offline"

    def research(self, title: str, year: int | None, genres: list[str]) -> MovieResearchOutput: ...


class OpportunityProvider(Protocol):
    name: str = "offline"

    def score(self, movie: object) -> OpportunityScoreOutput: ...


class AngleProvider(Protocol):
    name: str = "offline"

    def angles(self, movie: object) -> AnglesOutput: ...