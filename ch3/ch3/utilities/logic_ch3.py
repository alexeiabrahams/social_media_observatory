import time
from telethon.errors.rpcerrorlist import UsernameInvalidError
from telethon.sync import TelegramClient
from telethon import functions
from telethon.tl.patched import Message as TelegramMessage
from telethon.tl.types.messages import ChatFull

import pandas as pd
from deep_translator import GoogleTranslator
from ..config import handles_queue, messages_queue
from .mq_ch3 import send_data_to_queue
from .db_ch3 import (
    fetch_seed_list_names,
    fetch_seed_list_preview,
    fetch_seed_metadata_full,
    fetch_birth_chart_data,
    fetch_time_series_chart_data,
    fetch_top_messages,
    insert_data_into_seed_table,
    insert_data_into_channel_metadata_table_advanced,
    insert_data_into_channel_messages_table_advanced,
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


def get_names_of_seed_lists() -> list[dict]:
    return fetch_seed_list_names()


def get_seed_list_preview(my_seed_list_names: list[str]) -> list[dict]:
    return fetch_seed_list_preview(my_seed_list_names)


def get_seed_channel_metadata(seed_list_names: list[str]) -> list[dict]:
    records = fetch_seed_metadata_full(seed_list_names)

    # Remove private fields:
    private_fields = ["api_response", "checkup_time", "data_source"]
    for private_field in private_fields:
        [record.pop(private_field) for record in records]

    return records


def get_birth_chart_data(
    birth_chart_unit: str, seed_list_names: list[str]
) -> list[dict]:
    return fetch_birth_chart_data(seed_list_names, birth_chart_unit)


def get_time_series_chart_data(
    start_date: str,
    end_date: str,
    time_series_chart_unit: str,
    seed_list_names: list[str],
) -> list[dict]:
    return fetch_time_series_chart_data(
        seed_list_names, start_date, end_date, time_series_chart_unit
    )


def get_top_messages(
    start_date: str,
    end_date: str,
    seed_list_names: list[str],
    the_limit: int = 1000,
):
    records = fetch_top_messages(seed_list_names, start_date, end_date, the_limit)

    # Remove api_response field
    [record.pop("api_response") for record in records]

    return records


def generate_markdown_hyperlink(record):
    url = f"https://t.me/{record['channel_name']}/{record['message_id']}"
    return f"[{url}]({url})"


def make_message_table(records: list[dict], seed_list_names: list[str]) -> list[dict]:
    if len(records) == 0:
        return records

    df = pd.DataFrame.from_records(records)

    seed_df = pd.DataFrame.from_records(get_seed_list_preview(seed_list_names))

    df = df.merge(seed_df, on="channel_id", how="left")

    df["url"] = df.apply(lambda x: generate_markdown_hyperlink(x), axis=1)

    df = df[
        [
            "url",
            "message_datetime",
            "message_views",
            "message_forwards",
            "message_text",
            "channel_name",
            "channel_id",
            "message_id",
        ]
    ]

    return df.to_dict("records")


def render_message_table(
    start_date: str, end_date: str, seed_list_names: list[str]
) -> list[dict]:
    records = get_top_messages(start_date, end_date, seed_list_names)

    # Create table
    records = make_message_table(records, seed_list_names)
    return records


def translate_messages(records: list[dict]) -> list[dict]:
    df = pd.DataFrame.from_records(records)

    df["message_translated"] = df["message_text"].apply(
        lambda my_text: GoogleTranslator(source="auto", target="en").translate(my_text)
        if my_text is not None
        else None
    )

    df = df[
        [
            "url",
            "message_datetime",
            "message_views",
            "message_forwards",
            "message_translated",
            "message_text",
            "channel_name",
            "channel_id",
            "message_id",
        ]
    ]

    return df.to_dict("records")


def send_handles_to_tg_channel_metadata_lookup_queue(data_json: dict):
    send_data_to_queue([data_json], handles_queue)


def send_handles_to_tg_channel_messages_lookup_queue(records: list[dict]):
    send_data_to_queue(records, messages_queue)


def store_channel_messages(records: list[dict]):
    insert_data_into_channel_messages_table_advanced(records)


def extract_data_from_message_object(message: TelegramMessage) -> dict:
    message_dict = {
        "channel_id": message.to_dict()["peer_id"]["channel_id"],
        "message_id": message.to_dict()["id"],
        "message_datetime": message.to_dict()["date"],
        "message_views": message.to_dict()["views"],
        "message_forwards": message.to_dict()["forwards"],
        "message_text": message.to_dict()["message"],
        "forwardee_channel_id": None,
        "forwardee_message_id": None,
        "message_is_forward": False,
        "api_response": message.to_json(),
    }

    if message.fwd_from is not None:
        message_dict["message_is_forward"] = True
        if message.to_dict()["fwd_from"]["from_id"] is not None:
            if "channel_id" in message.to_dict()["fwd_from"]["from_id"].keys():
                message_dict["forwardee_channel_id"] = message.to_dict()["fwd_from"][
                    "from_id"
                ]["channel_id"]
                message_dict["forwardee_message_id"] = message.to_dict()["fwd_from"][
                    "channel_post"
                ]

    return message_dict


def retrieve_channel_messages_from_telegram(
    channel_name: str, app_name: str, api_id: int, api_hash: str
) -> list[dict]:
    new_max_id = 0
    messages = []
    with TelegramClient(app_name, api_id, api_hash) as client:
        while True:
            message_iterator = client.iter_messages(
                channel_name, min_id=0, max_id=new_max_id, limit=100
            )

            try:
                new_messages = list(message_iterator)
            except Exception as e:
                print(e)
                new_messages = []

            # Calculate new_max_id
            if len(new_messages) > 0:
                new_max_id = min([message.id for message in new_messages])
                messages += new_messages

                print(
                    f"found {len(messages)} messages so far, and set new_max_id={new_max_id}"
                )

            # Stopping condition
            if len(new_messages) < 100:
                break

            # Respectful pause so as not to flood the API
            time.sleep(1)

    records = [
        extract_data_from_message_object(message)
        for message in messages
        if message.to_dict()["_"] == "Message"
    ]

    return records


def retrieve_and_save_channel_messages(
    channel_name: str, app_name: str, api_id: int, api_hash: str
):
    # Retrieve messages from Telegram API
    records = retrieve_channel_messages_from_telegram(
        channel_name, app_name, api_id, api_hash
    )

    # Save data locally
    store_channel_messages(records)
