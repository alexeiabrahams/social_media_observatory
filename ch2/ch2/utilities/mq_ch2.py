import pika
from ..config import pikaparams
import json


def get_channel():
    connection = pika.BlockingConnection(pikaparams)
    channel = connection.channel()
    return channel


def send_data_to_queue(messages: list[dict], target_queue: str):
    channel = get_channel()
    channel.queue_declare(queue=target_queue, durable=True)

    # Send message to queue
    for message in messages:
        channel.basic_publish(
            exchange="",
            routing_key=target_queue,
            body=json.dumps(message).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )
