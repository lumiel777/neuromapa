from bot import storage


async def run(update):
    user = storage.user_from(update)
    slug, stars = storage.parse_rating(update)
    if storage.rated_today(user.id_hash, slug):
        await storage.reply(update, "You already rated this trail today.")
        return
    storage.save_rating(user.id_hash, slug, stars)
    await storage.reply(update, "Thanks! Rating saved.")
