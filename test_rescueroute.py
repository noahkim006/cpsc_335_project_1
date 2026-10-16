"""RescueRoute tests: one or two tests per requirement in the project brief (20 total).

Run from the project folder:  python -m unittest -v
"""
import contextlib
import csv
import io
import os
import tempfile
import unittest
from copy import deepcopy

with contextlib.redirect_stdout(io.StringIO()):
    import rescueroute as rr

HEADERS = {
    "donations": ["donation_id", "donor_name", "food_type", "quantity",
                  "pickup_area", "ready_time", "expiry_time"],
    "recipients": ["recipient_id", "org_name", "accepted_food_types",
                   "capacity", "area", "closing_time"],
    "volunteers": ["volunteer_id", "vehicle_capacity", "area",
                   "available_from", "available_until", "max_pickups"],
}


def donation(quantity=10, ready="10:00", expiry="12:00", area="Central", food="produce"):
    return {"donor_name": "Market", "food_type": food, "quantity": quantity,
            "pickup_area": area, "ready_time": ready, "expiry_time": expiry,
            "remaining_shelf_life": rr.time_to_minutes(expiry) - rr.time_to_minutes(ready)}


def recipient(capacity=30, closing="18:00", area="Central", foods="produce;bakery"):
    return {"org_name": "Community Pantry", "accepted_food_types": foods,
            "capacity": capacity, "area": area, "closing_time": closing}


def volunteer(capacity=20, start="09:00", end="17:00", pickups=3, area="Central"):
    return {"vehicle_capacity": capacity, "area": area, "available_from": start,
            "available_until": end, "max_pickups": pickups}


def reset_state():
    for name in ("donations_by_id", "recipients_by_id", "volunteers_by_id",
                 "processed_donor_ids", "processed_recipient_ids",
                 "processed_volunteer_ids", "fifo_assignments", "fifo_rejected",
                 "greedy_assignments", "greedy_rejected"):
        getattr(rr, name).clear()


def run_plan(donations, recipients, volunteers, strategy="fifo"):
    reset_state()
    rr.donations_by_id.update(deepcopy(donations))
    rr.recipients_by_id.update(deepcopy(recipients))
    rr.volunteers_by_id.update(deepcopy(volunteers))
    if strategy == "fifo":
        order = rr.sort_by_arrival_time(rr.donations_by_id)
        rr.fifo_implementation(order)
        results = rr.fifo_assignments + rr.fifo_rejected
    else:
        order = rr.sort_by_remaining_shelf_life(rr.donations_by_id)
        rr.greedy_implementation(order)
        results = rr.greedy_assignments + rr.greedy_rejected
    by_id = {a["donation_id"]: a for a in results}
    return deepcopy([by_id[donation_id] for donation_id, _ in order])


def statuses(outcomes):
    return {o["donation_id"]: o["status"] for o in outcomes}


def rescued(outcomes, donations):
    return sum(donations[o["donation_id"]]["quantity"]
               for o in outcomes if o["status"] == "assigned")


