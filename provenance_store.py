"""Semantic Provenance Store — Priority 7 provenance infrastructure.

Ensures every code is traceable back to source text through the full chain:
  Source Text → L1 Anchor → L2 Theme → L3 Theory

Four provenance types:
  1. AnchorProvenance — L1 anchor → source sentence traceability
  2. ThemeProvenance — L2 theme → L1 anchor support evidence
  3. TheoryProvenance — L3 theory → L2 → L1 → source full chain
  4. CompressionProvenance — semantic merge audit trail

Usage:
    from provenance_store import ProvenanceStore
    ps = ProvenanceStore()
    ps.record_anchor("客流聚集", source_text="...", grounding_score=0.91, ...)
    ps.record_theme("空间流量机制", supported_by=["客流聚集", "游客导流"])
    ps.record_theory("文化商业共生机制", supported_by=["空间流量机制", ...])
    ps.save("data/provenance.json")
"""

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("provenance_store")


# ── Individual provenance record types ──────────────────────────────────

class AnchorProvenance:
    """L1 Anchor → Source Sentence traceability record."""

    __slots__ = (
        "anchor", "source_text", "keywords", "keyword_bridge",
        "grounding_score", "jump_distance", "jump_level",
        "polarity_violation", "polarity_reason",
        "sentence_index", "source_file", "semantic_similarity",
        "candidate_rank", "verdict",
    )

    def __init__(self, anchor: str, source_text: str, **kwargs):
        self.anchor = anchor
        self.source_text = source_text
        self.keywords = kwargs.get("keywords", [])
        self.keyword_bridge = kwargs.get("keyword_bridge", [])
        self.grounding_score = kwargs.get("grounding_score", 0.0)
        self.jump_distance = kwargs.get("jump_distance", 0.0)
        self.jump_level = kwargs.get("jump_level", "unknown")
        self.polarity_violation = kwargs.get("polarity_violation", False)
        self.polarity_reason = kwargs.get("polarity_reason", "ok")
        self.sentence_index = kwargs.get("sentence_index", -1)
        self.source_file = kwargs.get("source_file", "")
        self.semantic_similarity = kwargs.get("semantic_similarity")
        self.candidate_rank = kwargs.get("candidate_rank")
        self.verdict = kwargs.get("verdict", "")

    def to_dict(self) -> dict:
        d = {
            "anchor": self.anchor,
            "source_text": self.source_text,
            "keywords": self.keywords,
            "keyword_bridge": self.keyword_bridge,
            "grounding_score": self.grounding_score,
            "jump_distance": self.jump_distance,
            "jump_level": self.jump_level,
            "polarity_violation": self.polarity_violation,
            "polarity_reason": self.polarity_reason,
            "sentence_index": self.sentence_index,
            "source_file": self.source_file,
        }
        if self.semantic_similarity is not None:
            d["semantic_similarity"] = self.semantic_similarity
        if self.candidate_rank is not None:
            d["candidate_rank"] = self.candidate_rank
        if self.verdict:
            d["verdict"] = self.verdict
        return d

    @classmethod
    def from_grounding_verdict(cls, anchor: str, source_text: str,
                                grounding: dict, provenance: dict = None) -> "AnchorProvenance":
        """Create from GroundingChecker.grounding_verdict() output."""
        return cls(
            anchor=anchor,
            source_text=source_text,
            grounding_score=grounding.get("grounding_score", 0.0),
            jump_distance=grounding.get("jump_distance", 0.0),
            jump_level=grounding.get("jump_level", "unknown"),
            polarity_violation=grounding.get("polarity_violation", False),
            polarity_reason=grounding.get("polarity_reason", "ok"),
            keywords=provenance.get("source_keywords", []) if provenance else [],
            keyword_bridge=provenance.get("keyword_bridge", []) if provenance else [],
            semantic_similarity=provenance.get("semantic_similarity") if provenance else None,
            candidate_rank=provenance.get("candidate_rank") if provenance else None,
            verdict=provenance.get("verdict", "") if provenance else "",
        )


