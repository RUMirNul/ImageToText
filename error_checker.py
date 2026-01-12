import logging
from typing import Dict, List
import re

logger = logging.getLogger(__name__)


class ErrorChecker:
    """Проверка и исправление ошибок OCR и орфографии"""

    def __init__(self, language='ru'):
        self.language = language
        logger.info(f"ErrorChecker инициализирован для языка: {language}")

        # Пытаемся загрузить спеллчекер
        try:
            from pyspellchecker import SpellChecker
            self.spell = SpellChecker(language=language)
            self.has_spellchecker = True
            logger.info("✓ pyspellchecker загружен")
        except Exception as e:
            logger.warning(f"pyspellchecker ошибка: {e}")
            self.has_spellchecker = False
            self.spell = None

        # Пытаемся загрузить LanguageTool для грамматики
        try:
            from language_tool_python import LanguageTool
            self.lt = LanguageTool('ru')
            self.has_language_tool = True
            logger.info("✓ LanguageTool загружен")
        except Exception as e:
            logger.warning(f"LanguageTool ошибка: {e}")
            self.has_language_tool = False
            self.lt = None

        # Словарь частых контекстных ошибок
        self.context_errors = {
            'в нес': 'в нее',
            'на нес': 'на нее',
            'к неи': 'к ней',
            'из нес': 'из нее',
            'для нес': 'для нее',
            'ве': 'её',
            'кнам': 'к нам'
        }

    def check_text(self, text: str, check_grammar: bool = True, check_ocr_errors: bool = True) -> Dict:
        """
        Проверить текст на ошибки OCR и орфографию
        """
        logger.info(f"Проверка текста ({len(text)} символов)")

        errors = []
        corrected_text = text

        # 0. Проверка переносов слов (дефис + перевод строки)
        hyphen_errors = self._fix_word_hyphenation(corrected_text)
        errors.extend(hyphen_errors)
        for error in hyphen_errors:
            corrected_text = corrected_text.replace(error['original'], error['suggestion'])

        # 1. Проверка OCR ошибок
        if check_ocr_errors:
            ocr_errors = self._check_ocr_errors(text)
            errors.extend(ocr_errors)
            for error in ocr_errors:
                corrected_text = corrected_text.replace(error['original'], error['suggestion'])

        # 2. Проверка контекстных ошибок
        context_errors = self._check_context_errors(corrected_text)
        errors.extend(context_errors)
        for error in context_errors:
            corrected_text = corrected_text.replace(error['original'], error['suggestion'])

        # 3. Проверка грамматики с LanguageTool
        if check_grammar and self.has_language_tool:
            grammar_errors = self._check_grammar(corrected_text)
            errors.extend(grammar_errors)
            for error in grammar_errors:
                if error.get('confidence', 0) > 0.8:
                    corrected_text = corrected_text.replace(error['original'], error['suggestion'], 1)

        # 4. Проверка орфографии
        if check_grammar and self.has_spellchecker:
            spell_errors = self._check_spelling(corrected_text)
            errors.extend(spell_errors)
            for error in spell_errors:
                corrected_text = corrected_text.replace(error['original'], error['suggestion'], 1)

        logger.info(f"Найдено ошибок: {len(errors)}")

        return {
            'success': True,
            'original_text': text,
            'corrected_text': corrected_text,
            'errors': errors,
            'error_count': len(errors),
            'error_types': self._count_error_types(errors)
        }

    def _fix_word_hyphenation(self, text: str) -> List[Dict]:
        """
        Исправление переносов слов (дефис + перевод строки).
        Пример: "чер-\nный" → "черный"
        """
        errors = []

        # Ищем паттерн: буква + дефис + новая строка + буква
        pattern = r'([а-яёА-ЯЁ])-\n([а-яёА-ЯЁ])'

        matches = list(re.finditer(pattern, text))

        for match in matches:
            original = match.group(0)  # полный матч (например: "р-\nн")
            part1 = match.group(1)  # первая часть (р)
            part2 = match.group(2)  # вторая часть (н)

            # Восстанавливаем слово без дефиса и переноса
            suggestion = part1 + part2

            # Находим полное слово для контекста
            start = match.start()
            end = match.end()

            # Ищем начало слова (в начале строки или после пробела)
            word_start = start
            while word_start > 0 and text[word_start - 1].isalpha():
                word_start -= 1

            # Ищем конец слова (после второго символа)
            word_end = end
            while word_end < len(text) and text[word_end].isalpha():
                word_end += 1

            full_original = text[word_start:word_end]
            full_suggestion = text[word_start:start] + suggestion + text[end:word_end]

            errors.append({
                'type': 'hyphenation_error',
                'original': full_original,
                'suggestion': full_suggestion,
                'text': original,
                'description': f'Перенос слова: "{full_original}" → "{full_suggestion}"'
            })

        return errors

    def _check_ocr_errors(self, text: str) -> List[Dict]:
        """Проверка типичных OCR ошибок"""
        errors = []
        replacements = {
            '0': 'О',
            '1': 'І',
            '3': 'З',
            'l': 'і',
        }

        words = re.findall(r'\b\w+\b', text)
        for word in words:
            original_word = word
            corrected_word = word

            for bad_char, good_char in replacements.items():
                if bad_char in word:
                    corrected_word = corrected_word.replace(bad_char, good_char)

            if corrected_word != original_word:
                errors.append({
                    'type': 'ocr_error',
                    'original': original_word,
                    'suggestion': corrected_word,
                    'text': original_word,
                    'description': f'Ошибка OCR: {original_word} → {corrected_word}'
                })

        return errors

    def _check_context_errors(self, text: str) -> List[Dict]:
        """Проверка контекстных ошибок"""
        errors = []

        for wrong_phrase, correct_phrase in self.context_errors.items():
            if wrong_phrase.lower() in text.lower():
                pattern = re.compile(re.escape(wrong_phrase), re.IGNORECASE)
                for match in pattern.finditer(text):
                    errors.append({
                        'type': 'context_error',
                        'original': match.group(),
                        'suggestion': correct_phrase,
                        'text': match.group(),
                        'description': f'Контекстная ошибка: "{match.group()}" → "{correct_phrase}"'
                    })

        return errors

    def _check_grammar(self, text: str) -> List[Dict]:
        """Проверка грамматики"""
        if not self.has_language_tool or not self.lt:
            return []

        errors = []

        try:
            matches = self.lt.check(text)

            for match in matches:
                if match.category in ['TYPOS', 'GRAMMAR']:
                    if match.replacements:
                        suggestion = match.replacements[0]
                        original_text = text[match.offset:match.offset + match.length]

                        errors.append({
                            'type': 'grammar_error',
                            'original': original_text,
                            'suggestion': suggestion,
                            'text': original_text,
                            'description': f'Грамматика: "{original_text}" → "{suggestion}"',
                            'confidence': 0.8
                        })
        except Exception as e:
            logger.debug(f"Ошибка при проверке грамматики: {e}")

        return errors

    def _check_spelling(self, text: str) -> List[Dict]:
        """Проверка орфографии"""
        if not self.has_spellchecker or not self.spell:
            return []

        errors = []

        try:
            words = re.findall(r'\b[а-яёА-ЯЁ]+\b', text)
            misspelled = self.spell.unknown(words)

            for word in misspelled:
                candidates = self.spell.candidates(word)

                if candidates:
                    suggestion = list(candidates)[0]
                    errors.append({
                        'type': 'spelling_error',
                        'original': word,
                        'suggestion': suggestion,
                        'text': word,
                        'description': f'Орфография: {word} → {suggestion}',
                        'candidates': list(candidates)[:3]
                    })
        except Exception as e:
            logger.debug(f"Ошибка при проверке орфографии: {e}")

        return errors

    def _count_error_types(self, errors: List[Dict]) -> Dict:
        """Подсчитать ошибки по типам"""
        counts = {}
        for error in errors:
            error_type = error.get('type', 'unknown')
            counts[error_type] = counts.get(error_type, 0) + 1
        return counts

    def get_stats(self, errors: List[Dict]) -> Dict:
        """Получить статистику ошибок"""
        return {
            'total_errors': len(errors),
            'error_types': self._count_error_types(errors),
            'by_type': {
                'ocr_errors': len([e for e in errors if e['type'] == 'ocr_error']),
                'context_errors': len([e for e in errors if e['type'] == 'context_error']),
                'grammar_errors': len([e for e in errors if e['type'] == 'grammar_error']),
                'spelling_errors': len([e for e in errors if e['type'] == 'spelling_error']),
            }
        }

    def close(self):
        """Закрыть ресурсы"""
        logger.info("ErrorChecker закрыт")
