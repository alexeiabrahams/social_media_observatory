from ch4.backend.get_channel_msgs import run
import argparse

parser = argparse.ArgumentParser(
    description="This script retrieves Telegram channel messages."
)
parser.add_argument(
    "--credentials",
    default="telegram-credentials-1",
    help="Credentials header from the config file (ex. telegram-credentials-1).",
)

args = parser.parse_args()

print(f"using {args.credentials} for credentials...")
run(args.credentials)
