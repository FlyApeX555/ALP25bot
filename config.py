import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///votes.db')

# ID администраторов (замени на свои Telegram ID)
ADMIN_IDS = [801181185]  # ЗАМЕНИ ЭТОТ ID НА СВОЙ РЕАЛЬНЫЙ!

# Конфигурация активностей
ACTIVITIES = {
    1: {"name": "Настольный теннис", "max_slots": 10},
    2: {"name": "Квиз", "max_slots": 40},
    3: {"name": "Не игры", "max_slots": 40},
    4: {"name": "Бункер", "max_slots": 15},
    5: {"name": "Нарды", "max_slots": 12},
    6: {"name": "Мафия", "max_slots": 15},
    7: {"name": "Эстафета", "max_slots": 30},
    8: {"name": "Иманджинариум", "max_slots": 7},
}
