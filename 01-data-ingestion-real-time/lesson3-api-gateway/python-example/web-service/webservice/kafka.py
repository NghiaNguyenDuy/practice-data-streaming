import dataclasses
import json
import logging
import os
import socket
from typing import Optional

from confluent_kafka import Producer, Message

logger = logging.getLogger(__name__)


def normalize_message_payload(message) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, dict) and 'payload' in message:
        return message['payload']
    return json.dumps(message)


def get_bootstrap_servers() -> str:
    return os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092')


def bootstrap_servers_reachable(timeout_seconds: float = 1.0) -> bool:
    for server in get_bootstrap_servers().split(','):
        host, _, port = server.strip().partition(':')
        if not host or not port:
            continue
        try:
            with socket.create_connection((host, int(port)), timeout=timeout_seconds):
                return True
        except OSError:
            logger.warning('Kafka bootstrap server not reachable: %s', server.strip())
    return False


def create_producer() -> Producer:
    bootstrap_servers = get_bootstrap_servers()
    logger.info('Creating Kafka producer for bootstrap servers: %s', bootstrap_servers)
    return Producer({'bootstrap.servers': bootstrap_servers,
                     'linger.ms': 10 * 1000,  # 10 seconds
                     'batch.num.messages': 10,
                     'retries': 3
                     })


@dataclasses.dataclass
class InputMessageHolder:
    delivery_success: bool
    key: Optional[str] = None
    payload: Optional[str] = None


class CallbackDataHolder:

    def __init__(self, event_key, initial_messages):
        self.messages_delivery_status = {}
        for payload in initial_messages:
            normalized_payload = normalize_message_payload(payload)
            self.messages_delivery_status[CallbackDataHolder._get_message_key(normalized_payload)] = InputMessageHolder(
                key=event_key, payload=normalized_payload, delivery_success=False
            )

    def handle_successful_delivery(self, delivery_message: Message):
        message_key = CallbackDataHolder._get_message_key(delivery_message.value().decode('utf-8'))
        self.messages_delivery_status[message_key] = InputMessageHolder(delivery_success=True)

    def get_failed_deliveries(self):
        return [{'key': event.key, 'payload': event.payload} for event in self.messages_delivery_status.values() if
                not event.delivery_success]

    @staticmethod
    def _get_message_key(payload):
        event_as_dict = payload
        if isinstance(payload, str):
            event_as_dict = json.loads(payload)
        return event_as_dict['id']


def create_delivery_callback_function(data_holder: CallbackDataHolder):
    def handle_delivery_result(error, result: Message):
        if error:
            logger.error('Record was not correctly delivered: %s', error)
        else:
            logger.info('Record delivered successfully: topic=%s partition=%s offset=%s',
                        result.topic(), result.partition(), result.offset())
            data_holder.handle_successful_delivery(result)

    return handle_delivery_result