class ThemeProvenance:
    """L2 Theme → L1 Anchor support evidence."""

    __slots__ = ("theme", "supported_by", "anchor_count", "coverage_ratio")

    def __init__(self, theme: str, supported_by: List[str], **kwargs):
        self.theme = theme
        self.supported_by = list(supported_by)
        self.anchor_count = len(self.supported_by)
        self.coverage_ratio = kwargs.get("coverage_ratio", 1.0)

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "supported_by": self.supported_by,
            "anchor_count": self.anchor_count,
            "coverage_ratio": self.coverage_ratio,
        }


class TheoryProvenance:
    """L3 Theory → L2 → L1 → Source full chain."""

    __slots__ = ("theory", "supported_by_themes", "theme_count",
                 "total_anchors", "total_sentences")

    def __init__(self, theory: str, supported_by_themes: List[str], **kwargs):
        self.theory = theory
        self.supported_by_themes = list(supported_by_themes)
        self.theme_count = len(self.supported_by_themes)
        self.total_anchors = kwargs.get("total_anchors", 0)
        self.total_sentences = kwargs.get("total_sentences", 0)

    def to_dict(self) -> dict:
        return {
            "theory": self.theory,
            "supported_by_themes": self.supported_by_themes,
            "theme_count": self.theme_count,
            "total_anchors": self.total_anchors,
            "total_sentences": self.total_sentences,
        }


