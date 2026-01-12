import cv2
import numpy as np
import pytesseract
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self, languages=None):
        self.languages = languages or ['ru', 'en']
        logger.info(f"OCR Engine инициализирован: {self.languages}")
    
    def recognize_text(self, image_path: str) -> dict:
        """Распознавание текста"""
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                return {'success': False, 'error': 'Файл не найден'}
            
            logger.info(f"Обработка: {image_path}")
            
            # Создаем несколько версий изображения
            images = self._preprocess_image(str(image_path))
            
            # Распознаем текст из лучшей версии
            best_text = ""
            for processed_img in images:
                text = self._recognize_with_tesseract(processed_img)
                if len(text) > len(best_text):
                    best_text = text
            
            return {
                'success': True,
                'full_text': best_text.strip(),
                'statistics': {
                    'characters': len(best_text.strip()),
                    'words': len(best_text.strip().split())
                }
            }
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return {'success': False, 'error': str(e)}
    
    def _preprocess_image(self, image_path: str) -> list:
        """Предобработка изображения - 5 версий"""
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        versions = [gray]
        
        # Версия 2: CLAHE контраст
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        versions.append(enhanced)
        
        # Версия 3: Otsu бинаризация
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        versions.append(otsu)
        
        # Версия 4: Адаптивная бинаризация
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        versions.append(adaptive)
        
        # Версия 5: Морфология
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        versions.append(morph)

        # Добавить версию 6: очистка шумов (денойзинг)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 10, 21)
        versions.append(denoised)

        # Добавить версию 7: Увеличение резкости
        kernel_sharp = np.array([[-1, -1, -1],
                                 [-1, 9, -1],
                                 [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, kernel_sharp)
        versions.append(sharpened)
        
        return versions
    
    def _recognize_with_tesseract(self, image: np.ndarray) -> str:
        """Распознавание Tesseract"""
        try:
            text = pytesseract.image_to_string(image, lang='rus+eng')
            return text
        except:
            return ""
