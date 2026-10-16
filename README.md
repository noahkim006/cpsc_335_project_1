# RescueRoute

RescueRoute is a command-line Python prototype that matches simulated surplus-food donations to recipients and volunteer drivers. It compares a first-in, first-out (FIFO) baseline with an earliest-expiry greedy strategy and explains each assignment or rejection.

This is an educational single-day simulation. It is not certified for real food handling or emergency operations.

## Setup and execution

Use Python 3.9 or newer. The application and tests use only the Python standard library; no package installation is required. Open a terminal in the project folder. Substitute `py` on Windows or `python3` on macOS/Linux if needed.

Keep these files together:

| Path | Purpose |
|---|---|
| `rescueroute_final.py` | Application, scheduling, explanations, and metrics |
| `test_rescueroute.py` | Loading, FIFO, metrics, and integration tests; shared fixtures |
| `test_greedy.py` | Greedy ordering, constraints, and tradeoff tests |
| `assets/donations.csv` | Donation input |
| `assets/recipients.csv` | Recipient input |
| `assets/volunteers.csv` | Volunteer input |
| `METRICS_COMPARISON.md` | Results, definitions, and interpretation |
| `FAIRNESS_DISCUSSION.md` | Discussion framework and limitations |

Run the application:

```bash
python rescueroute_final.py
```

Run all tests:

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

The verified suite reports **41 tests, OK**. Several methods contain additional subtests. Keep both test files because `test_greedy.py` imports shared fixtures from `test_rescueroute.py`.

Run one test file or the tradeoff case:

```bash
python -m unittest test_rescueroute -v
python -m unittest test_greedy -v
python -m unittest test_greedy.GreedyTests.test_urgency_changes_assignment_and_metrics -v
```

Tests exercise and verify program behavior; they do not display a full metrics report. To view metrics, run the application. Its terminal output includes validation messages, FIFO decisions, greedy decisions, and a final `Comparison` table. To save it:

```bash
python rescueroute_final.py > results.txt
```

`results.txt` is created in the terminal's current folder. There is no automatic CSV/JSON export. The program locates `assets/` relative to its own script, so the script can be launched from another working directory. Missing files or required headers produce `Input error:` on stdout and exit status 1; normal execution returns 0. Unsupported command-line arguments are not parsed: use the commands above rather than relying on flags.

## Data model

| Entity | Required CSV columns |
|---|---|
| Donation | `donation_id, donor_name, food_type, quantity, pickup_area, ready_time, expiry_time` |
| Recipient | `recipient_id, org_name, accepted_food_types, capacity, area, closing_time` |
| Volunteer | `volunteer_id, vehicle_capacity, area, available_from, available_until, max_pickups` |

Accepted food categories are separated with semicolons, such as `produce;bakery`. Quantity and capacities use the same abstract unit throughout a dataset. IDs and text are trimmed. Food/area comparisons are case-sensitive. Times are same-day hour/minute strings such as `09:00`; the current validator also accepts numeric forms such as `9:00` and `10:0`.

Assignments contain `donation_id`, `recipient_id`, `volunteer_id`, `scheduled_time`, `decision_reason`, and `status`. Failed assignments use null recipient, volunteer, and time fields. The loader also computes donation lifetime (`expiry − ready`) in minutes; greedy prioritization uses absolute expiry rather than this lifetime.

## Architecture and data structures

1. `read_rows()` opens and normalizes CSV rows and checks headers and row shape.
2. `load_files()` validates entities and fills dictionaries keyed by ID. Sets detect repeated IDs. Invalid donation records are retained in an audit list when possible.
3. Ordering helpers build FIFO and greedy work lists.
4. Each scheduler starts with fresh recipient-capacity and volunteer-pickup counters, scans feasible pairs, and records successes and failures in separate lists.
5. Explanation helpers describe the decision. `print_results()` displays outcomes in consideration order.
6. `calculate_metrics()` aggregates each strategy's results. `main()` prints their comparison.

Dictionaries support ID lookup; sets support duplicate detection; lists retain assignment history and greedy order. FIFO is passed a `deque`, which is iterated without removing entries. Accepted food categories are stored as a semicolon-separated string and split into a list for matching, rather than stored as sets.

The application uses module-level state. `main()` resets loaded state; each scheduler resets its own results. Direct calls to `load_files()` do not reset state automatically. The test adapter explicitly resets and seeds state, calls the real scheduler, and copies results for independent assertions. Importing the module does not run the application.

## Scheduling rules

### Shared feasibility

Both algorithms choose the first feasible recipient, then the first feasible volunteer in input order. A donation is assigned whole, without splitting, when:

- Recipient and volunteer areas match the donation pickup area.
- The recipient accepts the exact food category and has enough remaining capacity.
- The volunteer vehicle fits the whole quantity and has a pickup slot remaining.
- Pickup time is `max(donation ready time, volunteer available-from time)`.
- Pickup is within volunteer availability, at or before recipient closing, and strictly before expiry.

Successful assignment consumes recipient capacity and one volunteer pickup. Vehicle capacity is reused for each pickup. Failure consumes no resources. Each strategy receives the original capacities independently.

