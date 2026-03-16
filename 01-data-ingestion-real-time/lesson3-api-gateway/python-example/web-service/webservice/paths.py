import os
from pathlib import Path


def get_lesson_root() -> Path:
    default_path = Path(__file__).resolve().parents[2] / 'fallback-pipeline' / 'data' / 'lesson3'
    configured_path = os.environ.get('LESSON3_DATA_DIR')
    return Path(configured_path) if configured_path else default_path
