import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, MASTER_CLASSES
from database import Database
from keyboards import get_main_keyboard, get_registration_keyboard, create_master_classes_keyboard

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

# Состояния
class UserStates(StatesGroup):
    waiting_phone = State()
    waiting_vote = State()

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    if await db.is_user_registered(user_id):
        # Пользователь уже зарегистрирован
        await message.answer(
            "🎉 С возвращением! Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    else:
        # Нужна регистрация
        await message.answer(
            "👋 Добро пожаловать в систему записи на мастер-классы!\n\n"
            "Для участия необходимо зарегистрироваться.\n"
            "Пожалуйста, поделитесь своим номером телефона:",
            reply_markup=get_registration_keyboard()
        )
        await state.set_state(UserStates.waiting_phone)

@dp.message(UserStates.waiting_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка номера телефона"""
    contact = message.contact
    user = message.from_user
    
    # Регистрируем пользователя
    await db.register_user(
        telegram_id=user.id,
        username=user.username,
        full_name=f"{user.first_name} {user.last_name or ''}",
        phone=contact.phone_number
    )
    
    await message.answer(
        f"✅ Регистрация завершена!\n"
        f"Добро пожаловать, {user.first_name}!",
        reply_markup=get_main_keyboard()
    )
    
    await show_master_classes(message, state)

@dp.message(F.text == "📱 Отправить номер телефона")
async def request_phone(message: Message, state: FSMContext):
    """Запрос номера телефона"""
    await message.answer(
        "Пожалуйста, нажмите кнопку ниже чтобы поделиться номером телефона:",
        reply_markup=get_registration_keyboard()
    )
    await state.set_state(UserStates.waiting_phone)

@dp.message(F.text == "🎯 Выбрать мастер-класс")
async def show_master_classes(message: Message, state: FSMContext):
    """Показывает список мастер-классов"""
    user_id = message.from_user.id
    
    # Проверяем регистрацию
    if not await db.is_user_registered(user_id):
        await message.answer("Сначала нужно зарегистрироваться!", reply_markup=get_registration_keyboard())
        return
    
    # Проверяем, не голосовал ли уже пользователь
    if await db.has_user_voted(user_id):
        vote_info = await db.get_user_vote(user_id)
        if vote_info:
            mc_name, voted_at = vote_info
            await message.answer(
                f"❌ Вы уже записаны на мастер-класс!\n\n"
                f"🎯 Ваш выбор: {mc_name}\n"
                f"📅 Запись создана: {voted_at}\n\n"
                f"Один пользователь может записаться только на один мастер-класс.",
                reply_markup=get_main_keyboard()
            )
        return
    
    keyboard = await create_master_classes_keyboard()
    
    await message.answer(
        "🎯 <b>Выберите мастер-класс:</b>\n\n"
        "✅ - есть свободные места\n"
        "❌ - мест нет\n\n"
        "<i>Нажмите на кнопку с названием мастер-класса для записи</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_vote)

@dp.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора мастер-класса"""
    master_class_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Получаем информацию о мастер-классе
    master_classes = await db.get_master_classes()
    mc_info = next((mc for mc in master_classes if mc[0] == master_class_id), None)
    
    if not mc_info:
        await callback.answer("Ошибка: мастер-класс не найден", show_alert=True)
        return
    
    mc_id, mc_name, max_slots, used_slots = mc_info
    
    # Пытаемся записать пользователя
    success = await db.try_reserve_slot(master_class_id, user_id)
    
    if success:
        # Успешная запись
        await callback.message.edit_text(
            f"🎉 <b>Поздравляем с успешной записью!</b>\n\n"
            f"🏆 <b>Мастер-класс:</b> {mc_name}\n"
            f"📅 <b>Место забронировано:</b> ✅\n"
            f"👥 <b>Записано:</b> {used_slots + 1}/{max_slots} человек\n\n"
            f"Ждем вас на мастер-классе!",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        # Не удалось записаться
        await callback.answer(
            "❌ Не удалось записаться. Возможно, места уже закончились или вы уже записаны на другой мастер-класс.",
            show_alert=True
        )
    
    await state.clear()

@dp.callback_query(F.data == "refresh")
async def refresh_list(callback: CallbackQuery):
    """Обновление списка мастер-классов"""
    keyboard = await create_master_classes_keyboard()
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer("✅ Список обновлен")
    except:
        await callback.answer("✅ Список актуален")

@dp.callback_query(F.data == "full")
async def handle_full(callback: CallbackQuery):
    """Обработка нажатия на заполненный мастер-класс"""
    await callback.answer("❌ На этот мастер-класс уже нет свободных мест", show_alert=True)

@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показывает статистику записей"""
    stats = await db.get_statistics()
    total_users = await db.get_total_users()
    
    if not stats:
        await message.answer("Статистика временно недоступна")
        return
    
    text = "📊 <b>Статистика записей на мастер-классы:</b>\n\n"
    
    for name, used_slots, max_slots, is_full in stats:
        percentage = (used_slots / max_slots) * 100
        bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
        
        text += f"<b>{name}</b>\n"
        text += f"{bar} {used_slots}/{max_slots} ({percentage:.1f}%)\n\n"
    
    text += f"👥 <b>Всего зарегистрированных пользователей:</b> {total_users}"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "ℹ️ Моя запись")
async def show_my_vote(message: Message):
    """Показывает информацию о записи пользователя"""
    user_id = message.from_user.id
    
    if not await db.is_user_registered(user_id):
        await message.answer("Сначала нужно зарегистрироваться!", reply_markup=get_registration_keyboard())
        return
    
    vote_info = await db.get_user_vote(user_id)
    
    if vote_info:
        mc_name, voted_at = vote_info
        await message.answer(
            f"📋 <b>Ваша запись:</b>\n\n"
            f"🎯 <b>Мастер-класс:</b> {mc_name}\n"
            f"📅 <b>Время записи:</b> {voted_at}\n\n"
            f"Ждем вас на мероприятии! 🎉",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Вы еще не записаны ни на один мастер-класс.\n\n"
            "Нажмите «🎯 Выбрать мастер-класс» чтобы сделать запись."
        )

@dp.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показывает справку"""
    help_text = (
        "🆘 <b>Помощь по боту:</b>\n\n"
        "🎯 <b>Выбрать мастер-класс</b> - записаться на один из доступных мастер-классов\n"
        "📊 <b>Статистика</b> - посмотреть текущую статистику записей\n"
        "ℹ️ <b>Моя запись</b> - информация о вашей текущей записи\n\n"
        "<b>Правила:</b>\n"
        "• Один пользователь может записаться только на ОДИН мастер-класс\n"
        "• Отмена записи невозможна\n"
        "• Количество мест ограничено\n\n"
        "По всем вопросам обращайтесь к организаторам."
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(F.text == "↩️ Назад")
async def back_to_main(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

# Запуск бота
async def main():
    logger.info("Starting bot...")
    
    # Инициализация базы данных
    await db.init_db()
    logger.info("Database initialized")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
