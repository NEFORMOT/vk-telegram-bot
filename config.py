import os

class Config:
    VK_TOKEN = os.getenv("VK_TOKEN")  # Токен VK, должен быть в Secrets
    GROUP_ID = os.getenv("GROUP_ID")  # Новый ID группы (замени на свой)
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Токен Telegram, должен быть в Secrets
    CHAT_ID_TRACKING = os.getenv("CHAT_ID")  # Твой CHAT_ID для отслеживания
    CHAT_ID_HER = os.getenv("CHAT_ID_HER")  # Её CHAT_ID для комплиментов
    HF_TOKEN = os.getenv("HF_TOKEN")  # Токен Hugging Face, должен быть в Secrets
    YNDX_API_KEY = os.getenv("YNDX_API_KEY")  # Ключ Yandex, должен быть в Secrets
    STATE_FILE = "bot_state.json"  # Это можно оставить