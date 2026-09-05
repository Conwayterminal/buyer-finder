# Conway Buyer Finder — Readiness Report
**For:** Tuesday buyer-portal meeting · **Prepared:** Saturday, September 5, 2026
**Live site:** https://conwayterminal.github.io/buyer-finder/ (add to iPhone home screen)

## Audit result: ready
Every deal in the system passed the integrity check: valid date, price ≥ $500k, map coordinates, buyer/owner field, matching column structure. 2,488 exact duplicate rows and one bad-date row were removed in the final pass. All four markets were load-tested end to end (search → results → buyer profile).

**122,763 commercial deals · ~$399 billion in volume · 4 states · refreshed daily at 6 am ET, seven days a week.**

## Coverage by market

| | New York City | Connecticut | New Jersey | Florida |
|---|---|---|---|---|
| Deals ($500k+) | **34,823** | **10,695** | **52,801** | **24,444** |
| Period | Sep 2020 – Sep 2026 | Sep 2020 – Jun 2026 | Sep 2020 – Jun 2026 | **Jan 2025 – Jun 2026** |
| Geography | Manhattan, Brooklyn, Queens, Bronx | All 169 towns | All 21 counties | All 67 counties |
| Buyer resolved to a person/firm | 73% (25,525) | 83% (8,835) | 0% — state redacts names | 82% (19,971) |
| Distinct named buyers | 16,740 | 7,572 | — | 15,369 |
| Buyer mailing address | 100% | 100% | 49% | 100% |
| Lender / loan / leverage | 22,513 deals | — | — | — |
| Refis / resales tracked | 6,590 / 2,171 | — | — | — |
| Permit-filing contacts (DOB) | 18,656 deals | — | — | — |
| State registry principals | — (HPD instead) | 6,304 deals | — | 16,551 deals |
| Registered agent phone/email | — | **6,000 phones, 6,000+ emails** | — | agent name only |
| **In Pipedrive** | **7,568** | **1,388** | — | 73 |
| …with Aloware link | 7,429 | 1,386 | — | 72 |

## What the portal does (demo script)
1. **Market picker** → type an address or town, unit count, asset type, radius → **Find buyers**.
2. Results: buyer, date, units, SF, price, **$/sf vs. area** (Paid up / At market / Bargain), financing, distance. Sort any column.
3. Tap a buyer → **profile**: total bought, deal count, units, pricing behavior (aggressive vs. bargain hunter), lenders and leverage, refis, resales, every purchase on a timeline, entities used, mailing addresses, state-registry principals, permit signers, **In Pipedrive** with links to the Pipedrive and Aloware records.
4. **Research this buyer** → live search of PincusCo, TRD, Commercial Observer and the web (agent enters their API key once).
5. **Top buyers** tab, **Research all shown** (batch), filters for repeat buyers / named only / in or not in Pipedrive, **Export CSV**, and one-tap links to the deed PDF (NYC), assessor card (CT), county records (NJ).

## Suggested talking points
- NYC is the deepest dataset anywhere outside PincusCo: deed, owner, HPD principal, permit signer, lender, leverage, resale — all on one screen.
- Connecticut is the first market with **direct contact info from public records** (registered-agent phone/email on ~6,000 deals).
- **"Not in Pipedrive"** filter = the firm's prospecting list: named buyers with no CRM contact.
- Phone/email from Pipedrive load live per agent using their own token; nothing from the CRM is published on the public page.

## Known gaps (state these plainly)
1. **New Jersey buyer names.** The state blanks grantee/grantor names statewide (Daniel's Law), and the county portals are captcha-protected. Fix: a data subscription (PropertyShark ~$150–250/mo, or ATTOM/CoreLogic API for full automation). Until then, each NJ deal links to NJParcels, the county clerk and PropertyShark.
2. **Florida history starts Jan 2025.** The state roll only carries the last two sales, so 2020–2024 Florida deals need the archived yearly rolls (FGDL). Achievable; about a week of work.
3. **Direct cell/email for owners** beyond CT agents and Pipedrive requires a licensed skip-trace provider (BatchSkipTracing / TLO / LexisNexis). The portal is built to send name + mailing address and receive contacts back once an account exists.
4. **Name-only Pipedrive matches** (vs. phone/email-confirmed) are labeled "confirm it's the same person." Common names can collide.

## Operations
- Hosting: GitHub Pages on the Conwayterminal account, free. Daily job runs on GitHub's servers; nothing to maintain.
- Data sources (all public): NYC DOF, ACRIS, PLUTO, HPD, DOB; PincusCo public feed; CT CAMA/Parcel layer and Business Registry; NJ SR-1A and MOD-IV; Florida DOR NAL rolls and Sunbiz.
- Quarterly automatic refresh of Sunbiz officers; CT registry refresh runs with the daily job.
- Security: the GitHub token used for setup can be revoked at github.com/settings/personal-access-tokens; the daily job uses GitHub's own credentials.

## Next steps (proposed order)
1. Pick the skip-trace vendor and NJ data vendor; I wire both in.
2. Florida 2020–2024 back-history from FGDL archives.
3. Pipedrive API token for the daily job so new buyers are matched automatically.
4. Merge into Conway Terminal once the standalone version is approved.
