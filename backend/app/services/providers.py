import hashlib
import re

from app.schemas.research import (
    ANGLE_PERSONAS,
    Angle,
    AnglesOutput,
    MovieResearchOutput,
    OpportunityScoreOutput,
    ResearchedSource,
)
from app.schemas.scripting import (
    LicenseInfo,
    ScriptOutput,
    ScriptSegment,
    SectionId,
    SentenceTimestamp,
    TimelineOutput,
    TimelineSegment,
    VoiceOutput,
    WordTimestamp,
)
from app.services.base import (
    AngleProvider,
    OpportunityProvider,
    ResearchProvider,
    ScriptProvider,
    TimelineProvider,
    VoiceProvider,
)

# Ngữ tốc đọc trung bình offline (chars / giây) để ước lượng duration.
CHAR_SPEED = 12.0

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


# ---------- Phase 3: script / voice / timeline ----------
SECTION_ORDER = [
    "hook",
    "thesis",
    "context",
    "analysis",
    "evidence",
    "character_theme",
    "critique",
    "conclusion",
    "cta",
]


def _split_sentences(text: str) -> list[str]:
    parts = [p for p in re.split(r"(?<=[.!?。！？])[\s]+", text.strip()) if p]
    return parts or [text.strip()]


class OfflineScriptProvider(ScriptProvider):
    name = "offline"

    def generate(self, movie: object, angle: object | None) -> ScriptOutput:
        title = getattr(movie, "title", "Phim")
        year = getattr(movie, "year", None)
        angle_title = getattr(angle, "title", None) if angle is not None else None
        angle_type = getattr(angle, "angle_type", None) if angle is not None else None
        hook = getattr(angle, "hook", None) if angle is not None else None

        doc_title = angle_title or f"Review {title}{f' ({year})' if year else ''}"
        head = f"{title}{f' ({year})' if year else ''}"
        content = {
            "hook": hook or f"Bạn đang phân vân có nên xem {head} không? Video này sẽ giúp bạn quyết định nhanh.",
            "thesis": f"{head} là một bộ phim đáng để xem nhờ cấu trúc kể chuyện chặt chẽ và diễn xuất ấn tượng, dù không tránh khỏi vài điểm trừ. "
            "(Đây là luận điểm mẫu của provider offline cho pipeline test.)",
            "context": f"Ra mắt trong bối cảnh điện ảnh thị trường sôi động, {head} nhanh chóng thu hút sự chú ý của khán giả. "
            "Những thông tin bối cảnh chi tiết sẽ được bổ sung khi cắm provider nghiên cứu thật.",
            "analysis": f"Phần phân tích tập trung vào cách {head} dẫn dắt cảm xúc: nhịp phim, cách xây dựng xung đột và sự phát triển của từng tuyến nhân vật. "
            "Mỗi yếu tố đều nằm trong sơ đồ HOOK→THESIS→EVIDENCE theo đặc tả Script Agent.",
            "evidence": "Bằng chứng chính là các phân cảnh then chốt, thông điệp được cài cắm và lựa chọn đạo diễn. "
            "(Provider offline chưa kéo được đúng trích đoạn — sẽ thay bằng dữ kiện thật ở provider LLM.)",
            "character_theme": "Ở lớp chủ đề, bộ phim đặt ra câu hỏi về lý trí và cảm xúc, sự lựa chọn và hệ quả. "
            "Nhân vật trung tâm nâng đỡ toàn bộ thông điệp, tạo điểm tựa cho người xem đồng cảm.",
            "critique": "Điểm trừ nằm ở một số đoạn nhịp kéo dài và tuyến phụ chưa được khai thác triệt để. "
            "Tuy nhiên những khiếm khuyết này không lấn át giá trị tổng thể của tác phẩm.",
            "conclusion": f"{head} xứng đáng xuất hiện trong danh sách cân nhắc của bạn. "
            "Nếu bạn hợp thể loại và qua được vài chỗ lê thê, bộ phim sẽ đáp lại đủ cả.",
            "cta": "Bạn thấy sao? Bình luận bên dưới chia sẻ cảm nhận về bộ phim, và đừng quên đăng ký kênh để không bỏ lỡ bài review tiếp theo.",
        }

        if angle_type:
            content["thesis"] = (
                f"Với góc nhìn '{angle_type}', {head} đáng để xem vì câu chuyện có chiều sâu hơn vẻ ngoài. "
                "(Luận điểm mẫu offline định hướng theo góc nội dung đã chọn.)"
            )

        segments = [
            ScriptSegment(section=SectionId(label), text=content[label]) for label in SECTION_ORDER
        ]
        total_text = " ".join(content[s] for s in SECTION_ORDER)
        words = len(re.findall(r"[\w\u0600-\u06ff]+", total_text, re.UNICODE)) or 1
        duration = round(len(total_text) / CHAR_SPEED, 2)
        return ScriptOutput(
            title=doc_title,
            segments=segments,
            word_count=words,
            estimated_duration_s=duration,
        )


