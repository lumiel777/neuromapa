from bot import storage

TEXT = "/today - a hike for today\n/near - trails close to home\n/rate <trail> <1-5>\n/stop - forget me"


async def run(update):
    await storage.reply(update, TEXT)
