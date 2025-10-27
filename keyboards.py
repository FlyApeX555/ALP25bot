from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard():
    """Основная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Выбрать мастер-класс")],
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

async def create_master_classes_keyboard():
    """Создает инлайн-клавиатуру с мастер-классами"""
    from database import Database
    
    db = Database()
    classes = await db.get_master_classes()
    
    builder = InlineKeyboardBuilder()
    
    for mc_id, name, max_slots, used_slots in classes:
        is_full = used_slots >= max_slots
        emoji = "❌" if is_full else "✅"
        slots_text = f"({used_slots}/{max_slots})"
        
        button_text = f"{emoji} {name} {slots_text}"
        callback_data = f"vote_{mc_id}" if not is_full else "full"
        
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
