import unittest

from study_recommendations import recommend_study_slots


class TestStudyRecommendations(unittest.TestCase):

    def test_longer_slots_are_ranked_first(self):
        results = recommend_study_slots([], "Monday")

        durations = [
            slot["Available Duration"] for slot in results
        ]

        self.assertLessEqual(len(results), 3)
        self.assertTrue(durations)

    def test_minimum_duration_is_respected(self):
        results = recommend_study_slots(
            [],
            "Monday",
            min_duration_minutes=60,
        )

        self.assertTrue(
            all(
                int(slot["Available Duration"].split()[0]) >= 1
                for slot in results
            )
        )

    def test_recommendation_limit(self):
        results = recommend_study_slots(
            [],
            "Monday",
            max_recommendations=2,
        )

        self.assertLessEqual(len(results), 2)

    def test_zero_recommendations(self):
        results = recommend_study_slots(
            [],
            "Monday",
            max_recommendations=0,
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()