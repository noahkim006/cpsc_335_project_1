# RescueRoute: run the program and tests

the tests use Python's built-in `unittest` library.

## 1. Extract the package

Keep `rescueroute_final.py`, `test_rescueroute.py`, and `test_greedy.py` in the same folder. Keep the three CSVs in that folder's `assets/` subfolder. Open a terminal in the extracted folder.

## 2. Run all tests

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

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

## 4. Save the report

```bash
python rescueroute_final.py > results.txt
```

`results.txt` is created in your terminal's current folder. It contains the full report, including the comparison table. The application does not automatically create CSV or JSON metric files. `sample_output.txt` contains a report from the bundled sample CSVs. `test_results.txt` records the passing test run used to verify this package.

With the current csv's, each strategy assigns 5 of 12 donations, rescues 85 units, and leaves 322 units at risk. Urgent rescue rate is 33.33%, recipient utilization is 38.64%, and volunteer utilization is 21.52%.
