from typing import Optional

from pydantic import BaseModel, Field


# ---------- Visual plan (docs/09: Visual Planner) ----------
SECTION_ASSET_MAP: dict[str, dict] = {
    "hook": {
        "purpose": "Mở đầu gây chú ý: dramatic scene hoặc montage",
        "asset_types": ["ai_image", "graphics"],
        "duration_s": 4.0,
        "notes": "Hình ảnh mạnh, chuyển cảnh nhanh.",
    },
    "thesis": {
        "purpose": "Trình bày luận điểm chính",
        "asset_types": ["ai_image", "graphics", "text_overlay"],
        "duration_s": 5.0,
        "notes": "Kết hợp text + hình ảnh hỗ trợ.",
    },
    "context": {
        "purpose": "Thiết lập bối cảnh phim",
        "asset_types": ["ai_image", "stock_footage"],
        "duration_s": 8.0,
        "notes": "Poster hoặc b-roll không vi phạm bản quyền.",
    },
    "analysis": {
        "purpose": "Minh hoạ phân tích chuyên sâu",
        "asset_types": ["graphics", "chart", "ai_image"],
        "duration_s": 12.0,
        "notes": "Data visualization hoặc annotation.",
    },
    "evidence": {
        "purpose": "Trích dẫn bằng chứng cụ thể",
        "asset_types": ["ai_image", "stock_footage", "graphics"],
        "duration_s": 8.0,
        "notes": "Chỉ dùng footage-transformed hoặc poster promo.",
    },
    "character_theme": {
        "purpose": "Giới thiệu nhân vật / chủ đề",
        "asset_types": ["ai_image", "poster"],
        "duration_s": 8.0,
        "notes": "Sử dụng poster chính thức hoặc portrait.",
    },
    "critique": {
        "purpose": "So sánh ủng hộ/phản đối kèm ví dụ minh hoạ",
        "asset_types": ["graphics", "ai_image", "comparison_chart"],
        "duration_s": 7.0,
        "notes": "Layout so sánh, biểu đồ điểm.",
    },
    "conclusion": {
        "purpose": "Tổng kết — hình ảnh khép lại",
        "asset_types": ["ai_image", "graphics"],
        "duration_s": 4.0,
        "notes": "Poster hoặc hình ảnh tĩnh kết.",
    },
    "cta": {
        "purpose": "Kêu gọi đăng ký + kết nối",
        "asset_types": ["graphics", "text_overlay"],
        "duration_s": 3.0,
        "notes": "Subscribe button animation graphic.",
    },
}


class VisualPlanSegment(BaseModel):
    segment_index: int = Field(ge=0)
    section: str
    purpose: str
    asset_types: list[str] = Field(default_factory=list)
    duration_s: float = Field(default=5.0, ge=0)
    notes: Optional[str] = None


class VisualPlanMetadata(BaseModel):
    strategy_version: str = "v1"
    total_planned_duration_s: float = 0.0
    segments: list[VisualPlanSegment] = Field(default_factory=list)


# ---------- Asset DTOs ----------
class AssetCreate(BaseModel):
    segment_index: int = Field(ge=0)
    asset_type: str
    title: str | None = None
    source: str | None = None
    source_url: str | None = None
    license: str | None = None
    commercial_use: str = Field(default="unknown", pattern=r"^(yes|no|unknown)$")
    owner_name: str | None = None
    acquisition_time: float | None = Field(default=None, ge=0)
    usage_context: str | None = None
    duration_s: float | None = Field(default=None, ge=0)
    transformations: list[str] | None = None
    risk_score: float | None = Field(default=None, ge=0, le=1)
    file_url: str | None = None
    thumbnail_url: str | None = None


class AssetOut(BaseModel):
    id: int
    script_id: int
    segment_index: int
    asset_type: str
    title: str | None = None
    source: str | None = None
    source_url: str | None = None
    license: str | None = None
    commercial_use: str | None = None
    owner_name: str | None = None
    acquisition_time: float | None = None
    usage_context: str | None = None
    duration_s: float | None = None
    transformations: list | None = None
    risk_score: float | None = None
    file_url: str | None = None
    thumbnail_url: str | None = None


class AssetSearchRequest(BaseModel):
    script_id: int
    segment_index: int | None = Field(default=None, description="Tìm kiếm segment cụ thể; None = tất cả")


class AssetGenerateRequest(BaseModel):
    script_id: int
    segment_index: int | None = Field(default=None, description="Tạo asset cho segment cụ thể; None = tất cả")


class AssetActionResult(BaseModel):
    script_id: int
    assets_created: int = 0
    assets: list[AssetOut] = Field(default_factory=list)


# ---------- Copyright ----------
class CopyrightReviewInput(BaseModel):
    asset_id: int
    duration_s: float | None = None
    source: str | None = None
    commercial_use: str = "unknown"
    license: str | None = None


class CopyrightReviewOutput(BaseModel):
    asset_id: int
    risk_level: str  # low / medium / high
    duration_warning: bool = False
    human_review_required: bool = False
    policy_notes: list[str] = Field(default_factory=list)
    decision: str = "pending"
    notes: str | None = None


class CopyrightEvaluateRequest(BaseModel):
    script_id: int
    asset_ids: list[int] = Field(default_factory=list, description="IDs cụ thể; rỗng =evaluate tất cả asset của script")


class CopyrightEvaluateResult(BaseModel):
    script_id: int
    reviews: list[CopyrightReviewOutput] = Field(default_factory=list)
    human_review_count: int = 0
    blocked_count: int = 0