import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///votes.db')

# Конфигурация мастер-классов
MASTER_CLASSES = {
    1: {"name": "Настольный теннис", "max_slots": 10, "used_slots": 0},
    2: {"name": "Квиз (Григорьев)", "max_slots": 40, "used_slots": 0},
    3: {"name": "Не игры (Кристина Астапенкова)", "max_slots": 40, "used_slots": 0},
    4: {"name": "Бункер (Бородина Аня)", "max_slots": 15, "used_slots": 0},
    5: {"name": "Нарды (Эльвира)", "max_slots": 12, "used_slots": 0},
    6: {"name": "Мафия (Кимн)", "max_slots": 15, "used_slots": 0},
    7: {"name": "Эстафета (Паша Шелкович)", "max_slots": 30, "used_slots": 0},
    8: {"name": "Иманджинариум", "max_slots": 7, "used_slots": 0},
}
