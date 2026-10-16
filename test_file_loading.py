
import unittest
import rescueroute


# Test 1: Check time validation
class TestValidTime(unittest.TestCase):

    def test_valid_time_midday(self):
        self.assertTrue(rescueroute.valid_time("12:30"))

    def test_valid_time_midnight(self):
        self.assertTrue(rescueroute.valid_time("00:00"))

    def test_valid_time_last_minute_of_day(self):
        self.assertTrue(rescueroute.valid_time("23:59"))

    def test_invalid_hour(self):
        self.assertFalse(rescueroute.valid_time("24:00"))

    def test_invalid_minute(self):
        self.assertFalse(rescueroute.valid_time("12:60"))

    def test_invalid_text(self):
        self.assertFalse(rescueroute.valid_time("noon"))


# Test 2: Check assignment creation
class TestCreateAssignment(unittest.TestCase):

    def test_assignment_contains_expected_values(self):
        assignment = rescueroute.create_assignment(
            "D01",
            "R01",
            "V01",
            "10:30",
            "Food type and capacity match",
            "assigned"
        )

        self.assertEqual(assignment["donation_id"], "D01")
        self.assertEqual(assignment["recipient_id"], "R01")
        self.assertEqual(assignment["volunteer_id"], "V01")
        self.assertEqual(assignment["scheduled_time"], "10:30")
        self.assertEqual(assignment["status"], "assigned")

    def test_assignment_has_all_expected_keys(self):
        assignment = rescueroute.create_assignment(
            "D01", "R01", "V01", "10:30", "reason", "assigned"
        )

        expected_keys = {
            "donation_id",
            "recipient_id",
            "volunteer_id",
            "scheduled_time",
            "decision_reason",
            "status"
        }

        self.assertEqual(set(assignment.keys()), expected_keys)


# Test 3: Check FIFO and greedy sorting
class TestDonationSorting(unittest.TestCase):

    def setUp(self):
        self.donations = {
            "D01": {
                "donor_name": "Bakery",
                "quantity": "5",
                "ready_time": "09:00",
                "remaining_shelf_life": 7200
            },
            "D02": {
                "donor_name": "Market",
                "quantity": "8",
                "ready_time": "08:00",
                "remaining_shelf_life": 1800
            },
            "D03": {
                "donor_name": "Cafe",
                "quantity": "10",
                "ready_time": "10:00",
                "remaining_shelf_life": 1800
            }
        }

    def test_fifo_by_ready_time(self):
        sorted_donations = rescueroute.sort_by_arrival_time(
            self.donations
        )

        self.assertEqual(
            [d["donor_name"] for d in sorted_donations],
            ["Market", "Bakery", "Cafe"]
        )

    def test_greedy_shortest_shelf_life_first(self):
        sorted_donations = rescueroute.sort_by_remaining_shelf_life(
            self.donations
        )

        self.assertEqual(
            sorted_donations[0]["donor_name"], "Cafe"
        )
        self.assertEqual(
            sorted_donations[1]["donor_name"], "Market"
        )
        self.assertEqual(
            sorted_donations[2]["donor_name"], "Bakery"
        )

    def test_greedy_uses_larger_quantity_as_tie_breaker(self):
        sorted_donations = rescueroute.sort_by_remaining_shelf_life(
            self.donations
        )

        self.assertEqual(sorted_donations[0]["quantity"], "10")
        self.assertEqual(sorted_donations[1]["quantity"], "8")

    def test_sorting_empty_dictionary_returns_empty_list(self):
        self.assertEqual(
            rescueroute.sort_by_arrival_time({}), []
        )
        self.assertEqual(
            rescueroute.sort_by_remaining_shelf_life({}), []
        )


if __name__ == "__main__":
    unittest.main()

