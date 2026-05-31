"""
keyword_engine.py
-----------------
Takes the user's desired position + short description and produces:
  • search_queries   – list of search strings to send to every source
  • must_have        – at least one of these must appear in every result title
  • nice_to_have     – boost relevance score when present
  • negative         – reject results whose title is dominated by these
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

# ── domain taxonomy ─────────────────────────────────────────────
# Maps broad domain tokens → (synonyms, role-variations, negative-keywords)
DOMAIN_TAXONOMY: dict[str, dict] = {
    "ai": {
        "synonyms": [
            "artificial intelligence", "AI", "machine learning", "ML",
            "deep learning", "DL", "neural network", "NLP",
            "natural language processing", "computer vision", "CV",
            "LLM", "large language model", "generative AI", "gen AI",
            "reinforcement learning", "MLOps", "data science",
            "transformer", "GPT", "diffusion model",
        ],
        "negative": [
            "graphic design", "content creator", "SEO", "social media",
            "manga", "anime", "filmmaking", "e-commerce", "ecommerce",
            "sales", "marketing", "customer support",
            "accountant", "HR", "human resource", "receptionist",
            "delivery", "warehouse", "cashier",
        ],
    },
    "data science": {
        "synonyms": [
            "data science", "data scientist", "data analyst",
            "data engineering", "analytics", "BI", "business intelligence",
            "machine learning", "ML", "statistics", "big data",
            "data pipeline", "ETL", "visualization", "power BI", "tableau",
        ],
        "negative": [
            "graphic design", "content creator", "SEO", "social media",
            "manga", "anime", "filmmaking", "e-commerce",
            "sales executive", "customer support", "receptionist",
        ],
    },
    "web": {
        "synonyms": [
            "web developer", "frontend", "front-end", "backend",
            "back-end", "full stack", "fullstack", "react", "angular",
            "vue", "node.js", "django", "flask", "next.js", "HTML",
            "CSS", "javascript", "typescript", "PHP", "laravel",
        ],
        "negative": [
            "graphic design", "sales executive", "accountant",
            "delivery driver", "warehouse", "cashier",
        ],
    },
    "mobile": {
        "synonyms": [
            "mobile developer", "android", "iOS", "flutter", "react native",
            "kotlin", "swift", "dart", "mobile app",
        ],
        "negative": [
            "graphic design", "sales executive", "accountant",
        ],
    },
    "devops": {
        "synonyms": [
            "devops", "SRE", "site reliability", "cloud", "AWS", "azure",
            "GCP", "kubernetes", "docker", "CI/CD", "terraform",
            "infrastructure", "platform engineer",
        ],
        "negative": [
            "graphic design", "sales executive", "accountant",
        ],
    },
    "cybersecurity": {
        "synonyms": [
            "cybersecurity", "security", "penetration testing", "pentest",
            "SOC", "SIEM", "threat", "vulnerability", "infosec",
            "ethical hacking", "red team", "blue team",
        ],
        "negative": [
            "graphic design", "sales executive", "accountant",
        ],
    },
}

ROLE_VARIATIONS = [
    "intern", "internship", "trainee", "co-op", "coop",
    "working student", "student", "fresh graduate", "entry level",
    "junior", "apprentice", "fellow", "graduate",
]


@dataclass
class KeywordPlan:
    """Output of the keyword engine."""
    search_queries: list[str] = field(default_factory=list)
    must_have: list[str] = field(default_factory=list)
    nice_to_have: list[str] = field(default_factory=list)
    negative: list[str] = field(default_factory=list)
    role_keywords: list[str] = field(default_factory=list)


def _tokenize(text: str) -> list[str]:
    """Lowercase split on non-alphanum."""
    return re.findall(r"[a-z0-9/#+.-]+", text.lower())


def _detect_domains(tokens: list[str], raw_text: str) -> list[str]:
    """Detect which taxonomy domains match the user input."""
    raw_lower = raw_text.lower()
    matched = []

    # Direct token matches
    for domain in DOMAIN_TAXONOMY:
        domain_tokens = set(_tokenize(domain))
        if domain_tokens & set(tokens):
            matched.append(domain)
            continue
        # Check if any synonym appears in the raw text
        for syn in DOMAIN_TAXONOMY[domain]["synonyms"][:8]:
            if syn.lower() in raw_lower:
                matched.append(domain)
                break

    # Special patterns
    ai_signals = {"ai", "ml", "artificial", "intelligence", "machine",
                  "learning", "deep", "nlp", "llm", "neural", "cv",
                  "computer", "vision", "data", "science"}
    if ai_signals & set(tokens):
        if "ai" not in matched:
            matched.append("ai")

    return list(dict.fromkeys(matched))  # deduplicate, preserve order


def _detect_role_type(tokens: list[str], raw_text: str) -> list[str]:
    """Detect role type keywords from user input."""
    raw_lower = raw_text.lower()
    found = []
    for role in ROLE_VARIATIONS:
        if role in raw_lower:
            found.append(role)
    if not found:
        # Default: check individual tokens
        for tok in tokens:
            if tok in {"intern", "internship", "trainee", "junior", "entry"}:
                found.append(tok)
    return list(dict.fromkeys(found)) if found else ["intern", "internship"]


def build_keyword_plan(position: str, description: str = "") -> KeywordPlan:
    """
    Build a complete keyword plan from the user's position + description.
    
    Parameters
    ----------
    position : str
        e.g. "AI/ML Internship"
    description : str
        e.g. "machine learning, deep learning, NLP roles in tech"
    
    Returns
    -------
    KeywordPlan with search_queries, must_have, nice_to_have, negative, role_keywords
    """
    combined = f"{position} {description}"
    tokens = _tokenize(combined)

    # Detect domains
    domains = _detect_domains(tokens, combined)
    if not domains:
        # Fallback: use the position as-is
        domains = []

    # Detect role type
    role_kws = _detect_role_type(tokens, combined)

    # Build must-have keywords (domain-specific)
    must_have = set()
    nice_to_have = set()
    negative = set()

    for domain in domains:
        info = DOMAIN_TAXONOMY.get(domain, {})
        # First 6 synonyms are "must have at least one"
        for syn in info.get("synonyms", [])[:10]:
            must_have.add(syn.lower())
        # All synonyms are nice-to-have
        for syn in info.get("synonyms", []):
            nice_to_have.add(syn.lower())
        # Negatives
        for neg in info.get("negative", []):
            negative.add(neg.lower())

    # Add negative keywords for senior roles if we are looking for an intern
    if any(r in role_kws for r in ["intern", "internship", "trainee", "junior", "student"]):
        negative.update(["manager", "senior", "lead", "director", "head", "principal", "staff", "vp"])

    # Also add tokens from the user's description as nice-to-have
    desc_tokens = _tokenize(description)
    for tok in desc_tokens:
        if len(tok) > 2 and tok not in {"the", "and", "for", "with", "any", "looking"}:
            nice_to_have.add(tok)

    # Build search queries — combinations of domain synonyms + role keywords
    search_queries = []
    if domains:
        # Primary: user's exact position
        search_queries.append(position)

        # Generate targeted queries
        for domain in domains:
            info = DOMAIN_TAXONOMY.get(domain, {})
            key_terms = info.get("synonyms", [])[:6]
            for term in key_terms:
                for role in role_kws[:2]:
                    q = f"{term} {role}"
                    if q not in search_queries:
                        search_queries.append(q)
    else:
        # No recognized domain — use position directly with role variations
        search_queries.append(position)
        base = re.sub(r"\b(intern|internship|trainee|job|position)\b", "", position, flags=re.IGNORECASE).strip()
        if base:
            for role in role_kws[:2]:
                q = f"{base} {role}"
                if q not in search_queries:
                    search_queries.append(q)

    # Limit queries to avoid excessive API calls
    search_queries = search_queries[:15]

    # If no must_have was built, use tokens from the position
    if not must_have:
        pos_tokens = _tokenize(position)
        must_have = {t for t in pos_tokens if len(t) > 2}

    return KeywordPlan(
        search_queries=search_queries,
        must_have=sorted(must_have),
        nice_to_have=sorted(nice_to_have),
        negative=sorted(negative),
        role_keywords=role_kws,
    )
