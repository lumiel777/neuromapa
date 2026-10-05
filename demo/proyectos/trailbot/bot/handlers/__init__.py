from bot.handlers import help, near, rate, stop, today

COMMANDS = {"/today": today.run, "/near": near.run, "/rate": rate.run, "/stop": stop.run, "/help": help.run}


async def dispatch(update):
    text = (update.get("message") or {}).get("text", "")
    command = text.split()[0] if text else ""
    handler = COMMANDS.get(command, help.run)
    await handler(update)
