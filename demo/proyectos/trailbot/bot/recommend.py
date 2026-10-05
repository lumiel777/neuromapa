from dataclasses import dataclass

DIFFICULTY_WEIGHT = {"easy": 1.0, "moderate": 0.8, "hard": 0.55}
MAX_WIND_KMH = 45
RAIN_PENALTY = 0.6


@dataclass
class Trail:
    slug: str
    name: str
    difficulty: str
    km: float
    lat: float
    lon: float


def weather_factor(forecast):
    if forecast.wind_kmh > MAX_WIND_KMH or forecast.storm:
        return 0.0
    factor = 1.0
    if forecast.rain_mm > 1:
        factor *= RAIN_PENALTY
    if forecast.max_temp_c > 32:
        factor *= 0.7
    return factor


def distance_factor(km_from_user):
    if km_from_user <= 30:
        return 1.0
    return max(0.2, 1.0 - (km_from_user - 30) / 150)


def score_trail(trail, forecast, km_from_user, fitness):
    base = DIFFICULTY_WEIGHT.get(trail.difficulty, 0.5)
    if trail.difficulty == "hard" and fitness < 3:
        base *= 0.4
    return round(base * weather_factor(forecast) * distance_factor(km_from_user), 3)


def rank_trails(trails, forecasts, distances, fitness, top=3):
    scored = [(score_trail(t, forecasts[t.slug], distances[t.slug], fitness), t) for t in trails]
    scored = [pair for pair in scored if pair[0] > 0]
    scored.sort(key=lambda pair: (-pair[0], pair[1].km))
    return [t for _, t in scored[:top]]
