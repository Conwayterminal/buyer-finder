# Conway Buyer Finder — standing task brief (for Cowork / Claude Code)

**Live site:** https://conwayterminal.github.io/buyer-finder/  **Repo:** github.com/Conwayterminal/buyer-finder (this one — not the empty `Conwayterminal-buyer-finder`).

## Goal
Every commercial property in NY (city + state), NJ, CT, FL, PA, TX, CA and MA, with owner of record, true owner/principals, contacts, sale history, debt, taxes, violations and liens wherever public records carry them — searchable by address (Property lookup) and by buyer (Buyer search), refreshed automatically, exportable for skip tracing.

## How the system works
- `site/index.html` is built from `template.html` (replace `__COLS__` with `json.dumps(data.json cols)`). Never edit index.html directly.
- Buyer search reads `site/data/<ST>.json`; Property lookup reads `site/props/<ST>_<area>.json` (+ `index_NY.json`, `*_towns.json`, `*_counties.json`).
- One GitHub Actions job per market: `daily.yml` (NYC deeds via PincusCo + ACRIS backfill + DOB step), `acris_full.yml`, `dob_full.yml`, `sunbiz.yml`, `ma.yml`, `ct.yml`, `nj.yml`, `fl.yml`, `pa.yml`, `tx.yml`, `ca.yml`, `nys.yml`. Each writes only its own market files. Jobs are triggered by pushing a change to their script (`push: paths`); the token can't dispatch manually.
- All jobs `git pull --rebase -X theirs` before push and retry; publish step never fails the job.
- Generic property card: `showPropGeneric` in template.html (MA/PA/CA/NYS use it); NYC uses `showProp`.

## Rules
1. Never publish phone numbers or emails from Pipedrive on the public page (IDs/names only; details load live with the agent's own token).
2. Daily NYC job writes only `site/data/NY.json`.
3. Public-records data only; do not scrape captcha-protected sites; no bootlegged people-search data.
4. Every state job must produce: parcel id, address, town/county, lat/lng, type, owner, mailing, llc flag, sf, units, yb, lot, value, last sale/price where public.

## Checklist (work through without asking; only ask for purchases, credentials, legal calls)
- [ ] Check every job; on failure read the log, fix, relaunch by push.
- [ ] Wire finished states into Property lookup picker (CT, NJ, FL, TX, MA when their files land).
- [ ] Verify NYC ACRIS full history populated `debt`, `hist` and `site/props/hist/`.
- [ ] Texas: add Tarrant, Collin, Denton, Travis, Williamson, Bexar, Fort Bend, Montgomery CADs. Pattern = `tx_universe.py` (owner, mailing, deed date, appraised value, SF, units; Census geocode cached in tx_geo.json; write `site/props/TX_<County>.json` and append to `site/data/TX.json`).
  - Tarrant: PropertyData-Commercial delimited (`|`) file from tad.org/resources/data-downloads.php (site blocks non-browser UAs — fetch from Actions with a browser UA; if blocked, use the ArcGIS parcel service `https://tad.newedgeservices.com/arcgis/rest/services/OD_TAD/OD_Parcels/MapServer/0` for TAXPIN→centroid and the PropertyData file for attributes). Layout doc: PropertyData&PropertyLocation.
  - Travis (TCAD): traviscad.org → Public Information → appraisal roll export zip (fixed-width; layout PDF on same page). Bexar (BCAD): bcad.org → Data Downloads. Collin: collincad.org → Downloads. Denton: dentoncad.com/data-downloads (accessible). Fort Bend: fbcad.org → data downloads. Montgomery: mcad-tx.org → downloads. Williamson: wcad.org → data downloads. Most publish a "PACS export" zip (appraisal roll .txt + layout .pdf); parse with the layout.
- [ ] California: add Orange, San Diego, Santa Clara, Alameda, San Francisco assessor rolls. Pattern = `ca_universe.py` (no owner names anywhere in CA public rolls; use base year / assessed value). Sources: Orange — ocgis parcels FeatureServer; San Diego — SanGIS parcels (SDGIS FeatureServer, use codes); Santa Clara — county open data parcels; Alameda — ACGOV parcels; SF — data.sfgov.org "Assessor Historical Secured Property Tax Rolls" (has use code, sqft, units, base year values; no names).
- [ ] Florida 2020–2024 back-history from FGDL annual parcel files.
- [ ] NY State: county deed sources for sale dates/prices (start with Nassau, Suffolk, Westchester).
- [ ] Massachusetts Secretary of State principals for LLC owners.
- [ ] Keep `AUDIT_REPORT.md` and `README.md` current; one-paragraph status after each pass.

## Pending purchases (owner decision)
ATTOM (names/prices/mortgages for NJ, CA, TX, others), BatchData skip trace, DataTree seats, TLOxp for residuals. See Vendor_Comparison in outputs.
