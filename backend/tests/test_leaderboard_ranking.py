"""
test_leaderboard_ranking.py

Covers app.services.test_history_service.get_leaderboard()'s ranking math.

Regression context: the leaderboard previously ranked purely by raw average
score, so a student with one lucky 100% test outranked a student with fifty
consistent 85% tests. get_leaderboard() now weights the ranking toward the
platform-wide mean in proportion to how few tests a student has taken (a
Bayesian/"IMDb-style" adjustment), while `average_score` shown to students
stays their real, unadjusted average.
"""
import pytest

from app.services import test_history_service


def _row(username, percentage):
    return {"username": username, "percentage": percentage}


class TestLeaderboardWeighting:

    def test_one_lucky_test_does_not_outrank_many_consistent_tests(self, monkeypatch):
        history = (
            [_row("lucky", 100)]
            + [_row("consistent", 85) for _ in range(50)]
            # A few other students establish a platform mean below both of
            # the above, so the weighting has something real to pull toward.
            + [_row("average_joe", 60) for _ in range(10)]
        )
        monkeypatch.setattr(test_history_service, "get_all_history", lambda: history)

        leaderboard = test_history_service.get_leaderboard()
        usernames = [row["username"] for row in leaderboard]

        assert usernames.index("consistent") < usernames.index("lucky"), (
            "50 tests at 85% must outrank 1 test at 100% once ranking is "
            "weighted by sample size"
        )

    def test_average_score_field_is_never_adjusted(self, monkeypatch):
        history = [_row("lucky", 100)] + [_row("consistent", 85) for _ in range(50)]
        monkeypatch.setattr(test_history_service, "get_all_history", lambda: history)

        leaderboard = test_history_service.get_leaderboard()
        by_user = {row["username"]: row for row in leaderboard}

        # Displayed average must stay the real, unadjusted number — only
        # sort order is allowed to change.
        assert by_user["lucky"]["average_score"] == 100.0
        assert by_user["consistent"]["average_score"] == 85.0

    def test_many_tests_at_a_higher_average_still_wins(self, monkeypatch):
        history = (
            [_row("consistent_high", 90) for _ in range(30)]
            + [_row("consistent_low", 70) for _ in range(30)]
        )
        monkeypatch.setattr(test_history_service, "get_all_history", lambda: history)

        leaderboard = test_history_service.get_leaderboard()
        usernames = [row["username"] for row in leaderboard]

        assert usernames.index("consistent_high") < usernames.index("consistent_low"), (
            "weighting toward the platform mean must not flip a genuine, "
            "well-sampled performance gap"
        )

    def test_tests_and_best_score_fields_unchanged(self, monkeypatch):
        history = [_row("a", 40), _row("a", 60)]
        monkeypatch.setattr(test_history_service, "get_all_history", lambda: history)

        [row] = test_history_service.get_leaderboard()
        assert row["tests"] == 2
        assert row["best_score"] == 60
        assert row["average_score"] == 50.0

    def test_empty_history_returns_empty_leaderboard(self, monkeypatch):
        monkeypatch.setattr(test_history_service, "get_all_history", lambda: [])
        assert test_history_service.get_leaderboard() == []

    def test_rows_with_no_username_are_skipped(self, monkeypatch):
        history = [_row(None, 100), _row("", 90), _row("real_user", 80)]
        monkeypatch.setattr(test_history_service, "get_all_history", lambda: history)

        leaderboard = test_history_service.get_leaderboard()
        assert [row["username"] for row in leaderboard] == ["real_user"]
