import json
import os
import pathlib
import time

from flask import request, Response

from webservice import kafka
from webservice.kafka import CallbackDataHolder


def create_data_ingestion_with_fallback_storage(app):
    kafka_producer = kafka.create_producer()

    @app.route('/dataingestionfallback/ingest/<string:topic>/<string:event_key>', methods=['POST'])
    def new_data_with_fallback(topic: str, event_key: str):
        json_data_to_deliver = json.loads(request.data)
        callback_data_holder = CallbackDataHolder(event_key, json_data_to_deliver)
        for message_to_deliver in json_data_to_deliver:
            normalized_payload = kafka.normalize_message_payload(message_to_deliver)
            kafka_producer.produce(
                topic=topic,
                key=bytes(event_key, encoding='utf-8'),
                value=bytes(normalized_payload, encoding='utf-8'),
                on_delivery=kafka.create_delivery_callback_function(callback_data_holder))

        kafka_producer.flush(timeout=20)

        failed_deliveries = callback_data_holder.get_failed_deliveries()
        is_successful_delivery = True if not failed_deliveries else False
        if not is_successful_delivery and len(failed_deliveries) == len(json_data_to_deliver):
            file_name = f'data_{round(time.time()*1000)}'
            topic_path = f'/tmp/bde-snippets-3/lesson3/fallback/topic={topic}'
            os.makedirs(topic_path, exist_ok=True)
            pathlib.Path(f'{topic_path}/{file_name}')\
                .write_text('\n'.join([json.dumps({'key': event['key'], 'value': event['payload']}) for event in failed_deliveries]))
            return Response(json.dumps({'success': True, 'failed': []}),
                            status=200, mimetype='application/json')
        else:
            return Response(json.dumps({'success': is_successful_delivery, 'failed': failed_deliveries}),
                            status=200, mimetype='application/json')
