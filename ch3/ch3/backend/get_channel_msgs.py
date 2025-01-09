from ..utilities.logic_ch3 import retrieve_and_save_channel_messages
from ..utilities.mq_ch3 import get_channel
import json
from ..config import config, messages_queue


def consumer(app_name: str, api_id: int, api_hash: str):
    def callback(ch, method, properties, body):
        # Receive and parse message
        message = json.loads(body.decode("utf-8"))
        channel_name = message["handle"]
        print(f"retrieving messages from @{channel_name}...")

        # Retrieve and save the channel's messages from Telegram API
        retrieve_and_save_channel_messages(channel_name, app_name, api_id, api_hash)

        # Contact queue to acknowledge task completion
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("task complete!")

    input_channel = get_channel()
    input_channel.queue_declare(queue=messages_queue, durable=True)
    input_channel.basic_qos(prefetch_count=1)
    input_channel.basic_consume(on_message_callback=callback, queue=messages_queue)
    print("listening for handles...")
    input_channel.start_consuming()


def run(args_credentials):
    consumer(
        config[args_credentials]["app-name"],
        config[args_credentials]["api-id"],
        config[args_credentials]["api-hash"],
    )
