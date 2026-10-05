from fastapi import FastAPI, Request

from bot.handlers import dispatch

app = FastAPI()
seen_updates = set()


@app.post("/telegram/webhook")
async def webhook(request: Request):
    update = await request.json()
    update_id = update.get("update_id")
    if update_id in seen_updates:
        return {"ok": True, "duplicate": True}
    seen_updates.add(update_id)
    await dispatch(update)
    return {"ok": True}
