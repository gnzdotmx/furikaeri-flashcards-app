import random


class EpsilonGreedyBandit:
    def __init__(self, *, epsilon: float = 0.1):
        self.epsilon = float(epsilon)

    def choose(self, arms: list[dict]) -> str:
        """
        arms: [{arm_key, pulls, reward_sum}]
        """
        if not arms:
            raise ValueError("no arms")

        # Explore any arm with low pulls first.
        for a in arms:
            if int(a.get("pulls", 0)) < 3:
                return str(a["arm_key"])

        if random.random() < self.epsilon:
            return str(random.choice(arms)["arm_key"])

        def avg(a: dict) -> float:
            pulls = max(1, int(a.get("pulls", 0)))
            return float(a.get("reward_sum", 0.0)) / pulls

        best = max(arms, key=avg)
        return str(best["arm_key"])


def reward_from_outcome(*, rating: str, time_ms: int) -> float:
    """
    Map review outcome to a bounded reward signal for bandits.
    """
    base = {"again": -1.0, "hard": -0.2, "good": 0.6, "easy": 1.0}.get(rating, 0.0)
    # Penalize slow answers slightly (cap at 60s).
    t = max(0, min(int(time_ms), 60_000)) / 60_000.0
    return float(base - (0.2 * t))

