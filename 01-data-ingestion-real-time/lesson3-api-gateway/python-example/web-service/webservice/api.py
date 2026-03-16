#!flask/bin/python
import os
import sys
from pathlib import Path

from flask import Flask, logging
from flask_cors import CORS

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webservice.endpoint_data_ingestion import create_data_ingestion_without_fallback_storage
from webservice.endpoint_data_ingestion_fallback import create_data_ingestion_with_fallback_storage
from webservice.paths import get_lesson_root

app = Flask(__name__.split('.')[0])
CORS(app, allow_headers='*')

if __name__ == '__main__':
    lesson_root = get_lesson_root()
    fallback_root = lesson_root / 'fallback'
    os.makedirs(fallback_root, exist_ok=True)
    app.logger.setLevel('INFO')
    app.logger.info('Lesson data root resolved to: %s', lesson_root)
    app.logger.info('Fallback directory resolved to: %s', fallback_root)
    # Here we include the definitions for all endpoint
    create_data_ingestion_without_fallback_storage(app)
    create_data_ingestion_with_fallback_storage(app)

    app.run(debug=True, port=8080)
