"""
relevance.py
------------
Multi-layer relevance scoring for job listings.

Layers:
  1. Hard filter  – title must contain ≥1 domain keyword AND ≥1 role keyword
  2. Negative     – penalise / reject if dominated by negative keywords
  3. Soft scoring – 0-100 based on keyword density in title + description
  4. Threshold    – only jobs ≥ threshold make the cut
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from keyword_engine import KeywordPlan


@dataclass
class ScoredJob:
    """A job dict augmented with a relevance score."""
    job: dict
    score: int
    match_reasons: list[str]


def _normalise(text: str | None) -> str:
    """Lowercase + strip HTML tags + collapse whitespace."""
    if not text:
        return ""
    # Strip HTML tags (descriptions from APIs often contain HTML)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text.lower().strip())


def _count_matches(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Count how many keywords appear in *text*, return count + matched list."""
    matched = []
    for kw in keywords:
        # Use word boundary for short keywords, substring for phrases
        if len(kw) <= 3:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text):
                matched.append(kw)
        else:
            if kw in text:
                matched.append(kw)
    return len(matched), matched


def score_job(job: dict, plan: KeywordPlan) -> ScoredJob:
    """
    Score a single job against the keyword plan.
    
    Returns a ScoredJob with score 0–100.
    """
    title = _normalise(job.get("title"))
    description = _normalise(job.get("description"))
    combined = f"{title} {description}"
    reasons: list[str] = []
    score = 0

    # ── Layer 1: Hard filter (domain keyword in title) ──────────
    domain_in_title, domain_matched = _count_matches(title, plan.must_have)
    role_in_title, role_matched = _count_matches(title, plan.role_keywords)

    if domain_in_title == 0:
        # Check description as fallback – but apply heavy penalty
        domain_in_desc, domain_desc_matched = _count_matches(description, plan.must_have)
        if domain_in_desc >= 2:
            score += 10
            reasons.append(f"domain in desc: {', '.join(domain_desc_matched[:3])}")
        else:
            return ScoredJob(job=job, score=0, match_reasons=["no domain keyword in title"])

    if role_in_title == 0:
        # Check if description mentions the role
        role_in_desc, role_desc_matched = _count_matches(combined, plan.role_keywords)
        if role_in_desc > 0:
            score += 5
            reasons.append(f"role in desc: {', '.join(role_desc_matched[:2])}")
        else:
            # If user explicitly searched for an intern, and neither title nor desc says intern, reject.
            if any(r in plan.role_keywords for r in ["intern", "internship", "trainee", "student"]):
                return ScoredJob(job=job, score=0, match_reasons=["no role keyword in title or desc"])

    # ── Layer 2: Negative keyword check ─────────────────────────
    neg_in_title, neg_matched = _count_matches(title, plan.negative)
    if neg_in_title > 0 and domain_in_title <= 1:
        # Title has negative keywords and weak domain signal → reject
        score -= 40
        reasons.append(f"negative title: {', '.join(neg_matched)}")
        if score <= 0 and domain_in_title == 0:
            return ScoredJob(job=job, score=0, match_reasons=[f"negative dominated: {', '.join(neg_matched)}"])

    # ── Layer 3: Positive scoring ───────────────────────────────

    # Title domain hits (max +40)
    title_domain_score = min(domain_in_title * 12, 40)
    score += title_domain_score
    if domain_matched:
        reasons.append(f"title domain: {', '.join(domain_matched[:4])}")

    # Title role hits (+15)
    if role_in_title > 0:
        score += 15
        reasons.append(f"title role: {', '.join(role_matched[:2])}")

    # Exact phrase bonus — if the user typed "AI intern" and it's in title (+15)
    # Check pairs of must_have + role keyword in title
    for mh in plan.must_have[:5]:
        for rk in plan.role_keywords[:2]:
            phrase = f"{mh} {rk}"
            if phrase in title:
                score += 15
                reasons.append(f"exact phrase: '{phrase}'")
                break

    # Description richness — nice-to-have keywords in description (+max 20)
    if description:
        nice_count, nice_matched = _count_matches(combined, plan.nice_to_have)
        desc_score = min(nice_count * 3, 20)
        score += desc_score
        if nice_matched:
            reasons.append(f"description match: {len(nice_matched)} keywords")

    # Negative in description penalty
    neg_in_desc, _ = _count_matches(description, plan.negative)
    if neg_in_desc >= 3:
        score -= 10
        reasons.append("many negatives in description")

    # Clamp
    score = max(0, min(100, score))

    return ScoredJob(job=job, score=score, match_reasons=reasons)


def filter_jobs(
    jobs: list[dict],
    plan: KeywordPlan,
    threshold: int = 40,
) -> list[ScoredJob]:
    """
    Score all jobs and return only those meeting the threshold.
    Results are sorted by score descending, then date descending.
    """
    scored = [score_job(j, plan) for j in jobs]
    passing = [s for s in scored if s.score >= threshold]

    # Sort by score desc, then date desc
    def sort_key(sj: ScoredJob):
        date = sj.job.get("date_posted") or "0000-00-00"
        return (-sj.score, date)

    passing.sort(key=sort_key)

    # Stats
    total = len(jobs)
    rejected = total - len(passing)
    print(f"\n  📊 Relevance Filter: {total} scraped → {len(passing)} relevant ({rejected} rejected)")

    return passing
