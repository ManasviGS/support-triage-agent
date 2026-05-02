#!/usr/bin/env python3
"""
Multi-Domain Support Triage Agent
===================================
Entry point. Orchestrates retrieval, escalation checks, and LLM triage.

Usage:
    python code/main.py
"""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from retriever  import get_corpus
from escalation import check_escalation, check_invalid, is_prompt_injection
from triage     import call_llm, FALLBACK

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
TICKETS_CSV = ROOT / "support_tickets" / "support_tickets.csv"
OUTPUT_CSV  = ROOT / "support_tickets" / "output.csv"
LOG_FILE    = Path.home() / "hackerrank_orchestrate" / "log.txt"

FIELDNAMES = [
    "issue", "subject", "company",
    "response", "product_area", "status", "request_type", "justification"
]

# ── Reason → Product Area Mapping ──────────────────────────────────────────
REASON_TO_AREA = {
    "fraud": "fraud",
    "identity_theft": "fraud",
    "billing": "billing",
    "billing_dispute": "billing",
    "security": "security",
    "outage": "general_support",
    "policy_violation": "screen",
    "malicious": "general_support",
    "prompt_injection": "security",
}

# ── Per-ticket pipeline ────────────────────────────────────────────────────
def process_ticket(issue: str, subject: str, company: str, log_fh) -> dict:
    """
    Full triage pipeline for one ticket:
    1. Prompt injection detection (rule-based, pre-LLM)
    2. Escalation rule matching (rule-based, pre-LLM)
    3. Invalid/out-of-scope detection (rule-based)
    4. Keyword-ranked corpus retrieval from local data/files
    5. LLM triage with grounded structured JSON output
    """
    log_fh.write(f"\n{'='*60}\n")
    log_fh.write(f"TICKET | Company: {company} | Subject: {subject}\n")
    log_fh.write(f"Issue: {issue}\n")

    # Step 1 — prompt injection
    if is_prompt_injection(issue):
        log_fh.write("[RULE] Prompt injection detected → escalate\n")
        return {
            "response":      "Escalate to a human",
            "product_area":  REASON_TO_AREA["prompt_injection"],
            "status":        "escalated",
            "request_type":  "invalid",
            "justification": "Prompt injection attempt detected in ticket; escalating for human review."
        }

    # Step 2 — mandatory escalation rules
    escalation = check_escalation(issue, subject)
    if escalation:
        log_fh.write(f"[RULE] Escalation matched: {escalation['reason']} ({escalation['pattern']})\n")
        return {
            "response":      "Escalate to a human",
            "product_area":  REASON_TO_AREA.get(
                escalation["reason"],
                "general_support"
            ),
            "status":        "escalated",
            "request_type":  "product_issue",
            "justification": f"Rule-based escalation: {escalation['reason']}. This ticket requires human handling."
        }

    # Step 3 — invalid/out-of-scope
    invalid = check_invalid(issue, subject)
    if invalid:
        log_fh.write(f"[RULE] Invalid matched: {invalid['reason']}\n")
        return {
            "response":      "I'm sorry, this request is outside the scope of our support.",
            "product_area":  "general",
            "status":        "replied",
            "request_type":  "invalid",
            "justification": f"Ticket is out of scope ({invalid['reason']}); replied with out-of-scope message."
        }

    # Step 4 — corpus retrieval
    corpus = get_corpus(company, issue)
    log_fh.write(f"[RETRIEVAL] Corpus: {len(corpus)} chars\n")

    # Step 5 — LLM triage
    return call_llm(issue, subject, company, corpus, log_fh)


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "a", encoding="utf-8") as log_fh:
        log_fh.write(f"\n{'#'*60}\n")
        log_fh.write(f"Agent started: {datetime.now().isoformat()}\n")
        log_fh.write(f"{'#'*60}\n")

        # Read tickets
        tickets = []
        with open(TICKETS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tickets.append(row)

        print(f"Loaded {len(tickets)} tickets", file=sys.stderr)

        results = []
        for i, ticket in enumerate(tickets):
            issue   = ticket.get("Issue", "").strip()
            subject = ticket.get("Subject", "").strip()
            company = ticket.get("Company", "").strip()

            print(
                f"[{i+1}/{len(tickets)}] {company} | {subject or issue[:50]}",
                file=sys.stderr
            )

            try:
                result = process_ticket(issue, subject, company, log_fh)
            except Exception as e:
                log_fh.write(f"[FATAL] {e}\n")
                result = FALLBACK

            results.append({
                "issue":         issue,
                "subject":       subject,
                "company":       company,
                "response":      result.get("response", "Escalate to a human"),
                "product_area":  result.get("product_area", "unknown"),
                "status":        result.get("status", "escalated"),
                "request_type":  result.get("request_type", "product_issue"),
                "justification": result.get("justification", ""),
            })

            time.sleep(20)  # stay under Groq free tier rate limit

        # Write output CSV
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(results)

        log_fh.write(f"\nCompleted: {datetime.now().isoformat()}\n")
        log_fh.write(f"Total tickets processed: {len(results)}\n")

    print(f"\nDone! Output → {OUTPUT_CSV}", file=sys.stderr)
    print(f"Log   → {LOG_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()