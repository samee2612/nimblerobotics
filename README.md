# Fulfillment Exception Copilot

A local, synthetic-data demo of an internal fulfillment tool. It turns an at-risk order into an AI-assisted recovery plan, then validates the plan against inventory, carrier cutoff, and cost policies before an operator can approve it.

## What it demonstrates

- **Operations workflow:** one delayed high-value order, from exception to auditable approval.
- **Gemini structured output:** with `GEMINI_API_KEY`, Gemini returns a typed `RecoveryPlan`; no key is required for the deterministic local fallback.
- **AI safety:** the model does not decide what is safe. Server-side Python checks available-to-promise inventory, carrier eligibility, and a $25 approval limit.
- **A clear failure mode:** Reno looks attractive geographically, but all stock is reserved. The policy layer rejects this plausible suggestion and the tool selects Ontario instead.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional: add a Gemini API key
uvicorn app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Test

```bash
pytest
```

## Recording flow

1. Show the at-risk order and click **Generate recovery plan**.
2. Explain that Gemini proposes a typed plan using pre-queried inventory and carrier facts; Python policy code validates it.
3. Open “View rejected AI candidate” to show that reserved Reno inventory was caught by the available-to-promise check.
4. Approve the Ontario/UPS plan and point to the audit record. The headline value metric is the controlled demo comparison: 8 minutes of manual triage versus a 90-second assisted workflow.

All people, orders, inventory, and metrics are synthetic for demonstration only.
