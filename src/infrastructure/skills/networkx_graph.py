"""Infrastructure: NetworkX skill graph – implements SkillGraphPort.

Builds a directed graph from ESCO taxonomy where edges represent
broader→narrower skill relationships. Matching traverses up to 2 hops
for partial credit, e.g. "Python" → "scripting" when JD asks for
"software development" (parent concept).
"""
from __future__ import annotations

import asyncio
import functools
import re
from concurrent.futures import ThreadPoolExecutor

import networkx as nx
import structlog

from src.domain.ports.skill_graph import SkillGraphPort, SkillMatchResult
from src.infrastructure.skills.esco_loader import EscoTaxonomy

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="graph-worker")
_MAX_HOPS: int = 2
_PARTIAL_CREDIT: float = 0.5   # credit per hop above direct match


def _tokenise(text: str) -> set[str]:
    """Extract candidate skill tokens (1–3 word n-grams, lowercased)."""
    words = re.findall(r"\b[a-z][a-z0-9+#.\-]*\b", text.lower())
    tokens: set[str] = set(words)
    for i in range(len(words) - 1):
        tokens.add(f"{words[i]} {words[i+1]}")
    for i in range(len(words) - 2):
        tokens.add(f"{words[i]} {words[i+1]} {words[i+2]}")
    return tokens


class NetworkXSkillGraph(SkillGraphPort):
    """Directed skill graph built from ESCO taxonomy."""

    def __init__(self, taxonomy: EscoTaxonomy) -> None:
        self._taxonomy = taxonomy
        self._graph: nx.DiGraph = self._build_graph()

    @property
    def skill_count(self) -> int:
        return self._taxonomy.skill_count

    def _build_graph(self) -> nx.DiGraph:
        g: nx.DiGraph = nx.DiGraph()
        for uri, skill in self._taxonomy.skills_by_uri.items():
            g.add_node(uri, label=skill.preferred_label)
            for broader_uri in skill.broader_uris:
                g.add_edge(broader_uri, uri)  # broader → narrower
        logger.info("skill_graph_built", nodes=g.number_of_nodes(), edges=g.number_of_edges())
        return g

    async def match(self, resume_text: str, jd_text: str) -> SkillMatchResult:
        loop = asyncio.get_running_loop()
        result: SkillMatchResult = await loop.run_in_executor(
            _EXECUTOR,
            functools.partial(self._match_sync, resume_text, jd_text),
        )
        return result

    def _match_sync(self, resume_text: str, jd_text: str) -> SkillMatchResult:
        resume_tokens = _tokenise(resume_text)
        jd_tokens = _tokenise(jd_text)

        # Resolve token → ESCO URI
        resume_uris: set[str] = self._tokens_to_uris(resume_tokens)
        jd_uris: set[str] = self._tokens_to_uris(jd_tokens)

        if not jd_uris:
            return SkillMatchResult(matched=(), missing=(), graph_weight=0.0)

        total_weight = 0.0
        matched_labels: list[str] = []
        missing_labels: list[str] = []

        for jd_uri in jd_uris:
            skill = self._taxonomy.skills_by_uri.get(jd_uri)
            label = skill.preferred_label if skill else jd_uri

            if jd_uri in resume_uris:
                total_weight += 1.0
                matched_labels.append(label)
            else:
                # Try graph traversal up to _MAX_HOPS
                credit = self._graph_credit(jd_uri, resume_uris)
                if credit > 0:
                    total_weight += credit
                    matched_labels.append(f"{label} (~partial)")
                else:
                    missing_labels.append(label)

        graph_weight = min(total_weight / len(jd_uris), 1.0)

        return SkillMatchResult(
            matched=tuple(matched_labels),
            missing=tuple(missing_labels),
            graph_weight=round(graph_weight, 4),
        )

    def _tokens_to_uris(self, tokens: set[str]) -> set[str]:
        uris: set[str] = set()
        for token in tokens:
            uri = self._taxonomy.find_uri_for_label(token)
            if uri:
                uris.add(uri)
        return uris

    def _graph_credit(self, target_uri: str, candidate_uris: set[str]) -> float:
        """Walk ancestors up to _MAX_HOPS; return partial credit if found."""
        visited: set[str] = set()
        frontier: set[str] = {target_uri}
        for hop in range(1, _MAX_HOPS + 1):
            next_frontier: set[str] = set()
            for uri in frontier:
                for predecessor in self._graph.predecessors(uri):
                    if predecessor in candidate_uris:
                        return _PARTIAL_CREDIT / hop
                    if predecessor not in visited:
                        next_frontier.add(predecessor)
                        visited.add(predecessor)
            frontier = next_frontier
        return 0.0
