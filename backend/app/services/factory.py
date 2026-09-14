from app.core.config import settings
from app.services.providers import (
    OfflineAngleProvider,
    OfflineOpportunityProvider,
    OfflineResearchProvider,
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