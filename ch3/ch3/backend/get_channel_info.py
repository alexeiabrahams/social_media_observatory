from ..config import *
from ..utilities.logic_ch3 import retrieve_and_save_channel_metadata
from ..utilities.mq_ch3 import get_channel
import json


def consumer(app_name, api_id, api_hash):
    def callback(ch, method, properties, body):
        # Receive and parse message
        message = json.loads(body.decode("utf-8"))
        channel_names = message["handles"]
        seed_list_name = message["seed_list"]

        retrieve_and_save_channel_metadata(
            channel_names, app_name, api_id, api_hash, seed_list_name
        )

        # Contact queue to acknowledge task completion
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("task complete!")

    input_channel = get_channel()
    input_channel.queue_declare(queue=handles_queue, durable=True)
    input_channel.basic_qos(prefetch_count=1)
    input_channel.basic_consume(on_message_callback=callback, queue=handles_queue)
    print("listening for handles to look up...")
    input_channel.start_consuming()


def run(args_credentials):
    consumer(
        config[args_credentials]["app-name"],
        config[args_credentials]["api-id"],
        config[args_credentials]["api-hash"],
    )
