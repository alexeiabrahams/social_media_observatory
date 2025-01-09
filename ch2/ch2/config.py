import os
import platform
import configparser
import pika

HOME_DIR = (
    os.environ["USERPROFILE"] if platform.system() == "Windows" else os.environ["HOME"]
)

config_file_full_path = os.path.join(HOME_DIR, "smo_config.cfg")
config = configparser.ConfigParser()
config.read(config_file_full_path)

pikaparams = pika.ConnectionParameters(
    config["rabbit-mq"]["host"],
    credentials=pika.PlainCredentials(
        config["rabbit-mq"]["user"], config["rabbit-mq"]["password"]
    ),
    heartbeat=int(config["rabbit-mq"]["heartbeat"]),
    blocked_connection_timeout=int(config["rabbit-mq"]["blocked-connection-timeout"]),
)

handles_queue = config["rabbit-mq"]["telegram-handles-queue"]
channel_metadata_table_name = config["telegram-db"]["channel-metadata-table"]
seed_table_name = config["telegram-db"]["channel-seed-table"]
