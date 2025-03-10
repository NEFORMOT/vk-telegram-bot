import os
import schedule
import time
import sys
import json
import random
import logging
import requests
from datetime import datetime
from config import Config
from image_analyzer import ImageAnalyzer
from keywords import sketch_keywords, tattoo_keywords, in_progress_keywords, equipment_keywords, appointment_keywords, equipment_and_studio_keywords
from compliments import (
    weekly_compliments, sketch_compliments, tattoo_compliments, in_progress_compliments,
    equipment_compliments, appointment_compliments, client_interactions_compliments,
    tattoo_ideas_compliments, equipment_and_studio_compliments, no_photo_message
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Создаём объект для анализа изображений
analyzer = ImageAnalyzer(Config.HF_TOKEN, Config.YNDX_API_KEY)
logging.info("Инициализация ImageAnalyzer завершена")

# Работа с состоянием
def load_state():
    logging.info("Загрузка состояния из файла...")
    try:
        with open(Config.STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            logging.info("Состояние успешно загружено")
            return state
    except (FileNotFoundError, json.JSONDecodeError):
        logging.info("Файл состояния не найден или повреждён, создаётся новый")
        return {
            "last_checked": None,
            "processed_posts": {},
            "weekly_compliments_used": [],
            "client_interactions_compliments_used": [],
            "tattoo_ideas_compliments_used": [],
            "equipment_and_studio_compliments_used": [],
            "sketch_compliments_used": [],
            "tattoo_compliments_used": [],
            "in_progress_compliments_used": [],
            "equipment_compliments_used": [],
            "appointment_compliments_used": []
        }

import subprocess

def save_state(state):
    logging.info("Сохранение состояния в файл...")
    try:
        with open(Config.STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        subprocess.run(['git', 'config', '--global', 'user.email', 'bot@example.com'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Bot'], check=True)
        subprocess.run(['git', 'add', Config.STATE_FILE], check=True)
        result = subprocess.run(['git', 'commit', '-m', f'Update {Config.STATE_FILE}'], capture_output=True, text=True)
        if result.returncode == 0:
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            logging.info("Состояние успешно сохранено")
        else:
            logging.info("Нет изменений для коммита")
    except Exception as e:
        logging.error(f"Ошибка сохранения состояния: {e}")

# Функция для выбора комплимента без повторений
def get_unique_compliment(compliments_list, used_list_key, state):
    used_compliments = state.get(used_list_key, [])
    available_compliments = [comp for comp in compliments_list if comp not in used_compliments]
    if not available_compliments:
        state[used_list_key] = []
        available_compliments = compliments_list
        logging.info(f"Список комплиментов для {used_list_key} исчерпан, перезапуск цикла")
    compliment = random.choice(available_compliments)
    state[used_list_key].append(compliment)
    save_state(state)
    return compliment

# Функция для генерации случайного времени между 10:00 и 13:00
def get_random_time():
    hours = random.randint(10, 12)
    minutes = random.randint(0, 59)
    return f"{hours:02d}:{minutes:02d}"

# Извлечение медиа (фото или видео) из поста
def get_media_url(post):
    logging.info("Извлечение URL медиа из поста")
    for attachment in post.get('attachments', []):
        if attachment.get('type') == 'photo':
            sizes = attachment.get('photo', {}).get('sizes', [])
            if sizes:
                url = max(sizes, key=lambda s: s.get('width', 0) * s.get('height', 0)).get('url')
                logging.info(f"Найден URL фото: {url}")
                return url, "photo"
        elif attachment.get('type') == 'video':
            video = attachment.get('video', {})
            owner_id = video.get('owner_id')
            video_id = video.get('id')
            if owner_id and video_id:
                url = f"https://vk.com/video{owner_id}_{video_id}"
                logging.info(f"Найден URL видео: {url}")
                return url, "video"
    logging.warning("Медиа (фото или видео) не найдено в посте")
    return None, None

# Классификация медиа
def classify_media(post_text, caption, media_type):
    logging.info(f"Классификация медиа: post_text={post_text}, caption={caption}, media_type={media_type}")
    caption_lower = caption.lower() if caption else ""
    post_text_lower = post_text.lower() if post_text else ""
    post_lines = post_text_lower.split('\n')
    first_line = post_lines[0] if post_lines else ""
    rest_text = '\n'.join(post_lines[1:]) if len(post_lines) > 1 else ""

    if caption_lower:
        if any(keyword in caption_lower for keyword in appointment_keywords):
            logging.info(f"Определён тип: appointment (по подписи: {caption_lower})")
            return "appointment"
        elif any(keyword in caption_lower for keyword in tattoo_keywords):
            logging.info(f"Определён тип: tattoo (по подписи: {caption_lower})")
            return "tattoo"
        elif any(keyword in caption_lower for keyword in in_progress_keywords):
            logging.info(f"Определён тип: in_progress (по подписи: {caption_lower})")
            return "in_progress"
        elif any(keyword in caption_lower for keyword in sketch_keywords):
            logging.info(f"Определён тип: sketch (по подписи: {caption_lower})")
            return "sketch"
        elif any(keyword in caption_lower for keyword in equipment_keywords):
            logging.info(f"Определён тип: equipment (по подписи: {caption_lower})")
            return "equipment"
        elif any(keyword in caption_lower for keyword in equipment_and_studio_keywords):
            logging.info(f"Определён тип: equipment_and_studio (по подписи: {caption_lower})")
            return "equipment_and_studio"

    if post_text_lower:
        if any(keyword in post_text_lower for keyword in appointment_keywords):
            logging.info(f"Определён тип: appointment (по тексту поста: {post_text_lower})")
            return "appointment"
        elif any(keyword in post_text_lower for keyword in in_progress_keywords):
            logging.info(f"Определён тип: in_progress (по тексту поста: {post_text_lower})")
            return "in_progress"
        elif any(keyword in post_text_lower for keyword in tattoo_keywords):
            logging.info(f"Определён тип: tattoo (по тексту поста: {post_text_lower})")
            return "tattoo"
        elif any(keyword in post_text_lower for keyword in sketch_keywords):
            logging.info(f"Определён тип: sketch (по тексту поста: {post_text_lower})")
            return "sketch"
        elif any(keyword in post_text_lower for keyword in equipment_keywords):
            logging.info(f"Определён тип: equipment (по тексту поста: {post_text_lower})")
            return "equipment"
        elif any(keyword in post_text_lower for keyword in equipment_and_studio_keywords):
            logging.info(f"Определён тип: equipment_and_studio (по тексту поста: {post_text_lower})")
            return "equipment_and_studio"

    if media_type == "video":
        logging.info("Видео без явной классификации, возвращаем 'tattoo' по умолчанию")
        return "tattoo"
    if media_type == "photo":
        logging.info("Фото без явной классификации, возвращаем 'tattoo' по умолчанию")
        return "tattoo"
    logging.info("Тип не определён, возвращаем 'tattoo' по умолчанию")
    return "tattoo"

# Выбор комплимента
def get_compliment(post_text, caption, media_type, state):
    logging.info("Выбор комплимента")
    image_type = classify_media(post_text, caption, media_type)
    logging.info(f"Выбран тип медиа: {image_type}")
    if image_type == "sketch":
        return get_unique_compliment(sketch_compliments, "sketch_compliments_used", state)
    elif image_type == "tattoo":
        return get_unique_compliment(tattoo_compliments, "tattoo_compliments_used", state)
    elif image_type == "in_progress":
        return get_unique_compliment(in_progress_compliments, "in_progress_compliments_used", state)
    elif image_type == "equipment":
        return get_unique_compliment(equipment_compliments, "equipment_compliments_used", state)
    elif image_type == "appointment":
        return get_unique_compliment(appointment_compliments, "appointment_compliments_used", state)
    elif image_type == "equipment_and_studio":
        return get_unique_compliment(equipment_and_studio_compliments, "equipment_and_studio_compliments_used", state)
    return get_unique_compliment(tattoo_compliments, "tattoo_compliments_used", state)

# Проверка новых постов
def check_new_post(state):
    logging.info("Начало проверки новых постов")
    last_checked = state["last_checked"]
    processed_posts = state["processed_posts"]
    url = f"https://api.vk.com/method/wall.get?owner_id={Config.GROUP_ID}&count=5&access_token={Config.VK_TOKEN}&v=5.131"
    try:
        logging.info(f"Запрос к VK API: {url}")
        response = requests.get(url, timeout=10).json()
        logging.info(f"Ответ VK API: {response}")
        if "response" in response and response["response"]["items"]:
            posts = response["response"]["items"]
            last_checked_date = None
            if last_checked:
                try:
                    last_checked_date = datetime.fromisoformat(last_checked)
                except ValueError:
                    logging.warning(f"Некорректный формат last_checked: {last_checked}, сбрасываем")
                    last_checked_date = None

            for post in posts:
                post_id = post["id"]
                post_date = datetime.fromtimestamp(post["date"])
                is_pinned = post.get("is_pinned", False)

                logging.info(f"Обработка поста: ID={post_id}, дата={post_date}, закреплён={is_pinned}")
                if str(post_id) not in processed_posts:
                    if not last_checked_date or post_date > last_checked_date:
                        if is_pinned and last_checked_date and post_date <= last_checked_date:
                            logging.info(f"Пропуск закреплённого старого поста: ID={post_id}")
                            continue
                        state["last_checked"] = post_date.isoformat()
                        processed_posts[str(post_id)] = True
                        save_state(state)
                        media_url, media_type = get_media_url(post)
                        logging.info(f"Новый пост найден: ID={post_id}, медиа={media_url}, тип={media_type}, текст={post.get('text', '')}")
                        return True, media_url, media_type, post.get("text", "")
            # Если новых постов нет, обновляем last_checked на дату самого нового поста
            if posts:
                newest_post_date = max(datetime.fromtimestamp(post["date"]) for post in posts)
                state["last_checked"] = newest_post_date.isoformat()
                save_state(state)
            logging.info("Новых незакреплённых постов не найдено")
        else:
            logging.warning("Ответ VK API не содержит постов")
    except Exception as e:
        logging.error(f"Ошибка проверки постов: {e}")
    logging.info("Новых постов не найдено или произошла ошибка")
    return False, None, None, ""

# Отправка сообщения в Telegram
def send_telegram_message(text):
    logging.info(f"Подготовка отправки сообщения в Telegram: {text}")
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    params_tracking = {"chat_id": Config.CHAT_ID_TRACKING, "text": text}
    params_her = {"chat_id": Config.CHAT_ID_HER, "text": text}
    try:
        response = requests.post(url, params=params_tracking, timeout=10)
        if response.status_code == 200:
            logging.info(f"Сообщение успешно отправлено в Telegram (tracking, chat_id={Config.CHAT_ID_TRACKING})")
        else:
            logging.error(f"Ошибка Telegram (tracking): {response.status_code}, {response.text}")
        response = requests.post(url, params=params_her, timeout=10)
        if response.status_code == 200:
            logging.info(f"Сообщение успешно отправлено в Telegram (her, chat_id={Config.CHAT_ID_HER})")
        else:
            logging.error(f"Ошибка Telegram (her): {response.status_code}, {response.text}")
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")

# Основная работа
def job(state):
    try:
        logging.info("Запуск проверки постов (job)")
        has_new_post, media_url, media_type, post_text = check_new_post(state)
        if has_new_post:
            logging.info("Обработка нового поста")
            if media_url:
                caption = analyzer.get_image_caption(media_url) if media_type == "photo" else None
                message = get_compliment(post_text, caption, media_type, state)
            else:
                message = get_compliment(post_text, None, media_type, state) if post_text else no_photo_message
            send_telegram_message(message)
    except Exception as e:
        logging.error(f"Ошибка в функции job: {e}")
        save_state(state)

# Планирование отправки комплиментов для "equipment_and_studio"
def schedule_equipment_and_studio(state):
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    random_day = random.choice(days)
    random_time = get_random_time()
    getattr(schedule.every(), random_day).at(random_time).do(lambda: send_telegram_message(
        get_unique_compliment(equipment_and_studio_compliments, "equipment_and_studio_compliments_used", state)))
    logging.info(f"Запланирована отправка комплимента equipment_and_studio на {random_day} в {random_time}")

# Запуск планировщика
def run_scheduler(state):
    logging.info("Запуск планировщика...")
    schedule.every(1).minutes.do(lambda: job(state))
    random_time_weekly = get_random_time()
    schedule.every().monday.at(random_time_weekly).do(lambda: send_telegram_message(
        get_unique_compliment(weekly_compliments, "weekly_compliments_used", state)))
    logging.info(f"Запланирована отправка комплимента weekly на понедельник в {random_time_weekly}")
    random_time_client = get_random_time()
    schedule.every().friday.at(random_time_client).do(lambda: send_telegram_message(
        get_unique_compliment(client_interactions_compliments, "client_interactions_compliments_used", state)))
    logging.info(f"Запланирована отправка комплимента client_interactions на пятницу в {random_time_client}")
    random_time_ideas = get_random_time()
    schedule.every().wednesday.at(random_time_ideas).do(lambda: send_telegram_message(
        get_unique_compliment(tattoo_ideas_compliments, "tattoo_ideas_compliments_used", state)))
    logging.info(f"Запланирована отправка комплимента tattoo_ideas на среду в {random_time_ideas}")
    schedule_equipment_and_studio(state)
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка в планировщике: {e}")

if __name__ == "__main__":
    logging.info("Запуск бота... Python версия: " + sys.version)
    logging.info("Текущий каталог: " + os.getcwd())
    logging.info("Доступные файлы: " + str(os.listdir('.')))
    state = load_state()
    logging.info("Состояние загружено успешно")
    job(state)  # Выполняем проверку один раз и завершаем
