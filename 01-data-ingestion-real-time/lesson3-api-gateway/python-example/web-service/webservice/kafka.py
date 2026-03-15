import dataclasses
import json
import logging
from typing import Optional

from confluent_kafka import Producer, Message
import hashlib

logger = logging.getLogger(__name__)


def normalize_message_payload(message) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, dict) and 'payload' in message:
        return message['payload']
    return json.dumps(message)


def create_producer() -> Producer:
    return Producer({'bootstrap.servers': 'localhost:29092',
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
            print('Failure' + error)
            logger.error('Record was not correctly delivered: %s', error)
        else:
            print('success')
            data_holder.handle_successful_delivery(result)

    return handle_delivery_result
