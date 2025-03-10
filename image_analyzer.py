import requests
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ImageAnalyzer:

    def __init__(self, hf_token, yndx_api_key):
        self.hf_token = hf_token
        self.yndx_api_key = yndx_api_key  # Оставляем для совместимости, но не используем
        self.translation_dict = {
            "tattoo": "татуировка",
            "sketch": "эскиз",
            "design": "дизайн",
            "ink": "чернила",
            "art": "искусство",
            "drawing": "рисунок",
            "outline": "контур",
            "line": "линия"
        }

    def get_image_caption(self, image_url):
        logging.info(f"Скачивание изображения: {image_url}")
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                logging.error(
                    f"Не удалось скачать изображение: {response.status_code}")
                return "татуировка, эскиз"
            image_data = response.content
        except Exception as e:
            logging.error(f"Ошибка загрузки изображения: {e}")
            return "татуировка, эскиз"

        caption = self._try_hugging_face(image_data)
        if not caption:
            caption = self._try_alternative(image_data)
        if not caption:
            logging.warning(
                "Не удалось получить подпись, возвращаем значение по умолчанию"
            )
            return "татуировка, эскиз"

        logging.info(f"Подпись для перевода: {caption}")
        translated_caption = self._translate(caption)
        return translated_caption if translated_caption else "татуировка, эскиз"

    def _try_hugging_face(self, image_data):
        try:
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
            response = requests.post(url,
                                     headers=headers,
                                     data=image_data,
                                     timeout=10)
            if response.status_code == 200:
                caption = response.json()[0]['generated_text']
                logging.info(f"Hugging Face подпись: {caption}")
                return caption
            logging.warning(
                f"Hugging Face не сработал: {response.status_code}")
            return None
        except Exception as e:
            logging.warning(f"Ошибка Hugging Face: {e}")
            return None

    def _try_alternative(self, image_data):
        try:
            url = "https://api.ttt.tf/v1/caption"
            response = requests.post(
                url, files={'image': ('image.jpg', image_data)}, timeout=15)
            if response.status_code == 200:
                caption = response.json().get('caption', 'tattoo design')
                logging.info(f"Alternative API подпись: {caption}")
                return caption
            logging.warning(
                f"Alternative API не сработал: {response.status_code}")
            return None
        except Exception as e:
            logging.warning(f"Ошибка Alternative API: {e}")
            return None

    def _translate(self, caption):
        # Шаг 1: Пробуем Google Translate
        try:
            logging.info("Попытка перевода через Google Translate")
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en",
                "tl": "ru",
                "dt": "t",
                "q": caption
            }
            response = requests.get(url, params=params, timeout=8)
            if response.status_code == 200:
                translated = ''.join(part[0] for part in response.json()[0])
                logging.info(f"Google Translate перевод: {translated}")
                return translated
            logging.warning(
                f"Google Translate не сработал: {response.status_code}")
        except Exception as e:
            logging.warning(f"Ошибка Google Translate: {e}")

        # Шаг 2: Если Google не сработал, пробуем LibreTranslate
        try:
            logging.info("Попытка перевода через LibreTranslate")
            url = "https://libretranslate.de/translate"
            payload = {
                "q": caption,
                "source": "en",
                "target": "ru",
                "format": "text"
            }
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                translated = response.json()["translatedText"]
                logging.info(f"LibreTranslate перевод: {translated}")
                return translated
            logging.warning(
                f"LibreTranslate не сработал: {response.status_code}")
        except Exception as e:
            logging.warning(f"Ошибка LibreTranslate: {e}")

        # Шаг 3: Если ничего не сработало, используем внутренний словарь
        logging.info("Перевод через внутренний словарь")
        translated = ' '.join(
            self.translation_dict.get(word.lower(), word)
            for word in caption.split())
        return translated
