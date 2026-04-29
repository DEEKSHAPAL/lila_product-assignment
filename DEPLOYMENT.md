# Deployment Guide

## Short Answer

Use Streamlit Community Cloud for the interactive dashboard.

Use Vercel only as a static landing page for the project.

## Why Vercel Shows a Landing Page

The Vercel URL is working, but it is not supposed to run the full dashboard. This project is a Streamlit app, and Streamlit needs a live Python process and browser connection for the interactive UI. Vercel's serverless runtime is not a good fit for that style of app.

The repo includes:

- `vercel.json` so Vercel can deploy cleanly.
- `public/index.html` so the Vercel URL shows a polished project page.
- `app.py` for the real Streamlit dashboard.

## Deploy the Interactive App on Streamlit Cloud

1. Go to `https://share.streamlit.io`.
2. Sign in with GitHub.
3. Create a new app.
4. Select repository: `DEEKSHAPAL/lila_product-assignment`.
5. Select branch: `main`.
6. Set main file path: `app.py`.
7. Deploy.
8. Copy the generated `streamlit.app` URL.
9. Add that URL to `README.md` under `Deployed app`.

## Deploy the Landing Page on Vercel

1. Import the GitHub repo into Vercel.
2. Keep the root directory as the project root.
3. Vercel reads `vercel.json`.
4. Vercel publishes `public/index.html`.

## Submission Recommendation

Submit the GitHub repo link and the Streamlit Cloud URL for the actual dashboard. The Vercel URL can be included as a project landing page, but it should not be treated as the interactive app URL.
