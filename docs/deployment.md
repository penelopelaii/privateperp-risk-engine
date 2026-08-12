# Deployment

Two services: the Next.js frontend on Vercel, the FastAPI backend on Render or
Railway. Both have free tiers that are sufficient for a demo.

Everything in the repository is prepared. The remaining steps all require a
browser, an account, and your authorisation, so they are listed here rather than
scripted.

## What you need to do

1. **Create accounts** at [vercel.com](https://vercel.com) and
   [render.com](https://render.com) (or [railway.app](https://railway.app)), and
   connect each to the GitHub repository.
2. **Push this repository to GitHub** if it is not there already.
3. **Deploy the backend first**, because the frontend needs its URL.
4. **Deploy the frontend**, then come back and set the backend's CORS variable to
   the frontend's URL.

No step needs a payment method on the free tiers, and no credential belongs in
this repository.

## Backend — Render

`render.yaml` at the repository root is a Render blueprint, so the service is
described in code and you only supply the environment-specific values.

1. In Render, choose **New → Blueprint** and select the repository. Render reads
   `render.yaml` and proposes one web service.
2. Deploy it. The build runs `pip install -r backend/requirements.txt` and the
   service starts with `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
3. Note the assigned URL, e.g. `https://privateperp-risk-engine-api.onrender.com`.
4. Confirm it is up:

```bash
curl -s https://YOUR-API.onrender.com/health
```

5. After the frontend is deployed, set these in the Render dashboard under
   **Environment**, then redeploy:

| Variable | Value |
| --- | --- |
| `PRIVATEPERP_CORS_ORIGINS` | Your Vercel URL, e.g. `https://privateperp-risk-engine.vercel.app`. Comma-separate several |
| `PRIVATEPERP_CORS_ORIGIN_REGEX` | Optional. `https://.*\.vercel\.app` to also allow preview deployments |

Until `PRIVATEPERP_CORS_ORIGINS` is set the API only accepts
`http://localhost:3000`, and the deployed frontend will show "Could not reach the
risk engine API."

**Free tier caveat.** Render spins an idle free service down, and the first
request after that takes tens of seconds. The staleness experiment opens with 41
parallel requests, so a cold start is visible. Either accept it, or keep the
service warm with an external uptime pinger.

## Backend — Railway, as an alternative

`Procfile` and the root `requirements.txt` are there so Railway's builder detects
a Python project with no configuration.

1. **New Project → Deploy from GitHub repo**.
2. Under **Settings → Networking**, generate a public domain.
3. Set the same two `PRIVATEPERP_*` variables under **Variables**.

Railway injects `PORT`; the `Procfile` reads it, falling back to 8000 locally.

## Frontend — Vercel

The Next.js app lives in a subdirectory, which is the only setting that is easy
to miss.

1. **Add New → Project**, select the repository.
2. Set **Root Directory** to `frontend`. Vercel then detects Next.js and needs no
   further build configuration.
3. Under **Environment Variables**, add:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | The backend URL, no trailing slash, e.g. `https://YOUR-API.onrender.com` |

Add it for Production, Preview, and Development so preview deployments work too.

4. Deploy, then set the backend's `PRIVATEPERP_CORS_ORIGINS` to the resulting URL
   and redeploy the backend.

`NEXT_PUBLIC_*` variables are inlined into the client bundle at build time and
are therefore public. That is correct here — the API base URL is not a secret and
the API needs no credentials — but it means **changing it requires a rebuild**,
not just a restart, and it means no secret may ever be given that prefix.

## Verifying the deployment

```bash
curl -s https://YOUR-API.onrender.com/health

curl -s https://YOUR-API.onrender.com/risk/v1/evaluate \
  -H 'content-type: application/json' \
  -d '{"state": {
        "volatility": 0.9, "spot_depth": 350000,
        "impact_exponent": 1.15, "impact_coefficient": 0.0703,
        "hedge_depth": 17500, "hedge_volatility": 0.6,
        "hedge_correlation": 0.22, "hedge_ratio": 0.05,
        "mark_staleness_days": 120, "mark_refresh_days": 120,
        "source_count": 3, "source_dispersion": 0.05,
        "source_correlation": 0.5, "jump_intensity": 10,
        "jump_tail_index": 2, "jump_scale": 0.05,
        "open_interest_long": 5000000, "open_interest_short": 500000,
        "crowding": {"low": 0.02, "high": 0.2}}}'
```

The second should return `"viable_as_continuous_perp": false`,
`"recommended_mechanism": "settled_forward"`, and a required initial margin of
`3.0297...`, matching the 303.0% in the README.

Then open the Vercel URL, confirm the V1 tab loads an assessment rather than an
error, and update the **Live demo** line in `README.md`.

## Not included

No CI, no containers, no custom domain, no monitoring. Evaluation is a pure
function that runs in microseconds against no database, so there is nothing to
orchestrate. These get added when there is a reason.
