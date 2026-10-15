# RescueRoute changes

Scope: implements items 1–4 of the previous review: metrics, explanations, ordering, and validation. Existing dictionaries, sets, assignment schema, separate schedulers, and capacity bookkeeping are retained. No full project test suite or README rewrite was added.

## 1. Metrics and comparison

`calculate_metrics()` derives totals from each scheduler's assignments and rejections without changing the matching decisions. Both strategies start with separate resource counters and use the same input.

- Received: unique donation IDs retained for processing plus invalid donation records. Duplicate IDs are excluded and logged. A missing ID or malformed row counts as an invalid record.
- Assigned/unassigned: successful matches versus failed matches plus invalid records.
- Rescued: sum of successfully assigned quantities.
- At risk: total known positive quantity minus rescued quantity. Unknown, noninteger, or nonpositive quantities contribute zero; the program states this limitation.
- Urgent: earliest-expiring quarter of valid donations, rounded up, including every donation tied at the cutoff. Urgent rescue rate uses the same group for both strategies. Invalid rows lack trustworthy expiry and are excluded from this group.
- Recipient utilization: rescued quantity / total recipient capacity.
- Volunteer utilization: rescued quantity / sum(vehicle capacity × maximum pickups). This measures utilization of all potential pickup slots, including unused volunteers. It avoids misleading values above 100% merely because a vehicle makes several pickups.
- Empty denominators produce zero. Percentage differences are percentage points. The comparison reports greedy minus FIFO, without claiming greedy always wins.

## 2. Explainability

`assignment_reason()` reports organization, volunteer, time, quantity, vehicle capacity, compatibility, and time constraints. `print_results()` replaces raw dictionary dumps with per-donation messages and prints the greedy priority rule between decisions.

`rejection_reason()` repeats the feasibility filters without modifying resources. It finds the first stage that eliminates all remaining candidates: recipient food/area compatibility, recipient capacity, vehicle food-carrying capacity/area, remaining pickups, availability, expiry, or recipient closing time. This identifies a concrete blocker rather than reporting that no pair exists. Multiple blockers can exist; the message reports the first failed stage, not every possible cause.

## 3. Ordering fixes

FIFO uses CSV insertion order as arrival order. Ready time only determines the earliest feasible pickup. No separate arrival timestamp exists in the supplied schema.

Greedy uses ascending absolute expiry time, ascending quantity, ascending numeric ready time, then stable CSV order. The function's original name is retained to minimize changes, although its key now uses expiry. Smaller-quantity tie-breaking is preserved from the original implementation; the brief's larger-quantity example is optional.

FIFO's pair-search block now uses the same recipient-first, volunteer-second order as greedy. This isolates donation priority as the difference between strategies. Both retain independent recipient capacity and pickup counters.

Pickup must occur strictly before expiry. Closing and availability endpoints remain inclusive.

## 4. Validation and execution

`read_rows()` centralizes script-relative file paths, UTF-8 BOM handling, whitespace cleanup, required-header checks, and malformed-row checks. Empty files yield empty datasets; missing files and missing headers produce a clear error and exit status 1. Normal input returns status 0. The existing `assets/` layout is retained. `nullcontext` retains the existing validator block indentation and avoids reindenting most of the loader; the actual file context is managed inside `read_rows()`.

The loader additionally checks donor name, pickup area, recipient ID, whitespace-only fields, and reversed volunteer availability. Semicolon-separated accepted food values are trimmed and must contain a nonempty category. Food and area matching remain case-sensitive, preserving the existing convention.

Invalid donation rows remain in an audit list with specific reasons and known quantities. Expiry at or before readiness is an invalid same-day window, not evidence of current real-world spoilage. Duplicate donation IDs follow first-record-wins, even if the first row is invalid; subsequent copies are logged and excluded from totals.

`main()` clears loaded state and the schedulers clear previous results. The main guard allows importing functions without automatically loading files. These small supporting changes allow repeatable verification.

## Assumptions and limits

This remains a simulated, single-day assignment prototype. Travel, pickup, and delivery duration are zero. There is no current-time input, overnight scheduling, or prevention of simultaneous trips. Real routing is optional in the brief. Invalid records with unknown quantities cannot contribute an exact at-risk quantity. Header-only and empty datasets are valid. A missing required header is an error rather than an empty dataset.

## Verification

20 temporary behavior assertions passed: sample execution and totals, duplicate exclusion, FIFO/greedy competition and different urgent rescue rates, capacity rejection explanation, repeated scheduler calls, expiry boundary, empty inputs, missing headers/files, invalid donation quantity accounting, and reversed volunteer availability. These checks do not replace the still-required submitted automated test suite.

With the supplied sample CSVs, both strategies assign 5 of 12 donations, rescue 85 units, leave 322 units at risk, and rescue 33.33% of the urgent group. Identical results are valid for this dataset.

## Every changed line

The following map compares the original uploaded file with the delivered file. “After N” identifies an insertion or deletion boundary. `rescueroute_changes.diff` contains every exact addition (`+`) and subtraction (`-`); its hunk headers give original and updated line numbers. The original upload is the comparison baseline. The main changes are additions; the two scheduling functions and original validation blocks remain recognizable.

| Original lines | Updated lines | Change |
|---|---|---|
| after 1 | 2–3 | insert |
| after 10 | 13–14 | insert |
| 24 | 28 | replace |
| after 47 | 52–74 | insert |
| 50–56 | 77 | replace |
| after 65 | 87–103 | insert |
| after 68 | 107 | insert |
| after 79 | 119 | insert |
| 86 | 126–127 | replace |
| after 95 | 137 | insert |
| after 104 | 147 | insert |
| 116 | 159 | replace |
| 118–120 | 161–164 | replace |
| 125–136 | 169 | replace |
| 154–160 | 187–189 | replace |
| after 166 | 196–198 | insert |
| 184 | 216 | replace |
| 213 | 245 | replace |
| 221–226 | 253–254 | replace |
| after 272 | 301–304 | insert |
| 294 | 326 | replace |
| 299 | 331 | replace |
| 304 | 336 | replace |
| 306 | 338 | replace |
| after 308 | 341–342 | insert |
| 322–333 | 356–361 | replace |
| 335–348 | 363–378 | replace |
| after 349 | 380–382 | insert |
| 355–364 | after 387 | delete |
| 373 | 396 | replace |
| 380 | after 402 | delete |
| 388 | 410 | replace |
| after 394 | 417–418 | insert |
| 409 | 433 | replace |
| 427 | 451 | replace |
| 444–448 | 468–469 | replace |
| 470 | 491 | replace |
| 476–486 | 497–618 | replace |
