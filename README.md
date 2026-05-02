# Support Triage Agent

Terminal-based agent that triages support tickets across HackerRank, Claude, and Visa.

## Architecture

```
main.py        ← orchestrator: reads CSV, runs pipeline, writes output
retriever.py   ← corpus loader: topic-routed + keyword-ranked retrieval from data/
escalation.py  ← rule engine: regex-based pre-screening before LLM
triage.py      ← LLM layer: Groq API with structured JSON output
```

## Pipeline (per ticket)
1. **Prompt injection detection** (regex, pre-LLM)
2. **Mandatory escalation rules** (regex patterns for fraud, billing, security, malicious)
3. **Invalid/out-of-scope detection** (regex)
4. **Topic-routed corpus retrieval** from local data/ files (keyword scoring)
5. **LLM triage** with grounded structured JSON output (seed=42, temperature=0)

## Setup

```bash
pip install -r requirements.txt
```

## Environment Variables

```bash
# Linux/Mac
export GROQ_API_KEY=your_key_here

# Windows PowerShell
$env:GROQ_API_KEY="your_key_here"
```

## Run

```bash
python code/main.py
```

## Output
- Predictions: `support_tickets/output.csv`
- Log: `~/hackerrank_orchestrate/log.txt`
