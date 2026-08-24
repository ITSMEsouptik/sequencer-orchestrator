import logging
import sys

from config import Config
from consumer import VendorConsumer
from idempotency import IdempotencyStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)


def main() -> None:
    config = Config.from_env()
    idempotency = IdempotencyStore(config.idempotency_db_path)
    consumer = VendorConsumer(config, idempotency)
    consumer.run()


if __name__ == "__main__":
    main()