class OfflineVoiceProvider(VoiceProvider):
    name = "offline"

    def synthesize(  # noqa: PLR0913
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
    ) -> VoiceOutput:
        if commercial_use != "yes":
            raise ValueError(
                f"Voice '{voice_id}' không cho phép dùng thương mại (commercial_use={commercial_use})."
            )
        sentences = _split_sentences(text)
        words: list[WordTimestamp] = []
        out_sentences: list[SentenceTimestamp] = []
        rate = CHAR_SPEED * speed
        total_duration = max(len(text.strip()) / rate, 0.1)

        # Chia thời gian theo tỷ lệ độ dài câu (mô phỏng timestamps cho offline).
        cursor = 0.0
        total_chars = max(sum(len(s) for s in sentences), 1)
        for s in sentences:
            seg_dur = len(s) / rate
            start, end = round(cursor, 3), round(cursor + seg_dur, 3)
            out_sentences.append(SentenceTimestamp(sentence=s, start_s=start, end_s=end))
            # Word-level chia đều trong câu (giả lập, đủ cho Visual Planner test).
            for w in re.findall(r"\S+", s):
                w_share = len(w) / max(len(s), 1)
                w_start = start + w_share * (end - start) * 0.5
                words.append(
                    WordTimestamp(
                        word=w,
                        start_s=round(min(w_start, end), 3),
                        end_s=round(min(w_start + 1.0 / rate, end), 3),
                    )
                )
            cursor = end

        key = hashlib.sha256(f"{text}|{voice_id}|{model}|{speed}".encode()).hexdigest()[:16]
        return VoiceOutput(
            provider=provider,
            model=model,
            voice_id=voice_id,
            language=language,
            speed=speed,
            audio_url=f"null://offline/{key}.mp3",
            duration_s=round(total_duration, 3),
            words=words,
            sentences=out_sentences,
            license=LicenseInfo(
                commercial_use=commercial_use,
                license_url=license_url,
                cloning_permission=cloning_permission,
            ),
        )


def _char_ranges(text: str, units: list[str]) -> list[tuple[int, int]]:
    """Trả về [start, end) char để căn timeline deterministic theo vị trí text."""
    ranges: list[tuple[int, int]] = []
    pos = 0
    for u in units:
        start = text.find(u, pos)
        if start == -1:
            start = pos
            pos += len(u)
        else:
            pos = start + len(u)
        ranges.append((start, pos))
    return ranges


class OfflineTimelineProvider(TimelineProvider):
    name = "offline"

    def build(self, full_text: str, segments: list[str], sentences: list[SentenceLike]) -> TimelineOutput:
        seg_span = _char_ranges(full_text, segments)
        sentence_spans = _char_ranges(full_text, [s.sentence for s in sentences])

        out: list[TimelineSegment] = []
        for i, (seg_text, (seg_start, seg_end)) in enumerate(zip(segments, seg_span), start=1):
            seg_sentences: list[SentenceTimestamp] = []
            for span, sent in zip(sentence_spans, sentences):
                if span[0] < seg_end and span[1] > seg_start:
                    seg_sentences.append(sent)
            if seg_sentences:
                start = min(s.start_s for s in seg_sentences)
                end = max(s.end_s for s in seg_sentences)
            else:
                start = end = 0.0
            out.append(
                TimelineSegment(
                    position=i,
                    section=SECTION_ORDER[i - 1],
                    text=seg_text,
                    start_s=round(start, 3),
                    end_s=round(end, 3),
                )
            )
        total = out[-1].end_s if out else 0.0
        return TimelineOutput(total_duration_s=round(total, 3), segments=out, matches=True)