# Conway Buyer Finder
Live site: https://conwayterminal.github.io/buyer-finder/

Daily-updated database of commercial real estate buyers. NYC now (every recorded $500k+ sale in Manhattan, Brooklyn, Queens, Bronx since Sept 2020, with deed grantee, resolved owner, HPD principal, lender, leverage, refis and resales). CT, NJ, FL to follow.

- `site/index.html` — the dashboard (published by GitHub Pages)
- `data.json` — the database
- `pincus.py` — daily: today's closings from PincusCo's public feed
- `update.py` — daily: ACRIS/PLUTO/HPD backfill once the city posts recorded deeds
- `.github/workflows/daily.yml` — runs both at 6:00 am ET every day and republishes
