from telethon import TelegramClient

# Configuration data
app_name = "YOUR_APP_NAME_HERE"
api_id = int("YOUR_API_ID_HERE")
api_hash = "YOUR_API_HASH_HERE"

# Input data
channel_name = "rybar"

# Retrieve channel message metadata from Telegram API
with TelegramClient(app_name, api_id, api_hash) as client:
    message_batch = client.iter_messages(channel_name, min_id=0, max_id=0, limit=100)

    for message in message_batch:
        print(message.to_dict())