class BaseTest(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.addCleanup(reset_state)


class NormalMatchTests(BaseTest):
    def test_fifo_matches_compatible_donor_recipient_and_volunteer(self):
        a = run_plan({"D1": donation()}, {"R1": recipient()}, {"V1": volunteer()}, "fifo")[0]
        self.assertEqual((a["status"], a["recipient_id"], a["volunteer_id"], a["scheduled_time"]),
                         ("assigned", "R1", "V1", "10:00"))
        self.assertIn("Community Pantry", a["decision_reason"])

    def test_greedy_matches_compatible_donor_recipient_and_volunteer(self):
        a = run_plan({"D1": donation()}, {"R1": recipient()}, {"V1": volunteer()}, "greedy")[0]
        self.assertEqual((a["status"], a["recipient_id"], a["volunteer_id"], a["scheduled_time"]),
                         ("assigned", "R1", "V1", "10:00"))


class LoadingTests(BaseTest):
    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.assets = os.path.join(temp.name, "assets")
        os.mkdir(self.assets)
        old_cwd = os.getcwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, old_cwd)
        self.rows = {"donations": [{"donation_id": "D1", **donation()}],
                     "recipients": [{"recipient_id": "R1", **recipient()}],
                     "volunteers": [{"volunteer_id": "V1", **volunteer()}]}

    def load(self):
        for kind, rows in self.rows.items():
            with open(os.path.join(self.assets, kind + ".csv"), "w", newline="") as f:
                writer = csv.DictWriter(f, HEADERS[kind], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        reset_state()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = rr.load_files()
        return result, out.getvalue()

    def test_duplicate_donation_id_keeps_first_row_only(self):
        self.rows["donations"].append({"donation_id": "D1", **donation(99)})
        _, printed = self.load()
        self.assertEqual(list(rr.donations_by_id), ["D1"])
        self.assertEqual(rr.donations_by_id["D1"]["quantity"], 10)
        self.assertIn("already exists", printed)

    def test_duplicate_recipient_and_volunteer_ids_are_skipped(self):
        self.rows["recipients"].append({"recipient_id": "R1", **recipient(99)})
        self.rows["volunteers"].append({"volunteer_id": "V1", **volunteer(99)})
        self.load()
        self.assertEqual(rr.recipients_by_id["R1"]["capacity"], 30)
        self.assertEqual(rr.volunteers_by_id["V1"]["vehicle_capacity"], 20)

    def test_expired_donation_is_rejected_at_load(self):
        for expiry in ("10:00", "09:30"):  # expiry equal to ready, and before ready
            with self.subTest(expiry=expiry):
                self.rows["donations"][0]["expiry_time"] = expiry
                _, printed = self.load()
                self.assertEqual(rr.donations_by_id, {})
                self.assertIn("expired", printed)

    def test_header_only_files_load_as_empty_data(self):
        self.rows = {kind: [] for kind in HEADERS}
        ok, _ = self.load()
        self.assertTrue(ok)
        self.assertEqual((rr.donations_by_id, rr.recipients_by_id, rr.volunteers_by_id), ({}, {}, {}))

    def test_zero_byte_file_is_reported_and_nothing_is_scheduled(self):
        self.load()   # write valid files first
        open(os.path.join(self.assets, "recipients.csv"), "w").close()   # empty it
        reset_state()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertFalse(rr.load_files())
        self.assertIn("contains no data", out.getvalue())
        self.assertEqual(rr.donations_by_id, {})


class ExpiryTests(BaseTest):
    def test_volunteer_arrives_after_expiry_so_donation_is_unassigned(self):
        d = {"D": donation(5, "10:00", "10:20")}
        for strategy in ("fifo", "greedy"):
            with self.subTest(strategy):
                a = run_plan(d, {"R": recipient()}, {"V": volunteer(start="10:30")}, strategy)[0]
                self.assertEqual(a["status"], "unassigned")
                self.assertIn("expiry", a["decision_reason"])

    def test_pickup_exactly_at_expiry_is_still_allowed(self):
        d = {"D": donation(5, "10:00", "10:30")}
        a = run_plan(d, {"R": recipient()}, {"V": volunteer(start="10:30")}, "fifo")[0]
        self.assertEqual((a["status"], a["scheduled_time"]), ("assigned", "10:30"))


class ConstraintFailureTests(BaseTest):
    def check_unassigned(self, d, r, v, phrase):
        for strategy in ("fifo", "greedy"):
            with self.subTest(strategy):
                a = run_plan({"D": d}, {"R": r}, {"V": v}, strategy)[0]
                self.assertEqual(a["status"], "unassigned")
                self.assertTrue(a["recipient_id"] is None and a["volunteer_id"] is None)
                self.assertIn(phrase, a["decision_reason"])

    def test_no_recipient_accepts_the_food_type(self):
        self.check_unassigned(donation(food="seafood"), recipient(), volunteer(), "no recipient matches")

    def test_recipient_has_insufficient_capacity(self):
        self.check_unassigned(donation(10), recipient(capacity=5), volunteer(), "remaining capacity")

    def test_no_volunteer_vehicle_is_big_enough(self):
        self.check_unassigned(donation(10), recipient(), volunteer(capacity=5), "vehicle capacity")


class CompetitionTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.d = {"EARLY": donation(20, "09:00", "15:00"), "URGENT": donation(20, "10:00", "11:00")}
        self.r = {"R": recipient(capacity=30)}
        self.v = {"V": volunteer()}

    def test_fifo_gives_the_capacity_to_the_earlier_arrival(self):
        out = run_plan(self.d, self.r, self.v, "fifo")
        self.assertEqual(statuses(out), {"EARLY": "assigned", "URGENT": "unassigned"})
        self.assertIn("remaining capacity", out[1]["decision_reason"])

    def test_greedy_gives_the_capacity_to_the_more_urgent_donation(self):
        out = run_plan(self.d, self.r, self.v, "greedy")
        self.assertEqual(statuses(out), {"EARLY": "unassigned", "URGENT": "assigned"})
        self.assertIn("remaining capacity", out[1]["decision_reason"])


class EmptyListTests(BaseTest):
    def test_no_donations_produces_no_outcomes(self):
        for strategy in ("fifo", "greedy"):
            with self.subTest(strategy):
                self.assertEqual(run_plan({}, {"R": recipient()}, {"V": volunteer()}, strategy), [])

    def test_no_recipients_or_no_volunteers_leaves_donation_unassigned(self):
        for label, r, v in (("no recipients", {}, {"V": volunteer()}),
                            ("no volunteers", {"R": recipient()}, {})):
            for strategy in ("fifo", "greedy"):
                with self.subTest(label=label, strategy=strategy):
                    a = run_plan({"D": donation()}, r, v, strategy)[0]
                    self.assertEqual(a["status"], "unassigned")


HARBORSIDE_D = {"EARLY": donation(25, "08:00", "20:00"),
                "SMALL": donation(10, "08:30", "19:00"),
                "URGENT": donation(70, "11:00", "12:00")}
HARBORSIDE_R = {"R": recipient(capacity=80)}
HARBORSIDE_V = {"V": volunteer(capacity=80, start="08:00", end="21:00", pickups=4)}


class StrategyComparisonTests(BaseTest):
    def test_fifo_and_greedy_produce_different_results(self):
        fifo = run_plan(HARBORSIDE_D, HARBORSIDE_R, HARBORSIDE_V, "fifo")
        greedy = run_plan(HARBORSIDE_D, HARBORSIDE_R, HARBORSIDE_V, "greedy")
        self.assertEqual(statuses(fifo), {"EARLY": "assigned", "SMALL": "assigned", "URGENT": "unassigned"})
        self.assertEqual(statuses(greedy), {"EARLY": "unassigned", "SMALL": "assigned", "URGENT": "assigned"})
        self.assertEqual(rescued(fifo, HARBORSIDE_D), 35)
        self.assertEqual(rescued(greedy, HARBORSIDE_D), 80)

    def test_greedy_is_not_always_better_downtown_fifo_rescues_more_food(self):
        d = {"D1014": donation(25, "10:00", "14:00"), "D1001": donation(20, "11:30", "13:30"),
             "D1007": donation(10, "12:00", "12:20"), "D1010": donation(5, "12:00", "18:00")}
        r, v = {"R": recipient(capacity=50)}, {"V": volunteer(capacity=25, pickups=3)}
        fifo, greedy = run_plan(d, r, v, "fifo"), run_plan(d, r, v, "greedy")
        self.assertEqual((rescued(fifo, d), rescued(greedy, d)), (50, 35))
        self.assertEqual(statuses(fifo)["D1007"], "unassigned")   # FIFO misses the urgent one
        self.assertEqual(statuses(greedy)["D1007"], "assigned")

    def test_starvation_long_life_donation_is_deferred_and_then_rejected(self):
        # Greedy always serves shorter-life donations first, so LONG waits until
        # capacity is gone. FIFO serves it first because it arrived first.
        d = {"LONG": donation(20, "08:00", "20:00"), "S1": donation(10, "10:00", "11:00"),
             "S2": donation(10, "10:00", "11:30")}
        r, v = {"R": recipient(capacity=20)}, {"V": volunteer(pickups=5)}
        greedy = run_plan(d, r, v, "greedy")
        self.assertEqual([a["donation_id"] for a in greedy], ["S1", "S2", "LONG"])
        self.assertEqual(statuses(greedy)["LONG"], "unassigned")
        self.assertIn("remaining capacity", greedy[2]["decision_reason"])
        self.assertEqual(statuses(run_plan(d, r, v, "fifo"))["LONG"], "assigned")


class OutputTests(BaseTest):
    def test_printed_output_explains_every_assignment_and_rejection(self):
        d = {"OK": donation(10), "BIG": donation(500)}
        run_plan(d, {"R": recipient(capacity=600)}, {"V": volunteer()}, "fifo")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rr.print_results("FIFO RESULTS", rr.fifo_assignments, rr.fifo_rejected)
        text = out.getvalue()
        for phrase in ("FIFO RESULTS", "ASSIGNED at 10:00", "Community Pantry", "UNASSIGNED",
                       "vehicle capacity", "Total assigned: 1", "Total unassigned: 1"):
            with self.subTest(phrase):
                self.assertIn(phrase, text)
        self.assertEqual(text.count("Why:"), 2)   # one explanation per donation


if __name__ == "__main__":
    unittest.main()
