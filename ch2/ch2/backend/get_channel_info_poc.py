from telethon.sync import TelegramClient
from telethon import functions

# Configuration data
app_name = "YOUR_APP_NAME_HERE"
api_id = int("YOUR_API_ID_HERE")
api_hash = "YOUR_API_HASH_HERE"

# Input data
channel_names = ["rybar", "mig41"]

# Retrieve channel metadata from Telegram API
with TelegramClient(app_name, api_id, api_hash) as client:
    for channel_name in channel_names:
        channel_object = client(
            functions.channels.GetFullChannelRequest(channel=channel_name)
        )

        if channel_object is not None:
            print(channel_object.to_dict())
