from telethon.errors.rpcerrorlist import UsernameInvalidError
from telethon.sync import TelegramClient
from telethon import functions
from telethon.tl.types.messages import ChatFull
import time
from .db_ch2 import (
    insert_data_into_seed_table,
    insert_data_into_channel_metadata_table_advanced,
)

SECONDS_TO_PAUSE_BETWEEN_CHANNEL_INFO_LOOKUPS = 30


def extract_data_dictionary_from_channel_object(
    channel_object: ChatFull, channel_name: str
) -> dict:
    return {
        "channel_name": channel_name,
        "channel_id": channel_object.to_dict()["full_chat"]["id"],
        "channel_title": channel_object.to_dict()["chats"][0]["title"],
        "num_subscribers": channel_object.to_dict()["full_chat"]["participants_count"],
        "channel_bio": channel_object.to_dict()["full_chat"]["about"],
        "channel_birthdate": channel_object.to_dict()["chats"][0]["date"],
        "api_response": channel_object.to_json(),
    }


def retrieve_channel_metadata(
    channel_names: list[str], app_name: str, api_id: int, api_hash: str
) -> list[dict]:
    # Retrieve data from Telegram API, using Telethon:
    records = []
    with TelegramClient(app_name, api_id, api_hash) as client:
        for channel_name in channel_names:
            print(f"Querying Telegram API for @{channel_name}...")
            try:
                channel_object = client(
                    functions.channels.GetFullChannelRequest(channel=channel_name)
                )
            except ValueError as e:
                print(e)
                channel_object = None
            except UsernameInvalidError as e:
                print(e)
                channel_object = None
            except Exception as e:
                raise e

            if channel_object is not None:
                records.append(
                    extract_data_dictionary_from_channel_object(
                        channel_object, channel_name
                    )
                )
            else:
                print(f"No metadata returned by Telegram API for @{channel_name}")

            print(
                f"Pausing {SECONDS_TO_PAUSE_BETWEEN_CHANNEL_INFO_LOOKUPS} seconds "
                f"to respect Telegram API rate limits..."
            )
            time.sleep(
                SECONDS_TO_PAUSE_BETWEEN_CHANNEL_INFO_LOOKUPS
            )  # pause to respect API rate limiting

    return records


def retrieve_and_save_channel_metadata(
    channel_names: list[str],
    app_name: str,
    api_id: int,
    api_hash: str,
    seed_list_name: str,
):
    # Retrieve data from Telegram API
    records = retrieve_channel_metadata(channel_names, app_name, api_id, api_hash)

    # Prepare seed data
    seed_records = [
        {
            "channel_name": record["channel_name"],
            "channel_id": record["channel_id"],
            "seed_list": seed_list_name,
        }
        for record in records
    ]

    # Insert data into database
    if len(records) > 0:
        insert_data_into_channel_metadata_table_advanced(records)
        insert_data_into_seed_table(seed_records)
