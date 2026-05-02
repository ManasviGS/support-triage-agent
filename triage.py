"""
LLM triage module.
Calls Groq API with structured JSON output and deterministic settings.
"""

import json
import os
import sys
import time

from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM = """You are a support triage agent for HackerRank, Claude (Anthropic), and Visa.

STRICT RULES:
1. Use ONLY the support corpus provided. Never invent policies, URLs, or phone numbers.
2. ESCALATE (status=escalated, response="Escalate to a human") for:
   - Fraud, identity theft, unauthorized transactions
   - Billing or payment disputes
   - Platform-wide outages
   - Security vulnerabilities
   - Requests to change scores or bypass policies
   - Malicious or dangerous requests
3. For out-of-scope tickets: status=replied, request_type=invalid
7. Informational or onboarding questions (how-to, setup, process inquiries) should be REPLIED, not escalated, even if they mention security, infosec, or compliance topics.
4. Informational or onboarding questions (how-to, setup, process inquiries) should be
   REPLIED with request_type=product_issue, not escalated and not marked invalid.
   "invalid" is ONLY for completely off-topic requests (movies, weather, gibberish).
5. request_type: exactly "product_issue", "feature_request", "bug", or "invalid"
6. product_area: a short specific category (e.g. account_management, billing, screen, interviews, privacy, aws_bedrock, lti, consumer_support, dispute_resolution, fraud, security)

Return ONLY valid JSON, no markdown, no explanation:
{"response":"...","product_area":"...","status":"...","request_type":"...","justification":"..."}"""

FALLBACK = {
    "response": "Escalate to a human",
    "product_area": "unknown",
    "status": "escalated",
    "request_type": "product_issue",
    "justification": "Could not parse model response; defaulting to safe escalation."
}


def call_llm(issue: str, subject: str, company: str, corpus: str, log_fh) -> dict:
    """Call the LLM and return parsed triage decision."""

    prompt = f"""Support Corpus (use ONLY this):
{corpus}

---
Ticket:
Company: {company}
Subject: {subject}
Issue: {issue}

Return ONLY the JSON."""

    for attempt in range(3):
        try:
            if attempt > 0:
                wait = 20 * attempt
                print(f"  Retry {attempt}, waiting {wait}s...", end="", flush=True)
                time.sleep(wait)

            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0,
                seed=42,
                response_format={"type": "json_object"},
                max_tokens=350,
            )

            raw = resp.choices[0].message.content.strip()
            log_fh.write(f"--- LLM RESPONSE ---\n{raw}\n")

            result = json.loads(raw)

            # Normalize status
            result["status"] = result.get("status", "escalated").lower()
            if result["status"] not in {"replied", "escalated"}:
                result["status"] = "escalated"

            # Validate request_type
            valid_types = {"product_issue", "feature_request", "bug", "invalid"}
            if result.get("request_type") not in valid_types:
                result["request_type"] = "product_issue"

            return result

        except Exception as e:
            log_fh.write(f"[ERROR attempt {attempt+1}] {type(e).__name__}: {e}\n")
            print(f"  ERROR: {type(e).__name__}: {e}", file=sys.stderr)

    return FALLBACK
