"""Tests for the current global-state RescueRoute interface; standard library only."""
import csv
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import rescueroute_final as rr

HEADERS = {
    'donations': 'donation_id donor_name food_type quantity pickup_area ready_time expiry_time'.split(),
    'recipients': 'recipient_id org_name accepted_food_types capacity area closing_time'.split(),
    'volunteers': 'volunteer_id vehicle_capacity area available_from available_until max_pickups'.split(),
}


def donation(quantity=10, ready='10:00', expiry='12:00', area='Central', food='produce'):
    return dict(donor_name='Market', food_type=food, quantity=quantity, pickup_area=area,
                ready_time=ready, expiry_time=expiry,
                remaining_shelf_life=rr.time_to_minutes(expiry)-rr.time_to_minutes(ready))


def recipient(capacity=30, closing='18:00', area='Central', foods='produce;bakery'):
    return dict(org_name='Community Pantry', accepted_food_types=foods,
                capacity=capacity, area=area, closing_time=closing)


def volunteer(capacity=20, start='09:00', end='17:00', pickups=3, area='Central'):
    return dict(vehicle_capacity=capacity, area=area, available_from=start,
                available_until=end, max_pickups=pickups)


def reset_state():
    for name in ('donations_by_id', 'recipients_by_id', 'volunteers_by_id',
                 'processed_donor_ids', 'processed_recipient_ids', 'processed_volunteer_ids',
                 'invalid_donations', 'fifo_assignments', 'fifo_rejected',
                 'greedy_assignments', 'greedy_rejected'):
        getattr(rr, name).clear()


def run_plan(donations, recipients, volunteers, strategy='fifo'):
    """Test adapter only: call real schedulers and copy ordered outcomes and metrics."""
    reset_state()
    rr.donations_by_id.update(deepcopy(donations))
    rr.recipients_by_id.update(deepcopy(recipients))
    rr.volunteers_by_id.update(deepcopy(volunteers))
    order = (rr.sort_by_arrival_time if strategy == 'fifo'
             else rr.sort_by_remaining_shelf_life)(rr.donations_by_id)
    scheduler = rr.fifo_implementation if strategy == 'fifo' else rr.greedy_implementation
    scheduler(order)
    assigned = getattr(rr, strategy + '_assignments')
    rejected = getattr(rr, strategy + '_rejected')
    outcomes = {a['donation_id']: a for a in assigned + rejected}
    return deepcopy([outcomes[did] for did, _ in order]), deepcopy(rr.calculate_metrics(assigned, rejected))


