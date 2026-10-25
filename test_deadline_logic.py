import unittest
from datetime import date, timedelta

from deadline_logic import validate_deadline, get_deadline_status


class TestDeadlineLogic(unittest.TestCase):

    def test_valid_deadline(self):
        result, message = validate_deadline(
            "Physics Assignment",
            date.today() + timedelta(days=5),
            3,
            "High",
        )
        self.assertTrue(result)

    def test_empty_title(self):
        result, message = validate_deadline(
            " ",
            date.today(),
            2,
            "Medium",
        )
        self.assertFalse(result)

    def test_zero_preparation_hours(self):
        result, message = validate_deadline(
            "Physics Assignment",
            date.today(),
            0,
            "Medium",
        )
        self.assertFalse(result)

    def test_invalid_priority(self):
        result, message = validate_deadline(
            "Physics Assignment",
            date.today(),
            2,
            "Urgent",
        )
        self.assertFalse(result)

    def test_due_today(self):
        result = get_deadline_status(
            date(2026, 10, 25),
            today=date(2026, 10, 25),
        )
        self.assertEqual(result["status"], "Due today")
        self.assertEqual(result["days_remaining"], 0)

    def test_upcoming_deadline(self):
        result = get_deadline_status(
            date(2026, 11, 5),
            today=date(2026, 10, 25),
        )
        self.assertEqual(result["status"], "Upcoming")
        self.assertEqual(result["days_remaining"], 11)

    def test_overdue_deadline(self):
        result = get_deadline_status(
            date(2026, 10, 24),
            today=date(2026, 10, 25),
        )
        self.assertEqual(result["status"], "Overdue")
        self.assertEqual(result["days_remaining"], -1)


if __name__ == "__main__":
    unittest.main()