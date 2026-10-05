from bot import storage


async def run(update):
    user = storage.user_from(update)
    trails = storage.trails_near(user.home_lat, user.home_lon, km=40)
    await storage.reply(update, storage.format_list(trails))
