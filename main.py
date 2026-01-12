import argparse
import sys
import logging
from pathlib import Path

from config import DEFAULT_LANGUAGES, OUTPUT_DIR, SUPPORTED_FORMATS
from ocr_engine import OCREngine
from error_checker import ErrorChecker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OCRApplication:
    def __init__(self, languages=None):
        self.languages = languages or DEFAULT_LANGUAGES
        logger.info(f"Инициализация: языки={self.languages}")
        self.ocr = OCREngine(self.languages)
        self.checker = ErrorChecker()
    
    def process_image(self, image_path: str, check_errors: bool = True, save_output: bool = False):
        """Обработка одного изображения"""
        result = self.ocr.recognize_text(image_path)
        
        if not result['success']:
            print(f" Ошибка: {result['error']}")
            return
        
        text = result['full_text']
        stats = result['statistics']
        
        print("\n" + "="*70)
        print("  РАСПОЗНАННЫЙ ТЕКСТ:")
        print("="*70)
        print(text if text else "(пусто)")
        print()
        print("  СТАТИСТИКА:")
        print(f"  Символов: {stats['characters']}")
        print(f"  Слов: {stats['words']}")
        
        if check_errors:
            errors = self.checker.check_text(text)
            print(f"\n  НАЙДЕНО ОШИБОК: {errors['error_count']}")
            
            if errors['errors']:
                for i, err in enumerate(errors['errors'], 1):
                    print(f"  {i}. '{err['text']}' → '{err['suggestion']}'")
        
        print("="*70 + "\n")
        
        if save_output:
            output_file = OUTPUT_DIR / "result.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f" Результат сохранен: {output_file}\n")

def main():
    parser = argparse.ArgumentParser(description='OCR: Распознавание текста')
    parser.add_argument('-i', '--image', help='Путь к изображению')
    parser.add_argument('-d', '--folder', help='Папка с изображениями')
    parser.add_argument('--no-check', action='store_true', help='Без проверки ошибок')
    parser.add_argument('-o', '--output', action='store_true', help='Сохранить результат')
    
    args = parser.parse_args()
    
    if not args.image and not args.folder:
        parser.print_help()
        sys.exit(1)
    
    try:
        app = OCRApplication()
        
        if args.image:
            app.process_image(args.image, check_errors=not args.no_check, save_output=args.output)
        else:
            folder = Path(args.folder)
            for img_file in folder.glob('*'):
                if img_file.suffix.lower() in SUPPORTED_FORMATS:
                    print(f"\n Обработка: {img_file.name}")
                    app.process_image(str(img_file), check_errors=not args.no_check)
    
    except KeyboardInterrupt:
        print("\n Прервано")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        print(f" Ошибка: {e}")

if __name__ == '__main__':
    main()
