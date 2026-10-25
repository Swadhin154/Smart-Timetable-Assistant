import unittest

from natural_language import understand_request


class TestNaturalLanguage(unittest.TestCase):

    def test_find_free_time(self):
        result = understand_request("Find free time on Monday")
        self.assertEqual(result["action"], "find_free_time")
        self.assertEqual(result["day"], "Monday")

    def test_study_recommendations(self):
        result = understand_request("Show study periods on Sunday")
        self.assertEqual(
            result["action"], "study_recommendations"
        )
        self.assertEqual(result["day"], "Sunday")

    def test_check_conflicts(self):
        result = understand_request("Check clashes on Tuesday")
        self.assertEqual(result["action"], "check_conflicts")
        self.assertEqual(result["day"], "Tuesday")

    def test_missing_day(self):
        result = understand_request("Find free time")
        self.assertIsNotNone(result["error"])

    def test_unknown_request(self):
        result = understand_request("Tell me a joke")
        self.assertIsNotNone(result["error"])


if __name__ == "__main__":
    unittest.main()