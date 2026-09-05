# Data & Skip-Trace Vendor Comparison
**Prepared for Conway Property Advisors · September 5, 2026**

## What the portal already covers, and what it can't (why we're buying)

The public-records build now covers every commercial parcel in NYC, Philadelphia, Los Angeles County, NY State, and (as jobs finish today) Massachusetts, Connecticut, New Jersey, Florida and Houston/Dallas — with owner of record, mailing address, building detail, values, and, where public, sales, principals, lenders and violations. Four gaps cannot be closed from public sources, and those define the purchase:

| Gap | Where | Which vendor type fills it |
|---|---|---|
| Buyer/owner **names** | New Jersey (Daniel's Law redaction), California (assessor rolls) | Property-data vendor (recorded-deed data) |
| **Sale prices** | Texas (non-disclosure), California (exact), NY State outside NYC | Property-data vendor |
| **Mortgages / debt** | Every market except NYC | Property-data vendor |
| **Cell phones and emails** for LLC principals and individuals | All markets | Skip-trace vendor (licensed, FCRA/GLBA-gated data) |

Two purchases, two roles: one property-data license, one skip-trace account. The portal's exports are already formatted as the input file for the skip tracer.

---

## Part 1 — Property data: ATTOM vs CoreLogic (Cotality) vs DataTree (First American)

All three license the same raw material — ~3,100 county recorder/assessor offices — and differ in normalization, delivery, and price. Reonomy and PropertyShark are the commercial-only alternatives (Reonomy is owner-linking-focused; PropertyShark is cheap and browser-based but not an API).

| | **ATTOM** | **CoreLogic / Cotality** | **DataTree (First American)** |
|---|---|---|---|
| Coverage | 160M+ parcels, 30B transaction rows, deeds/mortgages/tax/foreclosure, 30+ yr chain of title | Largest deed, mortgage and lien holder (~99.9% of counties); industry ground truth | Title-plant grade; recorded documents **with images**; strongest on complex ownership |
| Fills NJ names? | Yes (recorded deeds pre- and post-redaction; they were named in the Daniel's Law suits, i.e., they have the data) | Yes | Yes |
| Fills CA names & prices? | Yes | Yes | Yes |
| Fills TX prices? | Partial (MLS/modeled, not recorded) | Partial (modeled) | Partial |
| Mortgages / lender / amount | Yes, nationwide | Yes, best-in-class | Yes, with document images |
| Delivery | REST API (JSON), bulk files, Snowflake, **MCP server for AI agents** | API, bulk, enterprise platforms | Web platform + API + bulk license |
| Indicative pricing | Property Navigator seat ~$499/yr; API from roughly **$500/mo** for a few thousand calls; bulk licensing custom (typically five figures/yr for multi-state) | Enterprise, quote only; generally the most expensive; annual contract | Seat plans roughly **$150–$275/mo**; bulk/API quote-based |
| Fit for us | **Best fit.** API + bulk, transparent-ish, commercial-friendly, MCP delivery means Claude can query it directly inside the portal | Best data, worst fit for a brokerage-sized budget and timeline | Best for pulling actual deed/mortgage PDFs in NJ/CT/FL; seat pricing is cheap for agents |

**Recommendation:** ATTOM as the system feed (API for lookups + a one-time bulk pull of NJ, CA, TX, FL, CT, MA, PA commercial parcels to backfill names, prices and mortgages), plus a **DataTree seat or two** for agents who need to open the recorded document itself. Skip CoreLogic unless ATTOM's quote comes back above CoreLogic's, which is unlikely.

Ask ATTOM for: (1) bulk "Assessor + Recorder + Mortgage" extract for commercial use codes in NJ/CA/TX/FL/CT/MA/PA, (2) API access with 20–50k calls/month, (3) MCP access so the portal's Research button can pull ATTOM records live. Get the quote in writing with per-record and per-state terms.

---

## Part 2 — Skip tracing: BatchLeads/BatchSkipTracing vs TLOxp (TransUnion)

| | **BatchLeads / BatchSkipTracing (BatchData)** | **TLOxp (TransUnion)** |
|---|---|---|
| Built for | Real-estate investors and brokers; bulk CSV upload and API | Law enforcement, collections, legal; single-subject investigations |
| Corporate/LLC handling | Purpose-built "behind the corporate veil" linking of LLCs and trusts to individuals — the exact problem we have | Strong relationship mapping, but one subject at a time; requires a person or entity as input |
| Right-party contact rate (vendor-reported) | ~76% | Not published; generally regarded as the deepest data (credit header, carrier, utility) |
| Pricing | **$0.09–$0.15 per matched record**, pay-per-match, no contract; platform from $119/mo (BatchLeads) or API with no minimums; enterprise from ~$2,000/mo for 100k records | Quote-based; typically **~$1–3 per search** plus a monthly platform minimum; annual contract; requires permissible-purpose certification and site inspection |
| Speed / integration | Minutes for bulk; API in milliseconds; direct CSV upload | Interface dated; not designed for bulk; API exists but is enterprise-gated |
| Compliance | DNC scrubbing built in; TCPA tooling | FCRA/GLBA/DPPA-grade; you certify purpose |
| Fit for us | **Primary.** Feed the portal's skip-trace CSVs (thousands of LLC owners per borough/county) and get cells/emails back the same day. Cost for the whole NYC unresolved list (~30k entities) ≈ $3–5k. | **Secondary.** Use for the high-value misses — the 5% BatchData can't hit on a $20M building — where a $3 deep search is trivial. |

Alternatives worth a quick quote: **REISkip** (~$0.15/record, 85–90% match, real-estate focused), **PropStream** (bundles property data + skip tracing at ~$99/mo + per-record), **IDI/idiCORE** (TLO-class data, somewhat friendlier pricing). LexisNexis Accurint is the other TLO-class option; same cost profile, same single-subject workflow.

**Recommendation:** open a BatchData account first (pay-per-match, no contract), run the NYC skip-trace export through it this week, and measure the hit rate on your own data before committing to anything annual. Add TLOxp (or IDI) only for the residual high-value names.

---

## How the two plug into the portal

1. **ATTOM** → nightly job pulls recorded deeds and mortgages for the seven non-NYC states and writes buyer name, price, lender and loan into the same fields NYC already has. The Property card's Debt section lights up everywhere.
2. **BatchData** → the "Export skip-trace list" CSV goes in; the returned file (entity → person, cell, email, address) is loaded back so the card shows the contact, and the Pipedrive match runs on the new names. Cells/emails stay behind the agent's login (same pattern as Pipedrive today — nothing personal on the public page).
3. **Compliance**: every number is scrubbed against the National DNC before it reaches an agent's dialer; TCPA consent language goes into the Aloware script.

## Budget summary (order-of-magnitude, pending quotes)

| Item | One-time | Recurring |
|---|---|---|
| ATTOM bulk backfill (7 states, commercial) | $10–25k | — |
| ATTOM API (lookups + MCP) | — | $500–1,500 / mo |
| DataTree seats (2) | — | $300–550 / mo |
| BatchData skip trace — initial NYC + CT + FL + PA unresolved (~60–80k entities) | $6–12k | — |
| BatchData ongoing (new owners monthly) | — | $200–600 / mo |
| TLOxp (residual high-value) | — | $300–500 / mo min + per search |

I can request the ATTOM and BatchData quotes on your behalf as soon as you say go; both need a company email and a stated use (brokerage prospecting on commercial property, which is permissible for both).
