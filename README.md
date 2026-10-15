# RescueRoute: run the program and tests

Requires Python 3.9 or newer. No third-party packages are needed: the tests use Python's built-in `unittest` library.

## 1. Extract the package

Keep `rescueroute_final.py`, `test_rescueroute.py`, and `test_greedy.py` in the same folder. Keep the three CSVs in that folder's `assets/` subfolder. Open a terminal in the extracted folder.

## 2. Run all tests

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

On Windows, `py` may be used instead of `python`; on macOS/Linux, `python3` may be needed. Expected result: `Ran 41 tests` followed by `OK`. Parameterized subtests check additional individual cases within these 41 methods. Any failure produces a traceback and a nonzero exit status.

Run either file separately:

```bash
python -m unittest test_rescueroute -v
python -m unittest test_greedy -v
```

The greedy tests import shared fixtures from `test_rescueroute.py`, so retain both files even when running only the greedy tests.

## 3. Run the program and view metrics

```bash
python rescueroute_final.py
```

The terminal first displays validation messages and FIFO/greedy decisions. The metrics appear near the end under `Comparison`. Columns are FIFO, Greedy, and Greedy-FIFO. Percentage differences are percentage points.

Tests verify metrics internally and capture most application output; running the tests does not display the full application report or automatically export metrics.

## 4. Save the report

```bash
python rescueroute_final.py > results.txt
```

`results.txt` is created in your terminal's current folder. It contains the full report, including the comparison table. The application does not automatically create CSV or JSON metric files. `sample_output.txt` contains a report from the bundled sample CSVs. `test_results.txt` records the passing test run used to verify this package.

With the bundled data, each strategy assigns 5 of 12 donations, rescues 85 units, and leaves 322 units at risk. Urgent rescue rate is 33.33%, recipient utilization is 38.64%, and volunteer utilization is 21.52%.

## Definitions and assumptions

- FIFO uses CSV insertion order as arrival order.
- Greedy uses earliest expiry, then smaller quantity, then earlier ready time, then stable CSV order.
- Pickup is strictly before expiry; recipient closing and volunteer end times are inclusive.
- Urgent means the earliest-expiring quarter of valid donations, rounded up, including cutoff ties.
- Volunteer utilization divides rescued quantity by sum(vehicle capacity × maximum pickups), including idle volunteers.
- Invalid donation records count as unassigned; duplicate IDs do not count twice. Unknown quantities contribute zero. The first donation record reserves its ID even if invalid.
- Empty denominators produce zero.
- This is a single-day simulation with zero-duration pickup/delivery, not real route planning.

## How the tests were adapted

See `TEST_CHANGES.md` for interface changes, altered expectations, scope, and remaining limitations. The application is byte-for-byte unchanged from the previously delivered updated program.
