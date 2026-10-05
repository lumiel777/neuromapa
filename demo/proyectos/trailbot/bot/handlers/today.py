from bot import recommend, storage, weather


async def run(update):
    user = storage.user_from(update)
    trails = storage.trails_near(user.home_lat, user.home_lon, km=120)
    forecasts = {t.slug: weather.get_forecast(t.lat, t.lon) for t in trails}
    picks = recommend.rank_trails(trails, forecasts, storage.distances(user, trails), user.fitness)
    await storage.reply(update, storage.format_picks(picks))
