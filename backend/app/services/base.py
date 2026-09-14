from typing import Protocol

from app.schemas.research import AnglesOutput, MovieResearchOutput, OpportunityScoreOutput
from app.schemas.scripting import ScriptOutput, TimelineOutput, VoiceOutput
from app.schemas.visual import (
    AssetCreate,
    CopyrightReviewInput,
    CopyrightReviewOutput,
    VisualPlanMetadata,
)


class SentenceLike(Protocol):
    sentence: str
    start_s: float
    end_s: float


class AssetLike(Protocol):
    source: str | None
    commercial_use: str | None
    duration_s: float | None
    license: str | None
    transformations: list | None


class ResearchProvider(Protocol):
    name: str = "offline"

    def research(self, title: str, year: int | None, genres: list[str]) -> MovieResearchOutput: ...


class OpportunityProvider(Protocol):
    name: str = "offline"

    def score(self, movie: object) -> OpportunityScoreOutput: ...


class AngleProvider(Protocol):
    name: str = "offline"

    def angles(self, movie: object) -> AnglesOutput: ...


class ScriptProvider(Protocol):
    name: str = "offline"

    def generate(self, movie: object, angle: object | None) -> ScriptOutput: ...


class VoiceProvider(Protocol):
    name: str = "offline"

    def synthesize(
        self,
        text: str,
        *,
        provider: str,
        model: str,
        voice_id: str,
        language: str,
        speed: float,
        commercial_use: str,
        license_url: str | None,
        cloning_permission: bool,
    ) -> VoiceOutput: ...


class TimelineProvider(Protocol):
    name: str = "offline"

    def build(self, full_text: str, segments: list[str], sentences: list[SentenceLike]) -> TimelineOutput: ...


class VisualPlannerProvider(Protocol):
    name: str = "offline"

    def plan(self, segments: list[object]) -> VisualPlanMetadata: ...


class AssetProvider(Protocol):
    name: str = "offline"

    def acquire(
        self,
        visual_plan: VisualPlanMetadata,
        segment_index: int | None,
        source_hint: str,
    ) -> list[AssetCreate]: ...


class CopyrightProvider(Protocol):
    name: str = "offline"

    def evaluate(self, asset: AssetLike) -> CopyrightReviewOutput: ...