### FIFO

Consider donations in CSV insertion order, treated as arrival order. Readiness does not change queue position. This provides a simple arrival-based baseline; no separate arrival timestamp is present.

### Greedy

Sort by:

1. Earliest absolute expiry time.
2. Smaller quantity when expiry ties.
3. Earlier numeric ready time when expiry and quantity tie.
4. CSV insertion order for any remaining tie, using Python's stable sort.

The retained function name `sort_by_remaining_shelf_life()` is historical; its current first key is absolute expiry. The local goal is to consider the earliest deadlines first, then commit the first feasible pair. It does not maximize total rescued quantity or guarantee a globally optimal plan. See the comparison report for a counterexample.

## Explanations and validation policies

Assignment explanations include organization, volunteer, time, quantity, vehicle capacity, and matching/time conditions. Rejection explanations identify the first failed feasibility stage: recipient compatibility, remaining capacity, suitable vehicle, pickup limit, availability, expiry, or closing time. A message identifies a blocker, not every possible alternative cause. Greedy output also states its priority rule between donations.

The loader validates required IDs/text, positive integer quantities/capacities/pickup limits, time ranges, and volunteer availability order. It trims accepted food categories and rejects empty category lists. Donation expiry must be after readiness in the same-day model. That is window validation, not a check against the real current time.

Duplicate donations use first-record-wins, including an invalid first row with a nonempty ID. Recipient and volunteer IDs are reserved after validation, so an invalid first record for those entities does not reserve the ID. Duplicate rows are logged and excluded from metrics. Invalid donation rows count as unassigned; known positive integer quantities contribute to food at risk. Unknown or nonpositive quantities contribute zero, so quantity totals can understate unknown input. Malformed rows are skipped and audited for donations. Empty and header-only files are allowed; missing required headers are errors.

## Metrics and verified results

Metrics cover received, assigned, unassigned, rescued quantity, at-risk quantity, urgent rescue rate, recipient utilization, and volunteer utilization. The comparison shows greedy minus FIFO; percentage changes are percentage-point differences.

Urgent donations are the earliest-expiring quarter of valid donations, rounded up, including all cutoff ties. Recipient utilization uses all recipient capacity. Volunteer utilization uses all potential pickup-slot capacity: `sum(vehicle capacity × maximum pickups)`. Empty denominators return zero by convention. Full definitions and hand calculations are in `METRICS_COMPARISON.md`.

With the bundled sample, each strategy assigns 5 of 12 donations, rescues 85 units, and leaves 322 units at risk. The controlled test case shows greedy improving urgent rescue while rescuing less total food. Equal sample results do not establish equal behavior on all inputs.

## Complexity

Let D be valid donations, R recipients, V volunteers, and F the maximum food-category string length/list size per recipient, treating time strings and other fields as bounded. ID lookup and set membership are expected O(1).

- CSV loading is linear in input size, including text parsing. Stored entity data is O(D + R + V) when field sizes are bounded.
- FIFO ordering is O(D). Greedy sorting is O(D log D).
- Each scheduler can scan R recipients and V volunteers per donation: O(D × R × (F + V)). With a bounded food vocabulary this simplifies to O(DRV). Rejection diagnostics add O(D(RF + V)), which does not exceed that dominant bound for nonempty R and V.
- Each metric calculation sorts expiry values, O(D log D), then scans results and entity totals. Thus the full FIFO pipeline also includes an O(D log D) metrics step even though FIFO ordering itself is linear.
- Additional working space is O(D + R + V) for orders, results, audit records, and resource counters, excluding input text sizes. Printed report length grows with decisions and explanations.

These are worst-case analytical bounds, not measured execution-time benchmarks.

## Tests and limits

The 41 methods cover normal matches, duplicates, expired/near-expiry windows, incompatible food/areas, insufficient capacities, availability, competing donations, pickup reuse/limits, empty/malformed inputs, repeated calls, sample totals, differing strategy results, and an urgency-versus-quantity fairness case. Temporary input tests do not modify the sample CSVs. Tests verify the implemented contract, including its documented choices.

The prototype assumes zero travel, pickup, and delivery duration; a volunteer can therefore have overlapping scheduled times. Area is exact equality, not distance. No overnight handling, current-clock expiry, donation splitting, reassignment/backtracking, recipient rotation, or starvation prevention is implemented. A single static batch can demonstrate displacement; it cannot establish long-run starvation frequency. No external API, optimization library, dashboard, or routing engine is needed for this scope.

## Project documentation and attribution

`METRICS_COMPARISON.md` records evidence and interpretation. `FAIRNESS_DISCUSSION.md` supplies a discussion framework. Team members are responsible for contribution statements, repository packaging, and presentation materials separately; this README makes no claim about their completion.

Sources used here are the supplied CPSC 335 RescueRoute Group Project Brief, supplied sample CSVs, the current program, and the adapted tests. Inputs are treated as simulated. Python standard-library modules provide CSV parsing, collections, file/path operations, testing, temporary files, mocking, and subprocess execution; no external service is called.

AI assistance was used to revise implementation and adapt tests.
