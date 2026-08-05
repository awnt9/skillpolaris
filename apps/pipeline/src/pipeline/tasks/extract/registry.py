from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.config import Settings
from pipeline.schemas.extract import SourcePolicy
from pipeline.tasks.sources.base import AtsExtractor, DetailExtractor, FeedExtractor
from pipeline.tasks.sources.france_travail import FranceTravailExtractor


@dataclass
class ExtractorRegistry:
    detail: dict[str, DetailExtractor] = field(default_factory=dict)
    feed: dict[str, FeedExtractor] = field(default_factory=dict)
    ats: dict[str, AtsExtractor] = field(default_factory=dict)
    policies: dict[str, SourcePolicy] = field(default_factory=dict)

    def detail_sources(self) -> list[str]:
        return list(self.detail.keys())

    def feed_sources(self) -> list[str]:
        return list(self.feed.keys())

    def ats_sources(self) -> list[str]:
        return list(self.ats.keys())

    def policy_for(self, source: str) -> SourcePolicy:
        return self.policies.get(source, SourcePolicy())


def build_extractor_registry(configuration: Settings) -> ExtractorRegistry:
    france_travail = FranceTravailExtractor(configuration=configuration)

    return ExtractorRegistry(
        detail={france_travail.source_name: france_travail},
        feed={},
        ats={},
        policies={
            france_travail.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
        },
    )
