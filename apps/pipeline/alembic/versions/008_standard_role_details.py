"""Standard role details: description + synonyms columns on standard_roles.

Backfills the 18 roles seeded in 007_open_role_taxonomy with a one-sentence
description and a starter synonym list, grounded in O*NET-SOC, SFIA, the 2025
Stack Overflow Developer Survey, LinkedIn's 2025 Jobs on the Rise report, the
Google SRE book, and Fournier's "The Manager's Path" -- see
skillpolaris-dissertation/agent_context/DESIGN.md, section
"Standard-role vocabulary provenance", for the source-by-role table.

Revision ID: 008_standard_role_details
Revises: 007_open_role_taxonomy
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008_standard_role_details"
down_revision: str | None = "007_open_role_taxonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# name -> (description, starter synonyms)
_ROLE_DETAILS: dict[str, tuple[str, list[str]]] = {
    "Software Engineer": (
        "General software engineering role spanning design, implementation, and "
        "maintenance of applications; the catch-all when a posting does not clearly "
        "fit a more specific role.",
        ["Software Developer", "Programmer", "Application Developer", "Applications Engineer"],
    ),
    "Backend Developer": (
        "Builds and maintains server-side application logic, APIs, and business "
        "services that power an application.",
        ["Back-End Developer", "Back End Developer", "Server-Side Developer", "API Developer"],
    ),
    "Frontend Developer": (
        "Builds the client-side user interface and interactive experience of web or "
        "software applications.",
        ["Front-End Developer", "Front End Developer", "UI Developer", "User Interface Developer"],
    ),
    "Full Stack Developer": (
        "Works across both the client-facing and server-side layers of an "
        "application, from UI to data storage.",
        ["Full-Stack Developer", "Fullstack Developer", "Full Stack Engineer"],
    ),
    "Mobile Developer": (
        "Builds native or cross-platform applications for smartphones and tablets.",
        ["Mobile App Developer", "iOS Developer", "Android Developer", "Mobile App Engineer"],
    ),
    "Data Engineer": (
        "Builds and maintains the pipelines and infrastructure that collect, "
        "transform, and store data for analytics and machine learning.",
        ["Data Pipeline Engineer", "ETL Engineer", "Big Data Engineer"],
    ),
    "Data Scientist": (
        "Analyzes data and builds statistical or machine-learning models to extract "
        "insights and support decisions.",
        ["Data Research Scientist", "Applied Scientist", "Research Data Scientist"],
    ),
    "Machine Learning Engineer": (
        "Designs, trains, and deploys machine-learning and AI models into production "
        "systems.",
        ["ML Engineer", "AI Engineer", "Applied Machine Learning Engineer"],
    ),
    "DevOps Engineer": (
        "Automates build, deployment, and infrastructure workflows to enable "
        "frequent, reliable software delivery.",
        ["DevOps Specialist", "Build and Release Engineer", "CI/CD Engineer"],
    ),
    "Site Reliability Engineer": (
        "Applies software-engineering practices to operations, focusing on system "
        "reliability, scalability, and incident response.",
        ["SRE", "Reliability Engineer", "Production Engineer"],
    ),
    "Platform Engineer": (
        "Builds and operates the internal developer platform and shared "
        "infrastructure that other engineering teams build on top of.",
        [
            "Internal Platform Engineer",
            "Developer Platform Engineer",
            "Infrastructure Platform Engineer",
        ],
    ),
    "Cloud Engineer": (
        "Designs, deploys, and manages applications and infrastructure on cloud "
        "platforms such as AWS, Azure, or GCP.",
        ["Cloud Infrastructure Engineer", "Cloud Solutions Engineer", "Cloud Systems Engineer"],
    ),
    "Security Engineer": (
        "Designs and implements measures to protect software systems, networks, and "
        "data from security threats.",
        [
            "Information Security Engineer",
            "Application Security Engineer",
            "Cybersecurity Engineer",
        ],
    ),
    "QA Automation Engineer": (
        "Designs and maintains automated test suites and quality-assurance processes "
        "for software products.",
        ["Test Automation Engineer", "SDET", "Software Quality Assurance Engineer", "QA Engineer"],
    ),
    "Embedded Software Engineer": (
        "Develops software that runs on embedded systems and hardware devices under "
        "real-time or resource constraints.",
        ["Embedded Systems Engineer", "Embedded Systems Developer", "Firmware Engineer"],
    ),
    "Database Administrator": (
        "Installs, configures, monitors, and maintains databases, ensuring their "
        "performance, availability, and security.",
        ["DBA", "Database Manager", "Data Administrator"],
    ),
    "Technical Lead": (
        "Senior engineer who guides the technical direction and coordinates the work "
        "of a development team while still writing code.",
        ["Tech Lead", "Lead Developer", "Lead Engineer", "Team Lead"],
    ),
    "Engineering Manager": (
        "Manages a team of engineers, owning people development, delivery, and "
        "technical strategy for their team.",
        ["Engineering Team Manager", "Software Engineering Manager", "Development Manager"],
    ),
}


def upgrade() -> None:
    op.add_column("standard_roles", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "standard_roles",
        sa.Column(
            "synonyms",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    connection = op.get_bind()
    standard_roles = sa.table(
        "standard_roles",
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("synonyms", JSONB()),
    )
    for name, (description, synonyms) in _ROLE_DETAILS.items():
        connection.execute(
            standard_roles.update()
            .where(sa.func.lower(standard_roles.c.name) == name.lower())
            .values(description=description, synonyms=synonyms)
        )


def downgrade() -> None:
    op.drop_column("standard_roles", "synonyms")
    op.drop_column("standard_roles", "description")
