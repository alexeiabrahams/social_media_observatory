from ..config import messages_queue
from ..utilities.mq_ch3 import send_data_to_queue

message = {"handle": "rybar"}


def run():
    send_data_to_queue([message], messages_queue)


if __name__ == "__main__":
    run()