class FifoTests(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.addCleanup(reset_state)
        self.d = {'D1': donation()}
        self.r = {'R1': recipient()}
        self.v = {'V1': volunteer()}

    def plan(self):
        return run_plan(self.d, self.r, self.v)[0]

    def test_normal_match_and_schema(self):
        a = self.plan()[0]
        self.assertEqual((a['status'], a['recipient_id'], a['volunteer_id'], a['scheduled_time']),
                         ('assigned', 'R1', 'V1', '10:00'))
        self.assertEqual(set(a), {'donation_id', 'recipient_id', 'volunteer_id',
                                  'scheduled_time', 'decision_reason', 'status'})

    def test_fifo_preserves_arrival_not_readiness(self):
        self.d = {'FIRST': donation(20, '11:00', '14:00'), 'URGENT': donation(20, '09:00', '10:00')}
        result = self.plan()
        self.assertEqual([a['donation_id'] for a in result], ['FIRST', 'URGENT'])
        self.assertEqual([a['status'] for a in result], ['assigned', 'unassigned'])

    def test_first_feasible_pair(self):
        self.r = {'bad': recipient(capacity=1), 'first': recipient(), 'last': recipient()}
        self.v = {'bad': volunteer(capacity=1), 'first': volunteer(), 'last': volunteer()}
        self.assertEqual((self.plan()[0]['recipient_id'], self.plan()[0]['volunteer_id']), ('first', 'first'))

    def test_later_recipient_when_first_closed(self):
        self.r = {'early': recipient(closing='10:30'), 'late': recipient()}
        self.v = {'V': volunteer(start='11:00')}
        self.assertEqual(self.plan()[0]['recipient_id'], 'late')

    def test_rejection_constraints_and_explanations(self):
        cases = [
            (donation(food='pro'), recipient(), volunteer(), 'accepts this food type'),
            (donation(), recipient(area='Other'), volunteer(), 'pickup area'),
            (donation(), recipient(capacity=1), volunteer(), 'remaining capacity'),
            (donation(), recipient(), volunteer(area='Other'), 'vehicle capacity'),
            (donation(), recipient(), volunteer(capacity=1), 'vehicle capacity'),
            (donation(), recipient(), volunteer(pickups=0), 'maximum pickups'),
            (donation(), recipient(), volunteer(end='09:00'), 'unavailable'),
            (donation(), recipient(), volunteer(start='12:00'), 'before expiry'),
            (donation(), recipient(closing='09:00'), volunteer(), 'close before'),
        ]
        for d, r, v, reason in cases:
            with self.subTest(reason=reason):
                a = run_plan({'D': d}, {'R': r}, {'V': v})[0][0]
                self.assertEqual(a['status'], 'unassigned')
                for key in ('recipient_id', 'volunteer_id', 'scheduled_time'):
                    self.assertIsNone(a[key])
                self.assertIn(reason, a['decision_reason'])

    def test_no_splitting(self):
        self.r = {'R1': recipient(capacity=6), 'R2': recipient(capacity=6)}
        self.assertEqual(self.plan()[0]['status'], 'unassigned')

    def test_waits_for_availability(self):
        self.v = {'V': volunteer(start='11:15')}
        self.assertEqual(self.plan()[0]['scheduled_time'], '11:15')

    def test_time_boundaries(self):
        cases = [(donation(expiry='10:00'), recipient(), volunteer(), 'unassigned'),
                 (donation(expiry='10:01'), recipient(), volunteer(), 'assigned'),
                 (donation(), recipient(closing='10:00'), volunteer(), 'assigned'),
                 (donation(), recipient(), volunteer(end='10:00'), 'assigned'),
                 (donation(), recipient(), volunteer(end='09:59'), 'unassigned')]
        for d, r, v, status in cases:
            with self.subTest(d=d, r=r, v=v):
                self.assertEqual(run_plan({'D': d}, {'R': r}, {'V': v})[0][0]['status'], status)

    def test_competing_capacity(self):
        self.d = {'A': donation(20), 'B': donation(20)}
        self.assertEqual([a['status'] for a in self.plan()], ['assigned', 'unassigned'])

    def test_vehicle_reuse_and_pickup_limit(self):
        self.d = {str(i): donation() for i in range(3)}
        self.v = {'V': volunteer(capacity=10, pickups=2)}
        self.assertEqual([a['status'] for a in self.plan()], ['assigned', 'assigned', 'unassigned'])

    def test_failed_match_does_not_consume_capacity(self):
        self.d = {'BIG': donation(25), 'SMALL': donation()}
        self.r = {'R': recipient(capacity=25)}
        self.assertEqual([a['status'] for a in self.plan()], ['unassigned', 'assigned'])

    def test_repeatability_and_nonmutation(self):
        before = deepcopy((self.d, self.r, self.v))
        first = self.plan()
        # Direct repeat verifies the scheduler clears its own results, independent of adapter.
        rr.fifo_implementation(rr.sort_by_arrival_time(rr.donations_by_id))
        self.assertEqual(first, rr.fifo_assignments)
        self.assertEqual(before, (self.d, self.r, self.v))

    def test_empty_inputs(self):
        self.assertEqual(run_plan({}, {}, {})[0], [])
        for r, v in [({}, self.v), (self.r, {})]:
            self.assertEqual(run_plan(self.d, r, v)[0][0]['status'], 'unassigned')

    def test_readable_output(self):
        outcomes, _ = run_plan(self.d, self.r, self.v)
        output = io.StringIO()
        with redirect_stdout(output):
            rr.print_results('FIFO', list(self.d.items()), outcomes, [])
        for phrase in ('FIFO', 'D1', 'Community Pantry', 'V1', '10:00', '10 units'):
            self.assertIn(phrase, output.getvalue())


class LoadingTests(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.addCleanup(reset_state)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.patcher = patch.object(rr, '__file__', str(self.root / 'rescueroute_final.py'))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.rows = {'donations': [{'donation_id': 'D1', **donation()}],
                     'recipients': [{'recipient_id': 'R1', **recipient()}],
                     'volunteers': [{'volunteer_id': 'V1', **volunteer()}]}

    def write(self):
        for kind, rows in self.rows.items():
            with (self.assets / (kind+'.csv')).open('w', newline='', encoding='utf-8') as target:
                writer = csv.DictWriter(target, HEADERS[kind], extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)

    def load(self):
        self.write()
        reset_state()
        output = io.StringIO()
        with redirect_stdout(output):
            rr.load_files()
        return output.getvalue()

    def test_duplicate_ids(self):
        for rows in self.rows.values():
            rows.append(dict(rows[0]))
        self.load()
        self.assertEqual([len(x) for x in (rr.donations_by_id, rr.recipients_by_id, rr.volunteers_by_id)], [1, 1, 1])
        self.assertEqual(len(rr.invalid_donations), 0)

    def test_invalid_first_donation_reserves_id_and_is_audited(self):
        good = self.rows['donations'][0]
        self.rows['donations'] = [{**good, 'expiry_time': '09:00'}, good]
        self.load()
        self.assertFalse(rr.donations_by_id)
        self.assertEqual(len(rr.invalid_donations), 1)
        self.assertEqual(rr.calculate_metrics([], [])['Food quantity at risk'], 10)

    def test_invalid_required_fields(self):
        bad = {'donations': {'donation_id': ' ', 'donor_name': ' ', 'quantity': 'abc',
                            'pickup_area': ' ', 'food_type': ' ', 'ready_time': '99:99'},
               'recipients': {'recipient_id': ' ', 'org_name': ' ', 'capacity': 0,
                              'accepted_food_types': '; ;', 'area': ' ', 'closing_time': 'bad'},
               'volunteers': {'volunteer_id': ' ', 'vehicle_capacity': -1, 'area': ' ',
                              'available_from': '99:00', 'available_until': '08:00', 'max_pickups': 0}}
        for kind, fields in bad.items():
            for field, value in fields.items():
                with self.subTest(kind=kind, field=field):
                    original = deepcopy(self.rows)
                    self.rows[kind][0][field] = value
                    self.load()
                    self.assertFalse(getattr(rr, kind+'_by_id'))
                    self.rows = original

    def test_trim_and_numeric_types(self):
        self.rows['donations'][0]['ready_time'] = ' 9:00 '
        self.rows['recipients'][0]['accepted_food_types'] = ' produce ; bakery '
        self.load()
        self.assertEqual(rr.donations_by_id['D1']['ready_time'], '9:00')
        self.assertIsInstance(rr.donations_by_id['D1']['quantity'], int)
        self.assertEqual(rr.recipients_by_id['R1']['accepted_food_types'], 'produce;bakery')

    def test_empty_and_header_only(self):
        self.rows = {kind: [] for kind in HEADERS}
        self.load()
        self.assertFalse(rr.donations_by_id)
        for kind in HEADERS:
            (self.assets/(kind+'.csv')).write_text('')
        rr.load_files()
        self.assertFalse(rr.recipients_by_id)
        self.assertEqual(rr.calculate_metrics([], [])['Donations received'], 0)

    def test_missing_columns(self):
        self.write()
        (self.assets/'donations.csv').write_text('wrong_header\nvalue\n')
        with self.assertRaisesRegex(ValueError, 'missing required columns'):
            rr.load_files()

    def test_missing_file(self):
        with self.assertRaisesRegex(ValueError, 'Cannot load'):
            rr.load_files()

    def test_malformed_rows(self):
        self.write()
        with (self.assets/'donations.csv').open('a') as target:
            target.write('short,row\nX,Market,produce,10,Central,10:00,12:00,extra\n')
        with redirect_stdout(io.StringIO()):
            rr.load_files()
        self.assertEqual(list(rr.donations_by_id), ['D1'])
        self.assertEqual(len(rr.invalid_donations), 2)

    def test_time_validation(self):
        for value in (None, '', '24:00', '12:60', '10', '1:2:3', '-1:30'):
            with self.subTest(value=value):
                self.assertFalse(rr.valid_time(value))
        for value in ('00:00', '23:59', '9:00', ' 09:00 ', '10:0'):
            with self.subTest(value=value):
                self.assertTrue(rr.valid_time(value))


class MetricsTests(unittest.TestCase):
    def tearDown(self):
        reset_state()

    def test_counts_quantities_and_denominators(self):
        _, m = run_plan({'A': donation(), 'B': donation(20, expiry='10:30')},
                        {'R': recipient(capacity=20)}, {'V': volunteer()})
        expected = {'Donations received': 2, 'Donations assigned': 1, 'Donations unassigned': 1,
                    'Food quantity rescued': 10, 'Food quantity at risk': 20,
                    'Recipient utilization (%)': 50, 'Urgent rescue rate (%)': 0}
        for key, value in expected.items():
            self.assertEqual(m[key], value)
        self.assertAlmostEqual(m['Volunteer utilization (%)'], 100/6)

    def test_urgent_cutoff_rounds_up_and_includes_ties(self):
        d = {key: donation(1, expiry=expiry) for key, expiry in
             [('A', '10:30'), ('B', '10:30'), ('C', '11:00'), ('D', '11:00'), ('E', '12:00')]}
        # Only A rescued: cutoff group A+B gives 50%, not 100% or 20%.
        _, m = run_plan(d, {'R': recipient(capacity=1)}, {'V': volunteer()})
        self.assertEqual(m['Urgent rescue rate (%)'], 50)
        d['C']['expiry_time'] = '10:30'
        _, m = run_plan(d, {'R': recipient(capacity=1)}, {'V': volunteer()})
        self.assertAlmostEqual(m['Urgent rescue rate (%)'], 100/3)

    def test_empty_metrics(self):
        _, m = run_plan({}, {}, {})
        self.assertTrue(all(value == 0 for value in m.values()))

    def test_idle_capacity_included(self):
        _, m = run_plan({'A': donation()}, {'R': recipient(capacity=10), 'IDLE': recipient(capacity=90)},
                        {'V': volunteer(capacity=10, pickups=1), 'IDLE': volunteer(capacity=90, pickups=1)})
        self.assertEqual(m['Recipient utilization (%)'], 10)
        self.assertEqual(m['Volunteer utilization (%)'], 10)

    def test_vehicle_capacity_counted_per_allowed_pickup(self):
        _, m = run_plan({str(i): donation() for i in range(3)}, {'R': recipient()},
                        {'V': volunteer(capacity=10, pickups=3)})
        self.assertEqual(m['Food quantity rescued'], 30)
        self.assertEqual(m['Volunteer utilization (%)'], 100)

    def test_metrics_repeatable_and_nonmutating(self):
        run_plan({'D': donation()}, {'R': recipient()}, {'V': volunteer()})
        before = deepcopy((rr.fifo_assignments, rr.fifo_rejected, rr.donations_by_id))
        first = rr.calculate_metrics(rr.fifo_assignments, rr.fifo_rejected)
        self.assertEqual(first, rr.calculate_metrics(rr.fifo_assignments, rr.fifo_rejected))
        self.assertEqual(before, (rr.fifo_assignments, rr.fifo_rejected, rr.donations_by_id))


class IntegrationTests(unittest.TestCase):
    def tearDown(self):
        reset_state()

    def test_sample_metrics_and_repeatable_main(self):
        outputs = []
        for _ in range(2):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(rr.main(), 0)
            outputs.append(output.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(len(rr.fifo_assignments)+len(rr.fifo_rejected), 12)
        m = rr.calculate_metrics(rr.fifo_assignments, rr.fifo_rejected)
        self.assertEqual(m['Food quantity rescued'], 85)
        self.assertEqual(m['Food quantity at risk'], 322)
        self.assertAlmostEqual(m['Urgent rescue rate (%)'], 100/3)
        self.assertAlmostEqual(m['Recipient utilization (%)'], 85/220*100)
        self.assertAlmostEqual(m['Volunteer utilization (%)'], 85/395*100)
        self.assertIn('Greedy-FIFO', outputs[0])

    def test_cli_outside_project_directory(self):
        with tempfile.TemporaryDirectory() as cwd:
            p = subprocess.run([sys.executable, str(Path(rr.__file__).resolve())], cwd=cwd,
                               capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('Comparison', p.stdout)
        self.assertIn('Food quantity rescued', p.stdout)

    def test_import_is_quiet(self):
        p = subprocess.run([sys.executable, '-c', 'import rescueroute_final'],
                           cwd=Path(rr.__file__).parent, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, '')

    def test_missing_assets_cli_error(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory)/'rescueroute_final.py'
            script.write_bytes(Path(rr.__file__).read_bytes())
            p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn('Input error:', p.stdout)
        self.assertNotIn('Traceback', p.stderr)


if __name__ == '__main__':
    unittest.main()
