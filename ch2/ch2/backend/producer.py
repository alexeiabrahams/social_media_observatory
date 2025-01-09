from ch2.ch2.config import handles_queue
from ch2.ch2.utilities.mq_ch2 import send_data_to_queue


message = {"handles": ["rybar", "mig41"], "seed_list": "russian_disinfo"}


def run():
    send_data_to_queue([message], handles_queue)


if __name__ == "__main__":
    run()
