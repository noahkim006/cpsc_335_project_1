# FIFO and greedy metrics comparison

This report compares the current `rescueroute_final.py` using the supplied simulated CSVs and a controlled two-donation fixture from `test_greedy.py`. Results describe assignment decisions in a zero-duration, single-day model, not actual food deliveries or measured food waste.

## Method and definitions

Both strategies receive identical entities and fresh recipient capacities and volunteer pickup limits. Both search recipients first and volunteers second in input order. FIFO considers CSV arrival order. Greedy sorts absolute expiry ascending, then quantity ascending, ready time ascending, and stable arrival order.

| Metric | Definition |
|---|---|
| Received | Unique donation records retained for processing plus invalid donation audit records; duplicate IDs excluded |
| Assigned | Successful whole-donation matches |
| Unassigned | Failed valid matches plus invalid donation audit records |
| Rescued quantity | Sum of assigned donation quantities |
| At-risk quantity | Total known positive quantity minus rescued quantity |
| Urgent rescue rate | Assigned urgent donation count / urgent donation count × 100 |
| Recipient utilization | Rescued quantity / sum of recipient capacity × 100 |
| Volunteer utilization | Rescued quantity / sum(vehicle capacity × maximum pickups) × 100 |

For n valid donations, select the earliest-expiring `ceil(n/4)` records and include all additional records tied at the cutoff. This same urgent group is used for both strategies. Invalid donation records are excluded from urgency because their expiry may not be trustworthy. Unknown/nonpositive quantities contribute zero. Empty denominators return zero; that convention must not be interpreted as evidence of poor performance on an empty dataset.

Differences are greedy minus FIFO. A positive assigned/rescued/urgent-rescue difference can be beneficial; a positive at-risk difference is unfavorable. Utilization alone does not measure fairness or guarantee better service.

## Scenario 1: supplied sample CSVs

The donation file contains 13 data rows, including a repeated D-1001. Twelve unique donations are processed. The repeated R-01 is also excluded. The unique donation quantity totals 407 units. Available recipient capacity totals 220 units; potential volunteer pickup capacity totals 395 units.

| Metric | FIFO | Greedy | Greedy − FIFO |
|---|---:|---:|---:|
| Donations received | 12 | 12 | 0 |
| Donations assigned | 5 | 5 | 0 |
| Donations unassigned | 7 | 7 | 0 |
| Food quantity rescued | 85 | 85 | 0 |
| Food quantity at risk | 322 | 322 | 0 |
| Urgent rescue rate | 33.33% | 33.33% | 0.00 percentage points |
| Recipient utilization | 38.64% | 38.64% | 0.00 percentage points |
| Volunteer utilization | 21.52% | 21.52% | 0.00 percentage points |

Both rescue D-1001 (20), D-1002 (35), D-1003 (15), D-1007 (10), and D-1010 (5). Consideration order differs, but the assignment set does not.

Hand checks:

- Rescued: 20 + 35 + 15 + 10 + 5 = 85 units.
- At risk: 407 − 85 = 322 units.
- Urgent group: D-1008 (11:45), D-1005 (12:15), D-1007 (12:20). Only D-1007 is assigned: 1/3 × 100 = 33.33%.
- Recipient utilization: 85/220 × 100 = 38.64%.
- Volunteer utilization: 85/395 × 100 = 21.52%. The 395 is 25×3 + 40×2 + 15×4 + 60×2 + 20×3.

The observed blockers explain why simply reordering these donations does not improve results. D-1008 and D-1012 lack compatible recipients in their pickup areas. D-1004, D-1005, D-1006, D-1009, and D-1011 lack sufficient remaining compatible recipient capacity when considered. Some could face additional constraints as well; the program reports the first failed stage.

These results establish equal outcomes for this sample only. They do not establish that greedy is unnecessary or that either strategy is globally optimal.

## Scenario 2: controlled competition for capacity

This is the existing `test_urgency_changes_assignment_and_metrics` fixture, verified through the actual schedulers and metric function.

| Donation, in arrival order | Quantity | Ready | Expiry |
|---|---:|---|---|
| LATE | 20 | 10:00 | 14:00 |
| URGENT | 10 | 10:00 | 11:00 |

Both donations are produce in Central. The Community Pantry accepts produce and bakery, has 20 units of capacity, and closes at 18:00. Volunteer V has a 20-unit vehicle, is available 09:00–17:00, and can make three pickups. Its planned transport capacity is therefore 60 units. A whole donation cannot be split.

FIFO assigns LATE first and exhausts recipient capacity. Greedy assigns URGENT first, leaving 10 units of recipient capacity, which cannot fit LATE. Both assignments are scheduled at 10:00. URGENT alone forms the urgent group.

| Metric | FIFO | Greedy | Greedy − FIFO |
|---|---:|---:|---:|
| Donations received | 2 | 2 | 0 |
| Donations assigned | 1 | 1 | 0 |
| Donations unassigned | 1 | 1 | 0 |
| Food quantity rescued | 20 | 10 | −10 |
| Food quantity at risk | 10 | 20 | +10 |
| Urgent rescue rate | 0% | 100% | +100 percentage points |
| Recipient utilization | 100% | 50% | −50 percentage points |
| Volunteer utilization | 33.33% | 16.67% | −16.67 percentage points |

Greedy better serves the earliest deadline, while FIFO rescues more quantity in this fixture. The common assigned-donation count conceals this conflict. The result disproves a claim that the current greedy strategy always maximizes rescued quantity.

## Reproduction

From the folder containing the program, tests, and assets:

```bash
python rescueroute_final.py
python -m unittest test_greedy.GreedyTests.test_urgency_changes_assignment_and_metrics -v
python -m unittest discover -s . -p "test_*.py" -v
```

The first command prints Scenario 1's comparison table. The targeted test verifies Scenario 2 and reports pass/fail, not a printed scenario table. Its fixture is defined in `test_greedy.py`, with the test-only runner in `test_rescueroute.py`. The full adapted suite passed 41 test methods. No runtime speed measurements are claimed.

## Interpretation and limits

The greedy rule is reasonable when imminent expiry matters, but it can lose quantity or strand remaining capacity. FIFO offers arrival-based priority but can let urgent later arrivals go unserved. Neither handles travel time, overlapping trips, repeated-day fairness, unequal recipient needs, or reassignment. Capacity percentages are useful resource summaries, not a standalone objective.

The evidence supports comparing several metrics and explaining the tradeoff. It does not support declaring a universal winning strategy. See `FAIRNESS_DISCUSSION.md` for a short discussion structure.
