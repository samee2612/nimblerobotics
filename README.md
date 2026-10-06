# Fulfillment Exception Copilot

A local, synthetic-data demo of an internal fulfillment tool. It turns an at-risk order into an AI-assisted recovery plan, then validates the plan against inventory, carrier cutoff, and cost policies before an operator can approve it.

## What it demonstrates

- **Operations workflow:** one delayed high-value order, from exception to auditable approval.
- **Gemini structured output:** with `GEMINI_API_KEY`, Gemini returns a typed `RecoveryPlan`; no key is required for the deterministic local fallback.
- **AI safety:** the model does not decide what is safe. Server-side Python checks available-to-promise inventory, carrier eligibility, and a $25 approval limit.
- **A clear safety boundary:** Gemini proposes a plan, and deterministic server-side checks verify inventory, carrier eligibility, and cost before approval. The tests cover rejection of a plan that names a warehouse with no available stock.

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

## Deploy on Render

1. In Render, create a new Blueprint and connect this GitHub repository.
2. Render reads `render.yaml` and prompts for `GEMINI_API_KEY`. Enter a newly generated key as a secret in Render; do not commit it or put it in the Blueprint file.
3. Deploy the Blueprint and open the generated `onrender.com` URL.

The free instance may take a short time to wake after inactivity. This app uses synthetic data only and has no authentication; do not connect it to real customer or operational data.

## Recording flow

1. Show the at-risk order and click **Generate recovery plan**.
2. Explain that Gemini proposes a typed plan using pre-queried inventory and carrier facts; Python policy code validates it.
3. Show the inventory, carrier cutoff, and cost checks, then approve the recommendation and point to the audit record.
4. If discussing a hard moment, describe the reserved-inventory case as a test scenario for the policy validator, not as a mistake observed from Gemini. The 8-minute versus 90-second comparison is a synthetic demo estimate, not a measured user result.

All people, orders, inventory, and metrics are synthetic for demonstration only.
