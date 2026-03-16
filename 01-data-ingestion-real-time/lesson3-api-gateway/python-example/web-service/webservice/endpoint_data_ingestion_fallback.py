import json
import os
import time
from pathlib import Path

from flask import request, Response

from webservice import kafka
from webservice.kafka import CallbackDataHolder
from webservice.paths import get_lesson_root


def store_failed_deliveries(topic: str, failed_deliveries, fallback_root: Path, app) -> None:
    file_name = f'data_{round(time.time()*1000)}'
    topic_path = fallback_root / f'topic={topic}'
    os.makedirs(topic_path, exist_ok=True)
    output_path = topic_path / file_name
    output_path.write_text(
        '\n'.join([json.dumps({'key': event['key'], 'value': event['payload']}) for event in failed_deliveries])
    )
    app.logger.warning(
        'Fallback batch stored on disk: file=%s records=%s',
        output_path,
        len(failed_deliveries),
    )


def create_data_ingestion_with_fallback_storage(app):
    kafka_producer = kafka.create_producer()

    @app.route('/dataingestionfallback/ingest/<string:topic>/<string:event_key>', methods=['POST'])
    def new_data_with_fallback(topic: str, event_key: str):
        json_data_to_deliver = json.loads(request.data)
        fallback_root = get_lesson_root() / 'fallback'
        bootstrap_servers = kafka.get_bootstrap_servers()
        broker_reachable = kafka.bootstrap_servers_reachable()
        app.logger.info(
            'Fallback endpoint invoked: topic=%s event_key=%s batch_size=%s fallback_root=%s bootstrap_servers=%s broker_reachable=%s',
            topic,
            event_key,
            len(json_data_to_deliver),
            fallback_root,
            bootstrap_servers,
            broker_reachable,
        )
        if not broker_reachable:
            failed_deliveries = [
                {'key': event_key, 'payload': kafka.normalize_message_payload(message)}
                for message in json_data_to_deliver
            ]
            app.logger.warning('Kafka bootstrap servers are unreachable; storing batch directly to fallback storage.')
            store_failed_deliveries(topic, failed_deliveries, fallback_root, app)
            return Response(json.dumps({'success': True, 'failed': []}),
                            status=200, mimetype='application/json')

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
        app.logger.info(
            'Fallback delivery result: topic=%s event_key=%s success=%s failed_count=%s total_count=%s',
            topic,
            event_key,
            is_successful_delivery,
            len(failed_deliveries),
            len(json_data_to_deliver),
        )
        if not is_successful_delivery and len(failed_deliveries) == len(json_data_to_deliver):
            store_failed_deliveries(topic, failed_deliveries, fallback_root, app)
            return Response(json.dumps({'success': True, 'failed': []}),
                            status=200, mimetype='application/json')
        else:
            if failed_deliveries:
                app.logger.warning(
                    'Partial failure did not trigger disk fallback: failed_count=%s total_count=%s',
                    len(failed_deliveries),
                    len(json_data_to_deliver),
                )
            return Response(json.dumps({'success': is_successful_delivery, 'failed': failed_deliveries}),
                            status=200, mimetype='application/json')
