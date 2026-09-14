from app.core.config import settings
from app.services.providers import (
    OfflineAngleProvider,
    OfflineOpportunityProvider,
    OfflineResearchProvider,
    OfflineScriptProvider,
    OfflineTimelineProvider,
    OfflineVoiceProvider,
)


def get_research_provider() -> OfflineResearchProvider:
    if settings.research_provider.lower() == "offline":
        return OfflineResearchProvider()
    return OfflineResearchProvider()


def get_opportunity_provider() -> OfflineOpportunityProvider:
    if settings.opportunity_provider.lower() == "offline":
        return OfflineOpportunityProvider()
    return OfflineOpportunityProvider()


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