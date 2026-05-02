"""
Corpus retrieval module.
Loads the most relevant support articles from data/ for each ticket.
Uses topic-based folder routing + keyword scoring for precise retrieval.
"""

from pathlib import Path
import re

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

COMPANY_DIRS = {
    "hackerrank": DATA_DIR / "hackerrank",
    "claude":     DATA_DIR / "claude",
    "visa":       DATA_DIR / "visa",
}

# Maps issue topic patterns -> priority subfolders to search first
TOPIC_ROUTING = {
    "hackerrank": [
        (r"remove|employee.*left|user.*left|delete.*user|remove.*interviewer|remove.*team", [
            "settings/teams-management",
        ]),
        (r"subscription|pause.*sub|billing|payment|invoice", [
            "settings/company-level-admin-settings",
            "general-help/contact-us",
        ]),
        (r"score|dispute|grade|unfair|recruiter.*reject|increase.*score", [
            "screen/frequently-asked-questions",
            "screen/managing-tests",
        ]),
        (r"certificate|name.*incorrect|name.*wrong|name.*update", [
            "screen/frequently-asked-questions",
            "general-help/contact-us",
        ]),
        (r"apply tab|resume builder|resume", [
            "screen/getting-started",
            "general-help/deprecations-and-experience-changes",
            "uncategorized",
        ]),
        (r"submission.*not working|all.*broken|site.*down|none.*working|platform.*down", [
            "screen/frequently-asked-questions",
            "uncategorized",
            "general-help/contact-us",
        ]),
        (r"zoom|compatibility|compatible check|blocker|connectivity", [
            "screen/frequently-asked-questions",
            "interviews/additional-resources",
            "uncategorized",
        ]),
        (r"reschedule|rescheduling|alternative.*date|postpone", [
            "screen/invite-candidates",
            "screen/managing-tests",
            "general-help/additional-resources",
        ]),
        (r"inactivity|timeout|lobby|screen share|kicked out|inactive", [
            "interviews/interview-settings",
            "interviews/getting-started",
            "interviews/additional-resources",
        ]),
        (r"mock interview|interview.*stopped|interview.*not working", [
            "interviews/manage-interviews",
            "interviews/additional-resources",
        ]),
        (r"infosec|security.*form|questionnaire|compliance.*form", [
            "settings/company-level-admin-settings",
            "general-help/contact-us",
        ]),
    ],
    "claude": [
        (r"workspace|seat|access|team.*account|admin.*removed|restore.*access", [
            "team-and-enterprise-plans",
            "identity-management-sso-jit-scim",
        ]),
        (r"bedrock|aws|amazon|api.*failing|requests.*failing", [
            "amazon-bedrock",
        ]),
        (r"lti|education|professor|student|university|canvas|college", [
            "claude-for-education",
        ]),
        (r"crawl|robot|website|bot|claudebot|stop.*crawling", [
            "privacy-and-legal",
        ]),
        (r"data.*train|model.*improv|how long.*data|training.*data|data.*used", [
            "privacy-and-legal",
            "team-and-enterprise-plans/security-and-compliance",
        ]),
        (r"security|vulnerabilit|bug bounty|exploit|report.*bug", [
            "safeguards",
            "privacy-and-legal",
        ]),
        (r"not working|all.*failing|completely down|outage|stopped working", [
            "claude",
            "amazon-bedrock",
        ]),
    ],
    "visa": [
        (r"dispute|wrong product|merchant|chargeback|seller", [
            "support/small-business",
            "support/consumer",
        ]),
        (r"identity.*theft|identity.*stolen|stolen.*identity", [
            "support/consumer",
            "support",
        ]),
        (r"lost.*card|stolen.*card|block.*card|card.*blocked|emergency", [
            "support/consumer",
            "support",
        ]),
        (r"minimum.*spend|minimum.*amount|spend.*minimum|10.*dollar|dollar.*minimum", [
            "support/consumer",
            "support/small-business",
        ]),
        (r"cash|atm|withdraw|urgent.*cash", [
            "support/consumer",
        ]),
        (r"travel|blocked.*card|card.*blocked|abroad|overseas", [
            "support/consumer",
        ]),
    ]
}


def _clean_md(text: str) -> str:
    """Remove image tags and long URLs to save tokens."""
    text = re.sub(r'!\[.*?\]\(https?://[^\)]+\)', '', text)
    text = re.sub(r'\(https?://[^\)]{60,}\)', '(...)', text)
    return text.strip()


def _read_file(path: Path, max_chars: int = 800) -> str:
    """Read a markdown file, strip frontmatter and images."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        title_match = re.search(r'title:\s*"([^"]+)"', content)
        title = title_match.group(1) if title_match else path.stem.replace("-", " ")
        content = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL)
        content = _clean_md(content)
        return f"## {title}\n{content.strip()[:max_chars]}"
    except Exception:
        return ""


def _keyword_score(path: Path, keywords: list) -> int:
    """Score a file by keyword matches."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
        return sum(1 for kw in keywords if kw.lower() in content)
    except Exception:
        return 0


def _get_priority_folders(company_key: str, issue: str) -> list:
    """Return priority folders based on topic pattern matching."""
    routing = TOPIC_ROUTING.get(company_key, [])
    issue_lower = issue.lower()
    matched = []
    for pattern, folders in routing:
        if re.search(pattern, issue_lower):
            for folder in folders:
                full_path = COMPANY_DIRS[company_key] / folder
                if full_path.exists():
                    matched.append(full_path)
    return matched


def get_corpus(company: str, issue: str = "", max_chars: int = 3000) -> str:
    """
    Retrieve the most relevant corpus for a ticket.
    1. Route to priority folders based on topic patterns
    2. Score all files by keyword relevance
    3. Take top-scored files up to max_chars
    4. Fall back to index.md if no matches
    """
    key = company.lower() if company else ""

    if "hackerrank" in key:
        company_key = "hackerrank"
    elif "claude" in key:
        company_key = "claude"
    elif "visa" in key:
        company_key = "visa"
    else:
        parts = []
        for ck in ["hackerrank", "claude", "visa"]:
            idx = COMPANY_DIRS[ck] / "index.md"
            if idx.exists():
                parts.append(_read_file(idx, max_chars=700))
        return "\n\n---\n\n".join(parts)[:max_chars]

    company_dir = COMPANY_DIRS[company_key]
    keywords = [w for w in issue.lower().split() if len(w) > 3]

    priority_folders = _get_priority_folders(company_key, issue)

    scored = []
    seen = set()

    for folder in priority_folders:
        for f in sorted(folder.rglob("*.md"))[:15]:
            if f in seen:
                continue
            seen.add(f)
            score = _keyword_score(f, keywords) + 5
            scored.append((score, f))

    for f in sorted(company_dir.rglob("*.md"))[:150]:
        if f in seen:
            continue
        seen.add(f)
        score = _keyword_score(f, keywords)
        if score > 0:
            scored.append((score, f))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_files = [f for _, f in scored[:8]]

    chunks = []
    total = 0
    for f in top_files:
        chunk = _read_file(f, max_chars=600)
        if chunk and total + len(chunk) < max_chars:
            chunks.append(chunk)
            total += len(chunk)

    if not chunks:
        idx = company_dir / "index.md"
        if idx.exists():
            return _read_file(idx, max_chars=max_chars)

    return "\n\n---\n\n".join(chunks)
