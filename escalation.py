"""
Escalation rules module.
Explicit rule-based pre-screening before LLM triage.
Keeps sensitive/dangerous cases away from the LLM entirely.
"""

import re

# Each pattern that triggers mandatory escalation
ESCALATION_RULES = [
    # Identity theft / fraud
    (r"(all|none).{0,10}(submissions|challenges).{0,40}(not working|broken|failing)", "outage"),
    (r"identity.{0,10}(stolen|theft|compromised)", "identity_theft"),
    (r"(fraud|fraudulent).{0,20}(transaction|charge|card)", "fraud"),
    (r"unauthorized.{0,20}(charge|transaction|access|payment)", "fraud"),
    (r"stolen.{0,10}card", "fraud"),
    # Billing / payment
    (r"order.{0,5}id.{0,10}cs_live", "billing_dispute"),
    (r"payment.{0,15}issue", "billing"),
    (r"give me my money", "billing"),
    # Security
    (r"security.{0,15}vulnerabilit", "security"),
    (r"bug.{0,10}bount", "security"),
    (r"found.{0,20}(vulnerability|exploit|bug in claude|bug in hackerrank)", "security"),
    # Malicious requests
    (r"(delete|remove|wipe).{0,15}(all|system|files|everything)", "malicious"),
    (r"rm\s+-rf", "malicious"),
    (r"format.{0,10}(drive|disk|system|c:)", "malicious"),
    (r"code to delete", "malicious"),
    # Prompt injection (English)
    (r"reveal.{0,20}(internal|system|prompt|rules|documents)", "prompt_injection"),
    (r"ignore.{0,20}(previous|instructions|rules|above)", "prompt_injection"),
    (r"show.{0,20}(internal|system prompt|retrieved|rules)", "prompt_injection"),
    (r"what.{0,20}(prompt|instructions).{0,20}(given|using|follow)", "prompt_injection"),
    # Prompt injection (French)
    (r"affiche.{0,40}(règles|documents|logique|interne)", "prompt_injection"),
    (r"montre.{0,20}(règles|système|prompt|logique)", "prompt_injection"),
    (r"logique exacte", "prompt_injection"),
    (r"documents récupérés", "prompt_injection"),
    # Platform-wide outage
    (r"none.{0,20}(working|accessible|loading)", "outage"),
    (r"(site|platform|everything|all requests).{0,20}(down|not working|failing|broken)", "outage"),
    (r"completely.{0,15}(down|stopped|broken|failing)", "outage"),
    # Score manipulation
    (r"(increase|change|modify).{0,20}(my score|test score|grade)", "policy_violation"),
    (r"tell.{0,20}company.{0,20}(move me|hire me|next round)", "policy_violation"),
    # Refunds
    (r"refund", "billing"),
]

# Patterns for clearly out-of-scope / invalid tickets
INVALID_RULES = [
    (r"^it.{0,5}s not working.{0,10}help[\s!.]*$", "too_vague"),
    (r"^(it|this|everything).{0,10}(not working|broken|doesn.t work)[\s,!.]*$", "too_vague"),
    (r"^(thank(s| you)|thanks for|ty)[\s!.]*$", "thanks"),
    (r"what.{0,10}(actor|actress).{0,20}(iron man|movie|film)", "off_topic"),
    (r"who (is|plays|played).{0,20}(iron man|batman|avenger)", "off_topic"),
    (r"weather.{0,20}(today|tomorrow|forecast)", "off_topic"),
    (r"^(hi|hello|hey|good morning|good evening)[\s!.]*$", "greeting"),
]


def check_escalation(issue: str, subject: str) -> dict | None:
    """
    Returns escalation info if the ticket matches a mandatory escalation rule.
    Returns None if no rule matches.
    """
    combined = f"{issue} {subject}".lower()
    for pattern, reason in ESCALATION_RULES:
        if re.search(pattern, combined):
            return {"reason": reason, "pattern": pattern}
    return None


def check_invalid(issue: str, subject: str) -> dict | None:
    """
    Returns invalid marker if ticket is clearly out of scope.
    """
    combined = f"{issue} {subject}".lower().strip()
    for pattern, reason in INVALID_RULES:
        if re.search(pattern, combined):
            return {"reason": reason, "pattern": pattern}
    return None


def is_prompt_injection(issue: str) -> bool:
    """Quick check for prompt injection in issue text."""
    injection_patterns = [
        r"affiche.{0,40}(règles|documents|logique)",
        r"reveal.{0,20}(internal|system|prompt)",
        r"ignore.{0,20}(previous|instructions)",
        r"show.{0,20}(system prompt|internal rules|retrieved)",
        r"logique exacte",
        r"documents récupérés",
        r"what (prompt|instructions) (are you|you are)",
    ]
    issue_lower = issue.lower()
    return any(re.search(p, issue_lower) for p in injection_patterns)
