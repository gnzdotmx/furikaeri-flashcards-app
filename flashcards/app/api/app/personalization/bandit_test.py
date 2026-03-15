"""Tests for app.personalization.bandit."""

import random

import pytest

from app.personalization.bandit import EpsilonGreedyBandit, reward_from_outcome


class TestEpsilonGreedyBandit:
    def test_choose_empty_arms_raises(self) -> None:
        bandit = EpsilonGreedyBandit(epsilon=0.1)
        with pytest.raises(ValueError, match="no arms"):
            bandit.choose([])

    def test_choose_low_pulls_first(self) -> None:
        bandit = EpsilonGreedyBandit(epsilon=0.0)
        arms = [
            {"arm_key": "a", "pulls": 10, "reward_sum": 5.0},
            {"arm_key": "b", "pulls": 0, "reward_sum": 0.0},
            {"arm_key": "c", "pulls": 5, "reward_sum": 2.0},
        ]
        assert bandit.choose(arms) == "b"

    def test_choose_exploit_best_avg(self) -> None:
        random.seed(42)
        bandit = EpsilonGreedyBandit(epsilon=0.0)
        arms = [
            {"arm_key": "a", "pulls": 10, "reward_sum": 2.0},
            {"arm_key": "b", "pulls": 10, "reward_sum": 8.0},
            {"arm_key": "c", "pulls": 10, "reward_sum": 5.0},
        ]
        assert bandit.choose(arms) == "b"

    def test_choose_epsilon_explore(self) -> None:
        random.seed(123)
        bandit = EpsilonGreedyBandit(epsilon=1.0)
        arms = [
            {"arm_key": "x", "pulls": 5, "reward_sum": 0.0},
            {"arm_key": "y", "pulls": 5, "reward_sum": 0.0},
        ]
        chosen = bandit.choose(arms)
        assert chosen in ("x", "y")

    def test_choose_arm_with_few_pulls(self) -> None:
        bandit = EpsilonGreedyBandit(epsilon=0.0)
        arms = [{"arm_key": "only", "pulls": 1, "reward_sum": 0.0}]
        assert bandit.choose(arms) == "only"


class TestRewardFromOutcome:
    def test_rating_again(self) -> None:
        r = reward_from_outcome(rating="again", time_ms=0)
        assert r == pytest.approx(-1.0)

    def test_rating_good(self) -> None:
        r = reward_from_outcome(rating="good", time_ms=0)
        assert r == pytest.approx(0.6)

    def test_rating_easy(self) -> None:
        r = reward_from_outcome(rating="easy", time_ms=0)
        assert r == pytest.approx(1.0)

    def test_rating_unknown_zero_base(self) -> None:
        r = reward_from_outcome(rating="unknown", time_ms=0)
        assert r == pytest.approx(0.0)

    def test_time_penalty(self) -> None:
        r_fast = reward_from_outcome(rating="good", time_ms=0)
        r_slow = reward_from_outcome(rating="good", time_ms=60_000)
        assert r_slow < r_fast
        assert r_slow == pytest.approx(0.6 - 0.2)

    def test_time_capped_at_60s(self) -> None:
        r = reward_from_outcome(rating="good", time_ms=120_000)
        assert r == pytest.approx(0.6 - 0.2)
