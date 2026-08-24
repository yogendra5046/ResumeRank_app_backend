"""Infrastructure: ESCO v1.1.1 skill taxonomy loader.

Loads the full ESCO skill graph from a local JSON file (3000+ skills).
In CI, a fixture generator creates a representative subset.

ESCO JSON format expected:
  {
    "skills": [
      {
        "uri": "http://data.europa.eu/esco/skill/...",
        "preferredLabel": {"en": "Python programming"},
        "altLabels": {"en": ["python", "Python scripting"]},
        "broaderUri": ["http://data.europa.eu/esco/skill/parent-uri"]
      },
      ...
    ]
  }
"""
from __future__ import annotations

import gzip
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_DEFAULT_ESCO_PATH = Path(__file__).parent / "data" / "esco_skills.json.gz"


@dataclass(frozen=True, slots=True)
class EscoSkill:
    """Single ESCO skill node."""

    uri: str
    preferred_label: str
    alt_labels: frozenset[str]
    broader_uris: tuple[str, ...]


@dataclass
class EscoTaxonomy:
    """Loaded taxonomy – indexed for fast lookup."""

    skills_by_uri: dict[str, EscoSkill] = field(default_factory=dict)
    # Inverted index: lowercase label → uri (covers preferred + alt labels)
    label_to_uri: dict[str, str] = field(default_factory=dict)

    @property
    def skill_count(self) -> int:
        return len(self.skills_by_uri)

    def find_uri_for_label(self, label: str) -> str | None:
        return self.label_to_uri.get(label.lower().strip())


def load_esco_taxonomy(path: Path = _DEFAULT_ESCO_PATH) -> EscoTaxonomy:
    """Load ESCO JSON (.gz or plain) into an indexed EscoTaxonomy."""
    logger.info("esco_loading", path=str(path))

    raw: bytes
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as fh:
            raw = fh.read()
    else:
        raw = path.read_bytes()

    data: dict[str, Any] = json.loads(raw)
    taxonomy = EscoTaxonomy()

    for entry in data.get("skills", []):
        uri: str = entry["uri"]
        en_label = entry.get("preferredLabel", {}).get("en", "")
        if not en_label:
            continue

        alt_en: list[str] = entry.get("altLabels", {}).get("en", [])
        broader: list[str] = entry.get("broaderUri", [])

        skill = EscoSkill(
            uri=uri,
            preferred_label=en_label,
            alt_labels=frozenset(a.lower() for a in alt_en),
            broader_uris=tuple(broader),
        )
        taxonomy.skills_by_uri[uri] = skill

        # Index preferred label
        taxonomy.label_to_uri[en_label.lower()] = uri
        # Index all alt labels
        for alt in alt_en:
            taxonomy.label_to_uri[alt.lower()] = uri

    logger.info("esco_loaded", skill_count=taxonomy.skill_count)
    if taxonomy.skill_count < 3000:
        logger.warning(
            "esco_skill_count_below_minimum",
            count=taxonomy.skill_count,
            required=3000,
        )

    return taxonomy
