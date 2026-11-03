"""Rank probabilities for the final bet standing (match points only).

Pure Python, no Django. Each user's remaining match points are drawn
independently from that user's own history of points per game. The result is
calculated exactly (no random trials), so the numbers are stable between page
loads.
"""
from collections import Counter

# Placements grouped by what they cost: (label, description, first rank, last rank)
RANK_GROUPS = (
    ('1–3', 'Betalar inte', 1, 3),
    ('4–7', 'Betalar', 4, 7),
    ('8–10', 'Betalar och är värd för fest', 8, 10),
)


def points_distribution(history, games):
    """Return {points: probability} for the sum of `games` independent games.

    `history` is a list of points per game. Each game is a draw from it.
    """
    distribution = {0: 1.0}
    if games <= 0 or not history:
        return distribution
    per_game = {points: count / len(history) for points, count in Counter(history).items()}
    for _ in range(games):
        next_distribution = {}
        for total, probability in distribution.items():
            for points, chance in per_game.items():
                next_distribution[total + points] = next_distribution.get(total + points, 0.0) + probability * chance
        distribution = next_distribution
    return distribution


def _count_distribution(chances):
    """Poisson-binomial: probability of exactly m successes, one chance each."""
    counts = [1.0]
    for chance in chances:
        updated = [0.0] * (len(counts) + 1)
        for m, probability in enumerate(counts):
            updated[m] += probability * (1 - chance)
            updated[m + 1] += probability * chance
        counts = updated
    return counts


def calculate_rank_probabilities(base_points, histories, remaining_games):
    """Return {user: {'rank_probabilities': [...], 'expected_rank': float}}.

    `base_points` is {user: points today}, `histories` is {user: [points per
    game]}. Users without history use everybody's history together. Ties share
    the better placement, as in the leaderboard.
    """
    pooled = [points for history in histories.values() for points in history]
    totals = {}
    for user, base in base_points.items():
        history = histories.get(user) or pooled
        distribution = points_distribution(history, remaining_games)
        totals[user] = {base + points: probability for points, probability in distribution.items()}

    result = {}
    for user, user_totals in totals.items():
        others = [other for other in totals if other != user]
        rank_probabilities = [0.0] * len(totals)
        for total, probability in user_totals.items():
            chances = [
                sum(chance for other_total, chance in totals[other].items() if other_total > total)
                for other in others
            ]
            for above, weight in enumerate(_count_distribution(chances)):
                rank_probabilities[above] += probability * weight
        result[user] = {
            'rank_probabilities': rank_probabilities,
            'expected_rank': sum((rank + 1) * p for rank, p in enumerate(rank_probabilities)),
        }
    return result


def group_probabilities(rank_probabilities, groups=RANK_GROUPS):
    """Return the combined probability of each rank group, in the order of `groups`.

    `rank_probabilities` is the list for ranks 1, 2, ... Ranks that don't exist (fewer
    players than the group's last rank) add nothing.
    """
    return [sum(rank_probabilities[first - 1:last]) for _, _, first, last in groups]
