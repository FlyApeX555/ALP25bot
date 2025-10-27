import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///votes.db')

# Конфигурация мастер-классов
MASTER_CLASSES = {
    1: {"name": "Настольный теннис", "max_slots": 10},
    2: {"name": "Квиз (Григорьев)", "max_slots": 40},
    3: {"name": "Не игры (Кристина Астапенкова)", "max_slots": 40},
    4: {"name": "Бункер (Бородина Аня)", "max_slots": 15},
    5: {"name": "Нарды (Эльвира)", "max_slots": 12},
    6: {"name": "Мафия (Кимн)", "max_slots": 15},
    7: {"name": "Эстафета (Паша Шелкович)", "max_slots": 30},
    8: {"name": "Иманджинариум", "max_slots": 7},
}
