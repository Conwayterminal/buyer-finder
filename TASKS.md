# Conway Buyer Finder — standing instructions for the automation owner

Goal: every commercial property in NY (city + state), NJ, CT, FL, PA, TX, CA and MA, with owner, principals, contacts, sales, debt, taxes, violations and liens wherever public records carry them, live at https://conwayterminal.github.io/buyer-finder/.

Work through this without asking permission unless a purchase, credential or legal question comes up.

1. Check every GitHub Actions job (.github/workflows/*.yml). On failure: read the log, fix the script, relaunch by pushing (the token cannot dispatch jobs; workflows trigger on push to their script path).
2. When a state job lands, add that state to the Property lookup picker in template.html (setPropState) using the generic card (showPropGeneric). Rebuild site/index.html from template.html (replace __COLS__ with data.json cols).
3. The daily NYC job (update.py, pincus.py, dob_step.py) must write only site/data/NY.json. State jobs own their own site/data/<ST>.json and site/props/<ST>_*.json files. Never let one job rewrite another's files.
4. Never publish phone numbers or emails from Pipedrive on the public page. Public-record contacts (CT registered agents) are fine.
5. Keep every file in site/ under 90 MB — shard large ones (see nyc_assemble.py / index_NY.json pattern).
6. Expand Texas to Tarrant, Collin, Denton, Travis, Williamson, Bexar, Fort Bend, Montgomery (appraisal district downloads; same pattern as tx_universe.py). Expand California to Orange, San Diego, Santa Clara, Alameda, San Francisco (assessor parcel layers; ca_universe.py pattern).
7. Add Florida 2020–2024 sale history from FGDL archived parcel layers.
8. NY State outside NYC: county deed sources for sale dates/prices where any county publishes them.
9. Skip-trace exports (Property lookup → Export buttons) are the input files for BatchData/TLO. When a skip-trace or ATTOM account exists, wire returned contacts behind the agent login only.
10. Keep AUDIT_REPORT.md and README.md current. Report in one paragraph after each pass.

Key files: template.html (UI), data.json (master deals), site/data/*.json (per-market deals), site/props/*.json (per-area property universe), *_universe.py (state builders), nyc_*.py (NYC layers), pd_match.py (Pipedrive match), fl_sunbiz.py (FL officers), ct_reg*.py (CT registry).
