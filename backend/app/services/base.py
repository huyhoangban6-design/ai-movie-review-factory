from typing import Protocol

from app.schemas.publishing import PublishOutput, UploadOutput
from app.schemas.render import QAReportOutput, RenderOutput, SubtitleOutput
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


# ---------- Phase 5: render / subtitle / QA ----------
class RenderLike(Protocol):
    script_id: int
    video_url: str | None
    audio_url: str | None
    duration_s: float | None
    fps: int | None


class RenderProvider(Protocol):
    name: str = "offline"

    def render(self, script_id: int, audio_url: str, duration_s: float) -> RenderOutput: ...


class SubtitleProvider(Protocol):
    name: str = "offline"

    def build(self, script_id: int, timeline: object | None, generation: object | None) -> SubtitleOutput: ...


class QAProvider(Protocol):
    name: str = "offline"

    def run(self, script_id: int, context: dict) -> list[QAReportOutput]: ...


# ---------- Phase 6: YouTube publishing ----------
class PublishingProvider(Protocol):
    name: str = "offline"

    def upload(
        self,
        script_id: int,
        title: str,
        description: str | None,
        tags: list[str],
        render_url: str | None,
        privacy: str,
        notify_subscribers: bool,
    ) -> UploadOutput: ...

    def publish(
        self,
        youtube_video_id: str,
        title: str,
        privacy: str,
        publish_at: object | None,
    ) -> PublishOutput: ...