from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


# ---------- internal DTOs (providers <-> services) ----------
class MovieResearchOutput(BaseModel):
    title: str
    year: Optional[int] = None
    director: Optional[str] = None
    genres: list[str] = Field(default_factory=list)
    synopsis: Optional[str] = None
    poster_url: Optional[str] = None
    release_date: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    summary: Optional[str] = None
    facts: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    sources: list["ResearchedSource"] = Field(default_factory=list)


class ResearchedSource(BaseModel):
    source_type: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    summary: Optional[str] = None
    provenance: Optional[str] = None


MovieResearchOutput.model_rebuild()


class OpportunityScoreOutput(BaseModel):
    overall: float = Field(ge=0, le=100)
    demand: float = Field(ge=0, le=100)
    competition: float = Field(ge=0, le=100)
    trend: float = Field(ge=0, le=100)
    audience_fit: float = Field(ge=0, le=100)
    evergreen: float = Field(ge=0, le=100)
    difficulty: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    rationale: str


class Angle(BaseModel):
    angle_type: str
    title: str
    summary: str
    hook: str
    rationale: str


class AnglesOutput(BaseModel):
    angles: list[Angle] = Field(default_factory=list)


@dataclass
class AnglePersona:
    label: str
    title_fmt: str
    summary_fmt: str
    hook_fmt: str
    rationale_fmt: str


ANGLE_PERSONAS: list[AnglePersona] = [
    AnglePersona(
        label="review",
        title_fmt="Review đầy đủ: {title} — mọi thứ cần biết trước khi xem",
        summary_fmt="Đánh giá trọn vẹn mạnh-yếu, điểm nổi bật và nên xem hay bỏ qua.",
        hook_fmt="Bạn đang phân vân có nên xem {title} không? Chain mình sẽ quyết giùm bạn.",
        rationale_fmt="Review toàn diện hợp người xem muốn quyết định nhanh theo review, CTR ổn định.",
    ),
    AnglePersona(
        label="analysis",
        title_fmt="Phân tích {title}: chủ đề, ẩn dụ và cách phim thao túng cảm xúc",
        summary_fmt="Đi sâu phân tích chủ đề, cấu trúc và ẩn dụ của phim.",
        hook_fmt="{title} không đơn thuần là giải trí — hãy cùng mổ xẻ cách nó được dựng nên.",
        rationale_fmt="Phân tích sâu thu hút người xem muốn hiểu phim, giữ chân tốt dù CTR vừa phải.",
    ),
    AnglePersona(
        label="explainer",
        title_fmt="{title} có gì đặc biệt? 5 khía cạnh nhiều người bỏ lỡ",
        summary_fmt="Các khía cạnh ít người để ý: bối cảnh, thiết kế, diễn xuất, âm nhạc, thông điệp.",
        hook_fmt="Sau khi xem {title}, bạn có để ý những chi tiết này không?",
        rationale_fmt="List-style giải thích dễ chia sẻ, phù hợp khán giả tìm trải nghiệm mới lạ.",
    ),
    AnglePersona(
        label="retrospective",
        title_fmt="Nhìn lại {title} sau {n} năm: nó vẫn đáng xem chứ?",
        summary_fmt="Góc nhìn hoài niệm, so sánh giá trị phim theo thời gian.",
        hook_fmt="Nghe nói {title} là kiệt tác — nhưng đặt lên bàn cân hôm nay thì sao?",
        rationale_fmt="Retrospective khai thác tìm kiếm 'film cũ đáng xem', evergreen và ít cạnh tranh.",
    ),
    AnglePersona(
        label="breakdown",
        title_fmt="Mổ xẻ {title}: từng phân cảnh giải thích vì sao nó hay",
        summary_fmt="Breakdown chi tiết các phân cảnh then chốt và kỹ thuật làm nên chúng.",
        hook_fmt="Đây là đoạn quay khiến {title} trở thành kinh điển — cùng xem vì sao.",
        rationale_fmt="Breakdown hợp khán giả cảnh phim, xem dài được nhiều và dễ đề xuất thuật toán.",
    ),
    AnglePersona(
        label="commentary",
        title_fmt="Bình luận {title}: thật ra phim đang nói về điều này",
        summary_fmt="Bình luận thẳng thắn về thông điệp, tranh cãi và kỳ vọng của khán giả.",
        hook_fmt="Nhiều người xem {title} để giải trí, nhưng có một tầng nghĩa khác đang ẩn mình.",
        rationale_fmt="Commentary mang tính luận chiến, tăng comment/engagement mạnh.",
    ),
    AnglePersona(
        label="comparison",
        title_fmt="So sánh {title} với bản chuyển thể/sequel — bên nào xứng đáng hơn?",
        summary_fmt="So sánh theo nội dung, diễn xuất, hình ảnh và tác động.",
        hook_fmt="{title} không xứng đáng với điểm số nó nhận được? Đặt lên bàn cân thử.",
        rationale_fmt="Comparison giải quyết tìm kiếm so sánh, dễ lên top từ khóa dài.",
    ),
    AnglePersona(
        label="list",
        title_fmt="Top {n} phong cảnh/chi tiết đáng nhớ nhất trong {title}",
        summary_fmt="Danh sách khoảnh khắc đáng nhớ, dễ tạo thumbnail và cắt ngắn để quảng bá.",
        hook_fmt="Nếu chỉ được giữ lại {n} khoảnh khắc của {title}, mình sẽ chọn những cái này.",
        rationale_fmt="List thường CTR cao, dễ làm clip dọc cho Shorts.",
    ),
    AnglePersona(
        label="video_essay",
        title_fmt="Video essay: {title} như một bài học viết kịch bản",
        summary_fmt="Phân tích phim như tác phẩm học thuật quy mô nhỏ, có cấu trúc luận điểm.",
        hook_fmt="{title} đang dạy nhà làm phim cách viết kịch bản hay — không lời thoại vẫn truyền tải.",
        rationale_fmt="Video essay tạo chỗ đứng riêng, khán giả trung thành cao dù volume khóscale.",
    ),
    AnglePersona(
        label="timeline",
        title_fmt="Toàn bộ dòng thời gian trong {title} được giải thích rõ ràng",
        summary_fmt="Sắp xếp timeline theo thứ tự, giải thích các nhánh thời gian và mẹo theo dõi.",
        hook_fmt="{title} có dòng thời gian rối — đây là cách xem nó theo đúng trật tự.",
        rationale_fmt="Timeline phim khó theo dõi luôn có nhu cầu tìm kiếm ổn định, ít cạnh tranh.",
    ),
]