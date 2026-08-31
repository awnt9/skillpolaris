from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.config import Settings
from pipeline.schemas.extract import SourcePolicy
from pipeline.tasks.extract.sources.adzuna import AdzunaExtractor
from pipeline.tasks.extract.sources.arbeitnow import ArbeitnowExtractor
from pipeline.tasks.extract.sources.ashby import AshbyExtractor
from pipeline.tasks.extract.sources.base import AtsExtractor, DetailExtractor, FeedExtractor
from pipeline.tasks.extract.sources.bundesagentur import BundesagenturExtractor
from pipeline.tasks.extract.sources.france_travail import FranceTravailExtractor
from pipeline.tasks.extract.sources.greenhouse import GreenhouseExtractor
from pipeline.tasks.extract.sources.himalayas import HimalayasExtractor
from pipeline.tasks.extract.sources.jobicy import JobicyExtractor
from pipeline.tasks.extract.sources.landing_jobs import LandingJobsExtractor
from pipeline.tasks.extract.sources.lever import LeverExtractor
from pipeline.tasks.extract.sources.recruitee import RecruiteeExtractor
from pipeline.tasks.extract.sources.remoteok import RemoteOkExtractor
from pipeline.tasks.extract.sources.remotive import RemotiveExtractor
from pipeline.tasks.extract.sources.smartrecruiters import SmartRecruitersExtractor
from pipeline.tasks.extract.sources.the_muse import TheMuseExtractor
from pipeline.tasks.extract.sources.weworkremotely import WeWorkRemotelyExtractor
from pipeline.tasks.extract.sources.workable import WorkableExtractor


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
    bundesagentur = BundesagenturExtractor(configuration=configuration)

    remoteok = RemoteOkExtractor(configuration=configuration)
    remotive = RemotiveExtractor(configuration=configuration)
    arbeitnow = ArbeitnowExtractor(configuration=configuration)
    himalayas = HimalayasExtractor(configuration=configuration)
    jobicy = JobicyExtractor(configuration=configuration)
    landing_jobs = LandingJobsExtractor(configuration=configuration)
    the_muse = TheMuseExtractor(configuration=configuration)
    weworkremotely = WeWorkRemotelyExtractor(configuration=configuration)
    adzuna = AdzunaExtractor(configuration=configuration)

    greenhouse = GreenhouseExtractor(configuration=configuration)
    lever = LeverExtractor(configuration=configuration)
    ashby = AshbyExtractor(configuration=configuration)
    recruitee = RecruiteeExtractor(configuration=configuration)
    workable = WorkableExtractor(configuration=configuration)
    smartrecruiters = SmartRecruitersExtractor(configuration=configuration)

    return ExtractorRegistry(
        detail={
            bundesagentur.source_name: bundesagentur,
        },
        feed={
            france_travail.source_name: france_travail,
            remoteok.source_name: remoteok,
            remotive.source_name: remotive,
            arbeitnow.source_name: arbeitnow,
            himalayas.source_name: himalayas,
            jobicy.source_name: jobicy,
            landing_jobs.source_name: landing_jobs,
            the_muse.source_name: the_muse,
            weworkremotely.source_name: weworkremotely,
            adzuna.source_name: adzuna,
        },
        ats={
            greenhouse.source_name: greenhouse,
            lever.source_name: lever,
            ashby.source_name: ashby,
            recruitee.source_name: recruitee,
            workable.source_name: workable,
            smartrecruiters.source_name: smartrecruiters,
        },
        policies={
            france_travail.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            bundesagentur.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            remoteok.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            remotive.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            arbeitnow.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            himalayas.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            jobicy.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            landing_jobs.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            the_muse.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            weworkremotely.source_name: SourcePolicy(
                min_interval_seconds=2.0,
                max_retries=2,
            ),
            adzuna.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            greenhouse.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            lever.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            ashby.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            recruitee.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            workable.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
            smartrecruiters.source_name: SourcePolicy(
                min_interval_seconds=1.0,
                max_retries=2,
            ),
        },
    )
