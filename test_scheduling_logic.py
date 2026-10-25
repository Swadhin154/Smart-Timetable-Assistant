import unittest
from datetime import time

from scheduling_logic import find_timetable_conflicts


class TestTimetableConflicts(unittest.TestCase):

    def test_overlapping_classes_are_detected(self):
        classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": time(9, 0),
                "End Time": time(10, 30),
            },
            {
                "subject": "Mathematics",
                "Day": "Monday",
                "Start Time": time(10, 0),
                "End Time": time(11, 0),
            },
        ]

        conflicts = find_timetable_conflicts(classes)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["Class 1"], "Physics")
        self.assertEqual(conflicts[0]["Class 2"], "Mathematics")

    def test_adjacent_classes_are_not_conflicts(self):
        classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": time(9, 0),
                "End Time": time(10, 0),
            },
            {
                "subject": "Mathematics",
                "Day": "Monday",
                "Start Time": time(10, 0),
                "End Time": time(11, 0),
            },
        ]

        self.assertEqual(find_timetable_conflicts(classes), [])

    def test_classes_on_different_days_do_not_conflict(self):
        classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": time(9, 0),
                "End Time": time(10, 30),
            },
            {
                "subject": "Mathematics",
                "Day": "Tuesday",
                "Start Time": time(10, 0),
                "End Time": time(11, 0),
            },
        ]

        self.assertEqual(find_timetable_conflicts(classes), [])

    def test_string_times_are_supported(self):
        classes = [
            {
                "Subject": "Physics",
                "Day": "Monday",
                "Start Time": "09:00",
                "End Time": "10:30",
            },
            {
                "Subject": "Mathematics",
                "Day": "Monday",
                "Start Time": "10:00 AM",
                "End Time": "11:00 AM",
            },
        ]

        self.assertEqual(len(find_timetable_conflicts(classes)), 1)

    def test_invalid_time_ranges_are_ignored(self):
        classes = [
            {
                "subject": "Physics",
                "Day": "Monday",
                "Start Time": time(10, 0),
                "End Time": time(9, 0),
            },
            {
                "subject": "Mathematics",
                "Day": "Monday",
                "Start Time": time(9, 30),
                "End Time": time(10, 30),
            },
        ]

        self.assertEqual(find_timetable_conflicts(classes), [])

    def test_empty_timetable_returns_no_conflicts(self):
        self.assertEqual(find_timetable_conflicts([]), [])


if __name__ == "__main__":
    unittest.main()