class CompressionProvenance:
    """Semantic merge audit trail."""

    __slots__ = ("merged_into", "merged_items", "reason", "timestamp")

    def __init__(self, merged_into: str, merged_items: List[str], **kwargs):
        self.merged_into = merged_into
        self.merged_items = list(merged_items)
        self.reason = kwargs.get("reason", {})
        self.timestamp = kwargs.get("timestamp", datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "merged_into": self.merged_into,
            "merged_items": self.merged_items,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


# ── Central provenance store ────────────────────────────────────────────

class ProvenanceStore:
    """Central registry for all provenance data across the coding pipeline.

    Collects anchor-level, theme-level, theory-level, and compression
    provenance. Supports full-chain querying and persistent storage.
    """

    def __init__(self):
        # Anchor provenance: anchor_name → list of AnchorProvenance records
        self._anchor_records: Dict[str, List[AnchorProvenance]] = defaultdict(list)
        # Theme provenance: theme_name → ThemeProvenance
        self._theme_records: Dict[str, ThemeProvenance] = {}
        # Theory provenance: theory_name → TheoryProvenance
        self._theory_records: Dict[str, TheoryProvenance] = {}
        # Compression provenance: list of CompressionProvenance
        self._compression_records: List[CompressionProvenance] = []
        # Fast lookup: source_text → anchor
        self._source_to_anchor: Dict[str, str] = {}
        # Metadata
        self._total_sentences = 0
        self._created_at = datetime.now().isoformat()

    # ── Recording ────────────────────────────────────────────────────

    def record_anchor(self, anchor: str, source_text: str, **kwargs) -> AnchorProvenance:
        """Record an L1 anchor provenance entry."""
        record = AnchorProvenance(anchor, source_text, **kwargs)
        self._anchor_records[anchor].append(record)
        self._source_to_anchor[source_text] = anchor
        self._total_sentences += 1
        return record

    def record_anchor_from_trace(self, trace: dict, sentence_index: int = -1,
                                  source_file: str = "") -> Optional[AnchorProvenance]:
        """Record anchor provenance from a build_first_level_candidate_trace dict."""
        anchor = trace.get("selected_candidate", "")
        normalized = trace.get("normalized", "")
        grounding = trace.get("grounding")
        provenance = trace.get("provenance")

        if not anchor or not normalized:
            return None

        if grounding and isinstance(grounding, dict):
            record = AnchorProvenance.from_grounding_verdict(
                anchor, normalized, grounding, provenance)
        elif provenance and isinstance(provenance, dict):
            record = AnchorProvenance(
                anchor=anchor,
                source_text=normalized,
                keywords=provenance.get("source_keywords", []),
                keyword_bridge=provenance.get("keyword_bridge", []),
                semantic_similarity=provenance.get("semantic_similarity"),
                candidate_rank=provenance.get("candidate_rank"),
                verdict=provenance.get("verdict", ""),
            )
        else:
            record = AnchorProvenance(anchor=anchor, source_text=normalized)

        record.sentence_index = sentence_index
        record.source_file = source_file
        self._anchor_records[anchor].append(record)
        self._source_to_anchor[normalized] = anchor
        self._total_sentences += 1
        return record

    def record_theme(self, theme: str, supported_by: List[str], **kwargs):
        """Record an L2 theme provenance entry."""
        record = ThemeProvenance(theme, supported_by, **kwargs)
        self._theme_records[theme] = record
        return record

    def record_theory(self, theory: str, supported_by_themes: List[str], **kwargs):
        """Record an L3 theory provenance entry."""
        record = TheoryProvenance(theory, supported_by_themes, **kwargs)
        self._theory_records[theory] = record
        return record

    def record_compression(self, merged_into: str, merged_items: List[str],
                           reason: dict = None):
        """Record a compression merge for audit trail."""
        record = CompressionProvenance(
            merged_into, merged_items,
            reason=reason or {},
            timestamp=datetime.now().isoformat(),
        )
        self._compression_records.append(record)
        return record

    # ── Building hierarchy from flat data ────────────────────────────

    def build_from_coding_results(self, results: List[dict],
                                   anchor_hierarchy: Dict[str, dict] = None):
        """Build full provenance from coding test results.

        Args:
            results: List of result dicts from test_first_level_coding.py.
                     Each must have: code, original, provenance, grounding,
                     file, index.
            anchor_hierarchy: Optional {anchor: {second_category, third_category}}
                              mapping from data/anchor_hierarchy.json.
        """
        anchor_hierarchy = anchor_hierarchy or {}

        # 1. Record all anchor provenance
        for r in results:
            code = r.get("code", "")
            original = r.get("original", "")
            if not code or not original:
                continue

            grounding = r.get("grounding")
            provenance = r.get("provenance")

            record = AnchorProvenance(
                anchor=code,
                source_text=original,
                sentence_index=r.get("index", -1),
                source_file=r.get("file", ""),
            )

            if grounding and isinstance(grounding, dict):
                record.grounding_score = grounding.get("grounding_score", 0.0)
                record.jump_distance = grounding.get("jump_distance", 0.0)
                record.jump_level = grounding.get("jump_level", "unknown")
                record.polarity_violation = grounding.get("polarity_violation", False)
                record.polarity_reason = grounding.get("polarity_reason", "ok")

            if provenance and isinstance(provenance, dict):
                record.keywords = provenance.get("source_keywords", [])
                record.keyword_bridge = provenance.get("keyword_bridge", [])
                record.semantic_similarity = provenance.get("semantic_similarity")
                record.candidate_rank = provenance.get("candidate_rank")
                record.verdict = provenance.get("verdict", "")

            self._anchor_records[code].append(record)
            self._source_to_anchor[original] = code
            self._total_sentences += 1

        # 2. Build theme provenance from anchor_hierarchy
        theme_to_anchors: Dict[str, List[str]] = defaultdict(list)
        theory_to_themes: Dict[str, List[str]] = defaultdict(list)
        theory_anchor_counts: Dict[str, int] = defaultdict(int)

        for anchor_name in self._anchor_records:
            hierarchy = anchor_hierarchy.get(anchor_name, {})
            second = hierarchy.get("second_category", "")
            third = hierarchy.get("third_category", "")
            if second:
                theme_to_anchors[second].append(anchor_name)
            if third and second:
                if second not in theory_to_themes.get(third, []):
                    theory_to_themes[third].append(second)
                theory_anchor_counts[third] += len(self._anchor_records[anchor_name])

        for theme, anchors in theme_to_anchors.items():
            self.record_theme(theme, anchors)

        for theory, themes in theory_to_themes.items():
            self.record_theory(
                theory, themes,
                total_anchors=theory_anchor_counts.get(theory, 0),
                total_sentences=sum(
                    len(self._anchor_records.get(a, []))
                    for theme_name in themes
                    for a in theme_to_anchors.get(theme_name, [])
                ),
            )

        logger.info("Built provenance from %d results: %d anchors, %d themes, %d theories",
                     len(results), len(self._anchor_records),
                     len(self._theme_records), len(self._theory_records))

    # ── Querying ─────────────────────────────────────────────────────

    def get_anchor_provenance(self, anchor: str) -> List[dict]:
        """Get all source sentences that map to a given anchor."""
        records = self._anchor_records.get(anchor, [])
        return [r.to_dict() for r in records]

    def get_theme_chain(self, theme: str) -> dict:
        """Get the full L2 → L1 chain for a theme."""
        theme_record = self._theme_records.get(theme)
        if not theme_record:
            return {"theme": theme, "error": "not found"}

        chain = theme_record.to_dict()
        chain["anchor_details"] = {}
        for anchor in theme_record.supported_by:
            chain["anchor_details"][anchor] = self.get_anchor_provenance(anchor)
        return chain

    def get_theory_chain(self, theory: str) -> dict:
        """Get the full L3 → L2 → L1 → Source chain for a theory."""
        theory_record = self._theory_records.get(theory)
        if not theory_record:
            return {"theory": theory, "error": "not found"}

        chain = theory_record.to_dict()
        chain["theme_details"] = {}
        for theme in theory_record.supported_by_themes:
            chain["theme_details"][theme] = self.get_theme_chain(theme)
        return chain

    def query_full_chain(self, anchor: str = None, theme: str = None,
                         theory: str = None) -> dict:
        """Query the full provenance chain from any entry point.

        Returns the complete chain from the specified level down to source text.
        """
        if theory:
            return self.get_theory_chain(theory)
        if theme:
            return self.get_theme_chain(theme)
        if anchor:
            result = {"anchor": anchor}
            result["source_sentences"] = self.get_anchor_provenance(anchor)
            # Also find which themes/theories this anchor belongs to
            for theme_name, theme_rec in self._theme_records.items():
                if anchor in theme_rec.supported_by:
                    result["parent_theme"] = theme_name
                    for theory_name, theory_rec in self._theory_records.items():
                        if theme_name in theory_rec.supported_by_themes:
                            result["parent_theory"] = theory_name
                            break
                    break
            return result
        return {"error": "specify anchor, theme, or theory"}

    def get_compression_history(self) -> List[dict]:
        """Get all recorded compression merges."""
        return [r.to_dict() for r in self._compression_records]

    # ── Statistics ───────────────────────────────────────────────────

    def compute_stats(self) -> dict:
        """Compute provenance coverage and quality statistics."""
        total_anchors = len(self._anchor_records)
        total_sentences = self._total_sentences
        total_themes = len(self._theme_records)
        total_theories = len(self._theory_records)
        total_compressions = len(self._compression_records)

        # Grounding quality distribution
        all_gs = []
        well_grounded = 0
        for records in self._anchor_records.values():
            for r in records:
                all_gs.append(r.grounding_score)
                if r.grounding_score >= 0.60:
                    well_grounded += 1

        # Keyword bridge presence
        with_bridge = sum(
            1 for records in self._anchor_records.values()
            for r in records if r.keyword_bridge
        )

        # Jump level distribution
        jump_dist = defaultdict(int)
        for records in self._anchor_records.values():
            for r in records:
                jump_dist[r.jump_level] += 1

        # Theme support stats
        themes_with_single_anchor = sum(
            1 for t in self._theme_records.values() if t.anchor_count <= 1
        )
        themes_with_many = sum(
            1 for t in self._theme_records.values() if t.anchor_count >= 5
        )

        # Theory support stats
        theories_with_single_theme = sum(
            1 for t in self._theory_records.values() if t.theme_count <= 1
        )

        avg_gs = sum(all_gs) / max(len(all_gs), 1)

        return {
            "total_anchors": total_anchors,
            "total_sentences": total_sentences,
            "total_themes": total_themes,
            "total_theories": total_theories,
            "total_compression_merges": total_compressions,
            "provenance_coverage": {
                "anchors_with_provenance": total_anchors,
                "sentence_coverage_ratio": round(
                    total_sentences / max(total_sentences, 1), 4),
                "anchors_with_keyword_bridge": with_bridge,
                "bridge_coverage_ratio": round(
                    with_bridge / max(total_sentences, 1), 4),
            },
            "grounding_quality": {
                "avg_grounding_score": round(avg_gs, 4),
                "well_grounded_ratio": round(
                    well_grounded / max(total_sentences, 1), 4),
                "jump_level_distribution": dict(jump_dist),
            },
            "hierarchy_quality": {
                "themes_with_single_anchor": themes_with_single_anchor,
                "themes_with_5plus_anchors": themes_with_many,
                "theories_with_single_theme": theories_with_single_theme,
                "avg_anchors_per_theme": round(
                    total_anchors / max(total_themes, 1), 1),
                "avg_themes_per_theory": round(
                    total_themes / max(total_theories, 1), 1),
            },
        }

    # ── Reporting ────────────────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a human-readable provenance report."""
        stats = self.compute_stats()
        lines = []
        lines.append("=" * 60)
        lines.append("  SEMANTIC PROVENANCE REPORT")
        lines.append("=" * 60)
        lines.append(f"  Generated: {datetime.now().isoformat()}")
        lines.append("")
        lines.append(f"  Anchors:   {stats['total_anchors']}")
        lines.append(f"  Sentences: {stats['total_sentences']}")
        lines.append(f"  Themes:    {stats['total_themes']}")
        lines.append(f"  Theories:  {stats['total_theories']}")
        lines.append(f"  Merges:    {stats['total_compression_merges']}")
        lines.append("")
        lines.append("  ── Grounding Quality ──")
        gq = stats["grounding_quality"]
        lines.append(f"  Avg grounding score:  {gq['avg_grounding_score']}")
        lines.append(f"  Well-grounded ratio:  {gq['well_grounded_ratio']}")
        lines.append(f"  Jump distribution:    {gq['jump_level_distribution']}")
        lines.append("")
        lines.append("  ── Hierarchy Quality ──")
        hq = stats["hierarchy_quality"]
        lines.append(f"  Themes w/ single anchor: {hq['themes_with_single_anchor']}")
        lines.append(f"  Themes w/ 5+ anchors:    {hq['themes_with_5plus_anchors']}")
        lines.append(f"  Theories w/ single theme: {hq['theories_with_single_theme']}")
        lines.append(f"  Avg anchors/theme:   {hq['avg_anchors_per_theme']}")
        lines.append(f"  Avg themes/theory:   {hq['avg_themes_per_theory']}")
        lines.append("")
        lines.append("  ── Provenance Coverage ──")
        pc = stats["provenance_coverage"]
        lines.append(f"  Anchors w/ keyword bridge: {pc['anchors_with_keyword_bridge']}")
        lines.append(f"  Bridge coverage ratio:     {pc['bridge_coverage_ratio']}")

        # Show sample chains
        lines.append("")
        lines.append("  ── Sample Full Chains (first 3 theories) ──")
        for i, (theory_name, theory_rec) in enumerate(self._theory_records.items()):
            if i >= 3:
                break
            lines.append(f"  Theory: {theory_name}")
            for theme in theory_rec.supported_by_themes[:3]:
                lines.append(f"    └─ Theme: {theme}")
                theme_rec = self._theme_records.get(theme)
                if theme_rec:
                    for anchor in theme_rec.supported_by[:3]:
                        anchor_recs = self._anchor_records.get(anchor, [])
                        src_preview = (anchor_recs[0].source_text[:60] + "..."
                                      if anchor_recs else "(no source)")
                        lines.append(f"         └─ Anchor: {anchor}")
                        lines.append(f"              └─ Source: {src_preview}")

        return "\n".join(lines)

    # ── Persistence ──────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize all provenance data to a dictionary."""
        return {
            "metadata": {
                "created_at": self._created_at,
                "updated_at": datetime.now().isoformat(),
                "version": "1.0",
            },
            "stats": self.compute_stats(),
            "anchor_provenance": {
                anchor: [r.to_dict() for r in records]
                for anchor, records in self._anchor_records.items()
            },
            "theme_provenance": {
                theme: rec.to_dict()
                for theme, rec in self._theme_records.items()
            },
            "theory_provenance": {
                theory: rec.to_dict()
                for theory, rec in self._theory_records.items()
            },
            "compression_provenance": [
                rec.to_dict() for rec in self._compression_records
            ],
            "full_chains": {
                theory: self.get_theory_chain(theory)
                for theory in self._theory_records
            },
        }

    def save(self, filepath: str):
        """Save full provenance data to JSON file."""
        data = self.to_dict()
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Provenance saved to %s (%d anchors, %d themes, %d theories)",
                     filepath, len(self._anchor_records),
                     len(self._theme_records), len(self._theory_records))

    @classmethod
    def load(cls, filepath: str) -> "ProvenanceStore":
        """Load provenance data from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        store = cls()
        store._created_at = data.get("metadata", {}).get("created_at", "")

        # Restore anchor provenance
        for anchor, records in data.get("anchor_provenance", {}).items():
            for r in records:
                record = AnchorProvenance(
                    anchor=r.get("anchor", anchor),
                    source_text=r.get("source_text", ""),
                    keywords=r.get("keywords", []),
                    keyword_bridge=r.get("keyword_bridge", []),
                    grounding_score=r.get("grounding_score", 0.0),
                    jump_distance=r.get("jump_distance", 0.0),
                    jump_level=r.get("jump_level", "unknown"),
                    polarity_violation=r.get("polarity_violation", False),
                    polarity_reason=r.get("polarity_reason", "ok"),
                    sentence_index=r.get("sentence_index", -1),
                    source_file=r.get("source_file", ""),
                    semantic_similarity=r.get("semantic_similarity"),
                    candidate_rank=r.get("candidate_rank"),
                    verdict=r.get("verdict", ""),
                )
                store._anchor_records[anchor].append(record)
                store._source_to_anchor[record.source_text] = anchor
                store._total_sentences += 1

        # Restore theme provenance
        for theme, rec in data.get("theme_provenance", {}).items():
            store._theme_records[theme] = ThemeProvenance(
                theme=rec.get("theme", theme),
                supported_by=rec.get("supported_by", []),
            )

        # Restore theory provenance
        for theory, rec in data.get("theory_provenance", {}).items():
            store._theory_records[theory] = TheoryProvenance(
                theory=rec.get("theory", theory),
                supported_by_themes=rec.get("supported_by_themes", []),
                total_anchors=rec.get("total_anchors", 0),
                total_sentences=rec.get("total_sentences", 0),
            )

        # Restore compression provenance
        for rec in data.get("compression_provenance", []):
            store._compression_records.append(CompressionProvenance(
                merged_into=rec.get("merged_into", ""),
                merged_items=rec.get("merged_items", []),
                reason=rec.get("reason", {}),
                timestamp=rec.get("timestamp", ""),
            ))

        logger.info("Provenance loaded from %s (%d anchors, %d themes, %d theories)",
                     filepath, len(store._anchor_records),
                     len(store._theme_records), len(store._theory_records))
        return store

    def save_compact_provenance(self, filepath: str,
                                 results: List[dict] = None):
        """Save a compact per-sentence provenance file alongside coding results.

        This is the lightweight version meant to accompany coding_test_results.json.
        Each sentence gets one provenance entry with grounding + hierarchy data.
        """
        entries = []
        for anchor, records in self._anchor_records.items():
            for r in records:
                entry = {
                    "anchor": r.anchor,
                    "source_text": r.source_text,
                    "sentence_index": r.sentence_index,
                    "source_file": r.source_file,
                    "grounding_score": r.grounding_score,
                    "jump_distance": r.jump_distance,
                    "jump_level": r.jump_level,
                    "polarity_violation": r.polarity_violation,
                    "keyword_bridge": r.keyword_bridge,
                    "verdict": r.verdict,
                }
                # Add hierarchy if available
                entries.append(entry)

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "total_entries": len(entries),
                "entries": entries,
            }, f, ensure_ascii=False, indent=2)
        logger.info("Compact provenance saved to %s (%d entries)", filepath, len(entries))
