from app.core.config import settings
from app.services.providers import (
    OfflineAnalyticsProvider,
    OfflineAngleProvider,
    OfflineAssetProvider,
    OfflineCopyrightProvider,
    OfflineOpportunityProvider,
    OfflinePublishingProvider,
    OfflineQAProvider,
    OfflineRenderProvider,
    OfflineResearchProvider,
    OfflineScriptProvider,
    OfflineSubtitleProvider,
    OfflineTimelineProvider,
    OfflineVisualPlannerProvider,
    OfflineVoiceProvider,
)


def get_research_provider() -> OfflineResearchProvider:
    if settings.research_provider.lower() == "offline":
        return OfflineResearchProvider()
    return OfflineResearchProvider()


def get_opportunity_provider(weights: dict | None = None) -> OfflineOpportunityProvider:
    if settings.opportunity_provider.lower() == "offline":
        return OfflineOpportunityProvider(weights=weights)
    return OfflineOpportunityProvider(weights=weights)


def get_angle_provider() -> OfflineAngleProvider:
    if settings.angle_provider.lower() == "offline":
        return OfflineAngleProvider()
    return OfflineAngleProvider()


def get_script_provider() -> OfflineScriptProvider:
    if settings.script_provider.lower() == "offline":
        return OfflineScriptProvider()
    return OfflineScriptProvider()


def get_voice_provider() -> OfflineVoiceProvider:
    if settings.voice_provider.lower() == "offline":
        return OfflineVoiceProvider()
    return OfflineVoiceProvider()


def get_timeline_provider() -> OfflineTimelineProvider:
    if settings.timeline_provider.lower() == "offline":
        return OfflineTimelineProvider()
    return OfflineTimelineProvider()


def get_visual_planner_provider() -> OfflineVisualPlannerProvider:
    if settings.visual_provider.lower() == "offline":
        return OfflineVisualPlannerProvider()
    return OfflineVisualPlannerProvider()


def get_asset_provider() -> OfflineAssetProvider:
    if settings.asset_provider.lower() == "offline":
        return OfflineAssetProvider()
    return OfflineAssetProvider()


def get_copyright_provider() -> OfflineCopyrightProvider:
    if settings.copyright_provider.lower() == "offline":
        return OfflineCopyrightProvider()
    return OfflineCopyrightProvider()


def get_render_provider() -> OfflineRenderProvider:
    if settings.render_provider.lower() == "offline":
        return OfflineRenderProvider()
    return OfflineRenderProvider()


def get_subtitle_provider() -> OfflineSubtitleProvider:
    if settings.subtitle_provider.lower() == "offline":
        return OfflineSubtitleProvider()
    return OfflineSubtitleProvider()


def get_qa_provider() -> OfflineQAProvider:
    if settings.qa_provider.lower() == "offline":
        return OfflineQAProvider()
    return OfflineQAProvider()


def get_publishing_provider() -> OfflinePublishingProvider:
    if settings.youtube_provider.lower() == "offline":
        return OfflinePublishingProvider()
    return OfflinePublishingProvider()


def get_analytics_provider() -> OfflineAnalyticsProvider:
    if settings.analytics_provider.lower() == "offline":
        return OfflineAnalyticsProvider()
    return OfflineAnalyticsProvider()