# Conway Buyer Finder
Live: https://conwayterminal.github.io/buyer-finder/  ·  Brief for autonomous runs: `TASKS.md`

A public-records commercial real estate database for Conway Property Advisors: every commercial parcel in eight states with owner of record, true owner/principals where filed, contacts, sale history, debt, taxes, violations and liens where public — plus buyer search across ~460k transactions.

## Two modes
- **Buyer search** — address/neighborhood + unit count + type + radius → who bought nearby, $/SF vs area, buyer profiles (portfolio, lenders, leverage, refis, resales, Pipedrive/Aloware links, research).
- **Property lookup** — state → borough/town/county → address or parcel id → full property card; skip-trace and owner CSV exports per area.

## Coverage (Sept 2026)
| Market | Property layer | Source | Names | Sales | Debt | Violations/liens |
|---|---|---|---|---|---|---|
| NYC | 269,761 lots | PLUTO, DOF roll, ACRIS, HPD, DOB | HPD principals, DOB signers, deed grantees | all deeds any price since 2010 | all mortgages | HPD/DOB/ECB, tax liens |
| NY State | 262,872 | State assessment roll | owner of record | none on roll | — | — |
| New Jersey | 355,763 | MOD-IV composite + SR-1A | withheld by state (mailing addr) | any price since 2020 | — | — |
| Massachusetts | 229,032 | MassGIS statewide | owner of record | last sale | — | — |
| Connecticut | (job running) | CAMA/parcel layer + Business Registry | owner + registry principals, agent phone/email | any price since 2020 | — | — |
| Philadelphia | 111,625 | OPA + L&I | owner, c/o | any price | — | L&I open violations |
| Texas (Harris, Dallas) | 302,821 | HCAD, DCAD | owner of record | transfer dates only (non-disclosure) | — | — |
| Los Angeles County | 209,328 | Assessor parcel layer | not public | Prop 13 base year, est. price | — | — |
| Florida (67 counties) | 551,606 + Broward | DOR NAL + Sunbiz | owner + Sunbiz officers | last two sales | — | — |

## Jobs (GitHub Actions, `.github/workflows/`)
`daily` (NYC, 6am ET daily) · `acris_full` (monthly) · `dob_full` (weekly) · `sunbiz` (quarterly) · `ma` `ct` `nj` `fl` `pa` `tx` `ca` `nys` (weekly). Jobs are launched by pushing a change to their script. Each writes only its own market files; merges disable rename detection.

## Files
`template.html` → `site/index.html` (`__COLS__` substituted) · `data.json` master (NYC + legacy) · `site/data/<ST>.json` markets · `site/props/<ST>_<area>.json` property cards (+ `index_NY.json`, `*_towns.json`, `FL_counties.json`) · `site/props/hist/` NYC recorded histories.

## Privacy
Only public records are published. Pipedrive contacts are never on the page (IDs/names only; phone/email fetched live with the agent's own token). No captcha circumvention, no people-search scraping.
