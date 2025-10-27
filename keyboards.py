from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database

def get_main_keyboard():
    """Основная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Выбрать активность")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="ℹ️ Моя запись")],
            [KeyboardButton(text="🆘 Помощь")]
        ],
        resize_keyboard=True
    )

def get_registration_keyboard():
    """Клавиатура для регистрации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True
    )

async def create_activities_keyboard():
    """Создает инлайн-клавиатуру с активностями"""
    db = Database()
    activities = await db.get_activities()
    
    builder = InlineKeyboardBuilder()
    
    for activity_id, name, max_slots, used_slots in activities:
        is_full = used_slots >= max_slots
        emoji = "❌" if is_full else "✅"
        slots_text = f"({used_slots}/{max_slots})"
        
        button_text = f"{emoji} {name} {slots_text}"
        callback_data = f"vote_{activity_id}" if not is_full else "full"
        
        if not is_full:
            builder.add(InlineKeyboardButton(
                text=button_text,
                callback_data=callback_data
            ))
        else:
            builder.add(InlineKeyboardButton(
                text=button_text,
                callback_data="full"
            ))
    
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить список",
        callback_data="refresh"
    ))
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()
