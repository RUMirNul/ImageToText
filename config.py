from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

DEFAULT_LANGUAGES = ['ru', 'en']
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
USE_LANGUAGE_TOOL = False
LOG_LEVEL = 'INFO'