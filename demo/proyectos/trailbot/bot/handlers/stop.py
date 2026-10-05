from bot import storage


async def run(update):
    user = storage.user_from(update)
    storage.forget(user.id_hash)
    await storage.reply(update, "Done. I deleted your settings and ratings.")
