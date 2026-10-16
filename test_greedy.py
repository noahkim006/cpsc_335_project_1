"""Greedy priority, fairness tradeoffs, explanations, and shared constraints."""
import io
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
import rescueroute_final as rr
from test_rescueroute import donation, recipient, volunteer, reset_state, run_plan


class GreedyTests(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.addCleanup(reset_state)
        self.d = {'LATE': donation(20, expiry='14:00'), 'URGENT': donation(10, expiry='11:00')}
        self.r = {'R': recipient(capacity=20)}
        self.v = {'V': volunteer()}

    def test_urgency_changes_assignment_and_metrics(self):
        fifo, fm = run_plan(self.d, self.r, self.v)
        greedy, gm = run_plan(self.d, self.r, self.v, 'greedy')
        self.assertEqual(fifo[0]['donation_id'], 'LATE')
        self.assertEqual(greedy[0]['donation_id'], 'URGENT')
        self.assertEqual(gm['Urgent rescue rate (%)']-fm['Urgent rescue rate (%)'], 100)
        self.assertEqual(gm['Food quantity rescued']-fm['Food quantity rescued'], -10)
        # Fairness/tradeoff: the larger, less urgent donation is deferred and cannot fit.
        self.assertEqual(greedy[1]['status'], 'unassigned')
        self.assertIn('remaining capacity', greedy[1]['decision_reason'])

    def test_ties_smaller_quantity_then_ready_then_arrival(self):
        d = {'LARGE': donation(10), 'LATER': donation(5, ready='10:30'),
             'FIRST': donation(5), 'SECOND': donation(5)}
        result, _ = run_plan(d, self.r, self.v, 'greedy')
        self.assertEqual([a['donation_id'] for a in result], ['FIRST', 'SECOND', 'LATER', 'LARGE'])

    def test_absolute_expiry_not_lifetime(self):
        d = {'SHORT': donation(5, '12:00', '12:10'), 'LONG': donation(5, '08:00', '11:00')}
        result, _ = run_plan(d, self.r, self.v, 'greedy')
        self.assertEqual(result[0]['donation_id'], 'LONG')

    def test_numeric_nonpadded_time_order(self):
        d = {'LATE': donation(5, expiry='11:00'), 'EARLY': donation(5, '08:00', '9:00')}
        result, _ = run_plan(d, self.r, self.v, 'greedy')
        self.assertEqual(result[0]['donation_id'], 'EARLY')

    def test_repeatable_and_nonmutating(self):
        before = deepcopy((self.d, self.r, self.v))
        first = run_plan(self.d, self.r, self.v, 'greedy')
        rr.greedy_implementation(rr.sort_by_remaining_shelf_life(rr.donations_by_id))
        self.assertEqual(len(rr.greedy_assignments), 1)
        self.assertEqual(first, run_plan(self.d, self.r, self.v, 'greedy'))
        self.assertEqual(before, (self.d, self.r, self.v))

    def test_empty_greedy(self):
        result, metrics = run_plan({}, {}, {}, 'greedy')
        self.assertEqual(result, [])
        self.assertTrue(all(value == 0 for value in metrics.values()))

    def test_shared_constraints(self):
        cases = [(recipient(foods='bakery'), volunteer()),
                 (recipient(capacity=1), volunteer()),
                 (recipient(), volunteer(capacity=1)),
                 (recipient(), volunteer(start='15:00')),
                 (recipient(area='Other'), volunteer()),
                 (recipient(), volunteer(area='Other')),
                 (recipient(closing='09:00'), volunteer()),
                 (recipient(), volunteer(pickups=0))]
        for r, v in cases:
            with self.subTest(r=r, v=v):
                result, _ = run_plan(self.d, {'R': r}, {'V': v}, 'greedy')
                self.assertTrue(all(a['status'] == 'unassigned' for a in result))

    def test_readable_priority_and_decisions(self):
        outcomes, _ = run_plan(self.d, self.r, self.v, 'greedy')
        output = io.StringIO()
        with redirect_stdout(output):
            rr.print_results('Greedy', rr.sort_by_remaining_shelf_life(self.d),
                             rr.greedy_assignments, rr.greedy_rejected)
        text = output.getvalue()
        for phrase in ('Greedy', 'earliest expiry first', 'Community Pantry', 'remaining capacity'):
            self.assertIn(phrase, text)
        self.assertEqual(sum(a['status'] == 'assigned' for a in outcomes), 1)


if __name__ == '__main__':
    unittest.main()
