import unittest

from free_time_logic import find_free_slots


class TestFreeTimeFinder(unittest.TestCase):

    def setUp(self):
        self.classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": "09:00",
                "End Time": "10:00",
            },
            {
                "subject": "Mathematics",
                "Day": "Monday",
                "Start Time": "11:00",
                "End Time": "12:00",
            },
        ]

    def test_finds_gaps_between_classes(self):
        slots = find_free_slots(self.classes, "Monday")

        self.assertEqual(len(slots), 3)
        self.assertEqual(slots[0]["Start Time"], "06:00 AM")
        self.assertEqual(slots[0]["End Time"], "09:00 AM")
        self.assertEqual(slots[1]["Start Time"], "10:00 AM")
        self.assertEqual(slots[1]["End Time"], "11:00 AM")
        self.assertEqual(slots[2]["Start Time"], "12:00 PM")
        self.assertEqual(slots[2]["End Time"], "07:00 PM")

    def test_ignores_classes_on_other_days(self):
        slots = find_free_slots(self.classes, "Tuesday")

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["Start Time"], "06:00 AM")
        self.assertEqual(slots[0]["End Time"], "07:00 PM")

    def test_omits_gaps_shorter_than_minimum(self):
        classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": "09:00",
                "End Time": "09:45",
            },
            {
                "subject": "Chemistry",
                "Day": "Monday",
                "Start Time": "10:00",
                "End Time": "11:00",
            },
        ]

        slots = find_free_slots(
            classes,
            "Monday",
            min_duration_minutes=30,
        )

        # The 15-minute gap from 9:45 to 10:00 is omitted.
        self.assertTrue(
            all(slot["Duration (minutes)"] >= 30 for slot in slots)
        )
        self.assertFalse(
            any(
                slot["Start Time"] == "09:45 AM"
                and slot["End Time"] == "10:00 AM"
                for slot in slots
            )
        )

    def test_merges_overlapping_classes(self):
        classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": "09:00",
                "End Time": "10:30",
            },
            {
                "subject": "Mathematics",
                "Day": "Monday",
                "Start Time": "10:00",
                "End Time": "11:00",
            },
        ]

        slots = find_free_slots(classes, "Monday")

        # The overlapping classes form one busy period, 9 AM–11 AM.
        self.assertEqual(slots[0]["End Time"], "09:00 AM")
        self.assertEqual(slots[1]["Start Time"], "11:00 AM")

    def test_empty_timetable_returns_full_search_window(self):
        slots = find_free_slots([], "Monday")

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["Start Time"], "06:00 AM")
        self.assertEqual(slots[0]["End Time"], "07:00 PM")
        self.assertEqual(slots[0]["Duration (minutes)"], 780)

    def test_rejects_invalid_search_window(self):
        with self.assertRaises(ValueError):
            find_free_slots(
                self.classes,
                "Monday",
                start_time="19:00",
                end_time="06:00",
            )


if __name__ == "__main__":
    unittest.main()