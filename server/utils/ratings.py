"""Calculate ELO ratings."""
from .. import enums
from ..config import ELO_K_FACTOR


def transformed_rating(elo: int) -> int:
    """Calculate "transformed rating" for easier calculations."""
    return 10 ** (elo / 400)


def updated_rating(
        old: int, expected: int, actual: int, k_factor: int) -> int:
    """Calculate the updated rating for a single user."""
    return round(old + k_factor * (actual - expected))


def host_result_value(winner: enums.Winner) -> float:
    """Get the "actual" result for the host."""
    if winner == enums.Winner.HOST:
        return 1
    if winner == enums.Winner.AWAY:
        return 0
    return 0.5


def calculate(
        host_elo: int, away_elo: int, winner: enums.Winner,
        k_factor: int = ELO_K_FACTOR) -> tuple[int, int]:
    """Calculate the updated ELO after a match."""
    host_transformed = transformed_rating(host_elo)
    away_transformed = transformed_rating(away_elo)
    total_transformed = host_transformed + away_transformed
    host_expected = host_transformed / total_transformed
    away_expected = away_transformed / total_transformed
    host_actual = host_result_value(winner)
    away_actual = 1 - host_actual
    host_updated = updated_rating(
        host_elo, host_expected, host_actual, k_factor
    )
    away_updated = updated_rating(
        away_elo, away_expected, away_actual, k_factor
    )
    return host_updated, away_updated
