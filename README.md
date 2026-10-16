# cpsc_335_project_1
# RescueRoute

RescueRoute is a command-line Python that matches simulated surplus-food donations to recipients and volunteer drivers.

## Setup and execution

The application and tests use only the Python standard library; no package installation is required. Open a terminal in the project folder.

Running the application:

```bash
python rescueroute.py
```

Run all tests:

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

Run one test file or the tradeoff case:

```bash
python -m unittest test_rescueroute -v
python -m unittest test_greedy -v
python -m unittest test_greedy.GreedyTests.test_urgency_changes_assignment_and_metrics -v
```

These commands verify program behavior; they do not display a full metrics report; Metrics are located at the end of a normal run of the program
`results.txt` is created in the terminal's current folder.

## Data model

| Entity | Required CSV columns |
|---|---|
| Donation | `donation_id, donor_name, food_type, quantity, pickup_area, ready_time, expiry_time` |
| Recipient | `recipient_id, org_name, accepted_food_types, capacity, area, closing_time` |
| Volunteer | `volunteer_id, vehicle_capacity, area, available_from, available_until, max_pickups` |

Accepted food categories are separated with semicolons, such as `produce;bakery`. Food/area comparisons are case-sensitive. Times are same-day hour/minute strings such as `09:00`; the current validator also accepts numeric forms such as `9:00` and `10:0`.

Assignments contain `donation_id`, `recipient_id`, `volunteer_id`, `scheduled_time`, `decision_reason`, and `status`. Failed assignments use null recipient, volunteer, and time fields. The loader also computes donation lifetime (`expiry − ready`) in minutes; greedy prioritization uses absolute expiry rather than this lifetime.

## Architecture and data structures in RescueRoute

1. `read_rows()` opens and normalizes CSV rows and checks headers and row shape.
2. `load_files()` validates entities and fills dictionaries keyed by ID. Sets detect repeated IDs. Invalid donation records are retained in an audit list when possible.
3. Ordering helpers build FIFO and greedy work lists.
4. Each scheduler starts with fresh recipient-capacity and volunteer-pickup counters, scans feasible pairs, and records successes and failures in separate lists.
5. Explanation helpers describe the decision. `print_results()` displays outcomes in consideration order.
6. `calculate_metrics()` aggregates each strategy's results. `main()` prints their comparison.

Dictionaries support ID lookup; sets support duplicate detection; lists retain assignment history and greedy order. FIFO is passed a `deque`, which is iterated without removing entries.

## Scheduling rules

### Shared feasibility

Both algorithms choose the first feasible recipient, then the first feasible volunteer in input order. A donation is assigned when:

- Recipient and volunteer areas match the donation pickup area.
- The recipient accepts the exact food category and has enough remaining capacity.
- The volunteer vehicle fits the whole quantity and has a pickup slot remaining.
- Pickup time is `max(donation ready time, volunteer available-from time)`.
- Pickup is within volunteer availability, at or before recipient closing, and strictly before expiry.

Successful assignment consumes recipient capacity and one volunteer pickup. Vehicle capacity is reused for each pickup. Failure consumes no resources. Each strategy receives the original capacities independently.

### FIFO

Take in donations by CSV insertion order, treated as arrival order. Readiness does not change queue position. This provides a simple arrival-based baseline; no separate arrival timestamp is present.

### Greedy

Sort by:

1. Earliest absolute expiry time.
2. Smaller quantity when expiry ties.
3. Earlier numeric ready time when expiry and quantity tie.
4. CSV insertion order for any remaining tie, using Python's stable sort.

## Explanations and validation policies

Assignment entries include organization, volunteer, time, quantity, vehicle capacity, and matching/time conditions. Assignment rejections identify the first failed feasibility stage: recipient compatibility, remaining capacity, suitable vehicle, pickup limit, availability, expiry, or closing time. A message identifies a blocker, not every possible alternative cause.

The loader validates required IDs/text, positive integer quantities/capacities/pickup limits, time ranges, and volunteer availability order. It trims accepted food categories and rejects empty category lists. Donation expiry must be after readiness in the same-day model. That is window validation, not a check against the real current time.

## Metrics and verified results

Metrics include received, assigned, unassigned, rescued quantity, at-risk quantity, urgent rescue rate, recipient utilization, and volunteer utilization. The comparison shows greedy minus FIFO; percentage changes are percentage-point differences.

Urgent donations are the earliest-expiring quarter of valid donations, rounded up, including all cutoff ties. Volunteer utilization uses all potential pickup-slot capacity: `sum(vehicle capacity × maximum pickups)`.

With the bundled sample, each strategy assigns 5 of 12 donations, rescues 85 units, and leaves 322 units at risk. The controlled test case shows greedy improving urgent rescue while rescuing less total food.

## Complexity

Let D be valid donations, R recipients, V volunteers, and F the maximum food-category string length/list size per recipient, treating time strings and other fields as bounded. ID lookup and set membership are expected O(1).

- CSV loading is linear in input size, including text parsing. Stored entity data is O(D + R + V) when field sizes are bounded.
- FIFO ordering is O(D). Greedy sorting is O(D log D).
- Each scheduler can scan R recipients and V volunteers per donation: O(D × R × (F + V)). With a bounded food vocabulary this simplifies to O(DRV). Rejection diagnostics add O(D(RF + V)), which does not exceed that dominant bound for nonempty R and V.
- Each metric calculation sorts expiry values, O(D log D), then scans results and entity totals. Thus the full FIFO pipeline also includes an O(D log D) metrics step even though FIFO ordering itself is linear.
- Additional working space is O(D + R + V) for orders, results, audit records, and resource counters, excluding input text sizes. Printed report length grows with decisions and explanations.

## Individual Contribution Statements
- Noah Kim) Created data set, implemented data loading from files and FIFO / Greedy algorithms with Steven Pettis.

## Project documentation and attribution

Sources used here are the supplied CPSC-335 RescueRoute Group Project Brief and CPSC-335 class slides units 1-7. Python standard-library modules provide functions to the system as described in https://docs.python.org/3/library/index.html
