import os
import httpx

async def notify_admin(title: str, message: str, color: str = 'blue'):
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print(f"[Discord] {title}: {message}")
        return
    colors = {'blue': 3447003, 'green': 3066993, 'red': 15158332, 'yellow': 15105570}
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": colors.get(color, 3447003),
        }]
    }
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload)
