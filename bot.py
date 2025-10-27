import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_IDS
from database import Database
from keyboards import get_main_keyboard, get_registration_keyboard, create_activities_keyboard

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Проверка токена
if not BOT_TOKEN or BOT_TOKEN == "тут_твой_токен_от_BotFather":
    logger.error("❌ BOT_TOKEN не настроен! Проверь файл .env")
    sys.exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
db = Database()

# Состояния
class UserStates(StatesGroup):
    waiting_phone = State()
    waiting_vote = State()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    
    if await db.is_user_registered(user_id):
        await message.answer("🎉 С возвращением! Выберите действие:", reply_markup=get_main_keyboard())
        await state.clear()
    else:
        await message.answer(
            "👋 Добро пожаловать в систему записи на активности!\n\n"
            "Для участия необходимо зарегистрироваться.\n"
            "Пожалуйста, поделитесь своим номером телефона:",
            reply_markup=get_registration_keyboard()
        )
        await state.set_state(UserStates.waiting_phone)

@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    """Показывает ID пользователя"""
    user_id = message.from_user.id
    await message.answer(f"Твой ID: `{user_id}`\n\nДобавь этот ID в ADMIN_IDS в config.py", parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    keyboard = [
        [KeyboardButton(text="👥 Все пользователи")],
        [KeyboardButton(text="📋 Списки по активностям"), KeyboardButton(text="📊 Полная статистика")],
        [KeyboardButton(text="📁 Экспорт в CSV"), KeyboardButton(text="🔄 Обновить данные")],
        [KeyboardButton(text="↩️ Главное меню")]
    ]
    
    admin_keyboard = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    total_users = await db.get_total_users()
    stats = await db.get_statistics()
    
    text = "🛠️ <b>Админ-панель</b>\n\n"
    text += f"👥 <b>Всего пользователей:</b> {total_users}\n\n"
    
    for name, used_slots, max_slots, is_full in stats:
        text += f"• {name}: {used_slots}/{max_slots}\n"
    
    await message.answer(text, reply_markup=admin_keyboard, parse_mode="HTML")

@dp.message(Command("update_activities"))
async def cmd_update_activities(message: Message):
    """Обновляет список активностей в базе данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    try:
        await db.update_activities()
        await message.answer("✅ Список активностей обновлен в базе данных!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обновлении: {e}")

@dp.message(F.text == "👥 Все пользователи")
async def show_all_users(message: Message):
    """Показывает всех зарегистрированных пользователей"""
    if not is_admin(message.from_user.id):
        return
    
    users = await db.get_all_users()
    
    if not users:
        await message.answer("📭 Нет зарегистрированных пользователей")
        return
    
    text = "👥 <b>Все зарегистрированные пользователи:</b>\n\n"
    
    for i, (user_id, username, full_name, phone, registered_at) in enumerate(users, 1):
        username_display = f"@{username}" if username else "нет username"
        phone_display = phone if phone else "не указан"
        
        text += f"<b>{i}.</b> {full_name}\n"
        text += f"   ID: {user_id}\n"
        text += f"   Username: {username_display}\n"
        text += f"   Телефон: {phone_display}\n"
        text += f"   Дата: {registered_at}\n\n"
        
        # Разбиваем сообщение если слишком длинное
        if len(text) > 3000:
            await message.answer(text, parse_mode="HTML")
            text = ""
    
    if text:
        await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📋 Списки по активностям")
async def show_activity_lists(message: Message):
    """Показывает списки по активностям"""
    if not is_admin(message.from_user.id):
        return
    
    # Создаем клавиатуру с активностями
    keyboard = await create_activities_keyboard()
    
    await message.answer(
        "🎯 <b>Выберите активность для просмотра списка участников:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора активности"""
    activity_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Если это админ и он смотрит списки
    if is_admin(user_id) and callback.message.text and "список участников" in callback.message.text:
        # Получаем информацию о активности
        activities = await db.get_activities()
        activity_info = next((a for a in activities if a[0] == activity_id), None)
        
        if not activity_info:
            await callback.answer("Ошибка: активность не найдена")
            return
        
        act_id, act_name, max_slots, used_slots = activity_info
        
        # Получаем участников
        participants = await db.get_activity_participants(activity_id)
        
        text = f"📋 <b>Участники активности:</b> {act_name}\n"
        text += f"👥 <b>Записано:</b> {len(participants)}/{max_slots}\n\n"
        
        if not participants:
            text += "📭 Нет записавшихся участников"
        else:
            for i, (user_id, username, full_name, phone, voted_at) in enumerate(participants, 1):
                username_display = f"@{username}" if username else "нет username"
                text += f"<b>{i}.</b> {full_name}\n"
                text += f"   ID: {user_id} | {username_display}\n"
                if phone:
                    text += f"   📞 {phone}\n"
                text += f"   🕐 {voted_at}\n\n"
        
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()
        return
    
    # Обычное голосование для пользователей
    success = await db.try_reserve_slot(activity_id, user_id)
    
    if success:
        activities = await db.get_activities()
        activity_info = next((a for a in activities if a[0] == activity_id), None)
        
        if activity_info:
            act_id, act_name, max_slots, used_slots = activity_info
            await callback.message.edit_text(
                f"🎉 <b>Поздравляем с успешной записью!</b>\n\n"
                f"🏆 <b>Активность:</b> {act_name}\n"
                f"📅 <b>Место забронировано:</b> ✅\n"
                f"👥 <b>Записано:</b> {used_slots + 1}/{max_slots} человек\n\n"
                f"Ждем вас на активности!",
                parse_mode="HTML"
            )
        await callback.answer()
    else:
        await callback.answer(
            "❌ Не удалось записаться. Возможно, места уже закончились или вы уже записаны на другую активность.",
            show_alert=True
        )
    
    await state.clear()

@dp.message(F.text == "📊 Полная статистика")
async def show_full_stats(message: Message):
    """Показывает полную статистику"""
    if not is_admin(message.from_user.id):
        return
    
    stats = await db.get_statistics()
    total_users = await db.get_total_users()
    votes_details = await db.get_votes_details()
    
    text = "📊 <b>Полная статистика:</b>\n\n"
    text += f"👥 <b>Всего пользователей:</b> {total_users}\n"
    text += f"🎯 <b>Всего записей на активности:</b> {len(votes_details)}\n\n"
    
    for name, used_slots, max_slots, is_full in stats:
        percentage = (used_slots / max_slots) * 100 if max_slots > 0 else 0
        bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
        
        text += f"<b>{name}</b>\n"
        text += f"{bar} {used_slots}/{max_slots} ({percentage:.1f}%)\n\n"
    
    # Список всех записей
    text += "<b>Все записи:</b>\n"
    for i, (user_id, username, full_name, phone, activity_name, voted_at) in enumerate(votes_details, 1):
        username_display = f"@{username}" if username else "нет username"
        text += f"{i}. {full_name} → {activity_name}\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📁 Экспорт в CSV")
async def export_to_csv(message: Message):
    """Экспортирует данные в CSV формат"""
    if not is_admin(message.from_user.id):
        return
    
    import csv
    import io
    from datetime import datetime
    
    # Получаем данные
    votes_details = await db.get_votes_details()
    
    if not votes_details:
        await message.answer("📭 Нет данных для экспорта")
        return
    
    # Создаем CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['ID', 'Username', 'ФИО', 'Телефон', 'Активность', 'Дата записи'])
    
    # Данные
    for user_id, username, full_name, phone, activity_name, voted_at in votes_details:
        writer.writerow([user_id, username or '', full_name, phone or '', activity_name, voted_at])
    
    # Создаем файл
    csv_data = output.getvalue()
    output.close()
    
    # Отправляем файл
    file_name = f"activities_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    await message.answer_document(
        types.BufferedInputFile(
            csv_data.encode('utf-8'),
            filename=file_name
        ),
        caption="📁 Экспорт данных завершен"
    )

@dp.message(F.text == "🔄 Обновить данные")
async def refresh_admin_data(message: Message):
    """Обновляет данные в админ-панели"""
    if not is_admin(message.from_user.id):
        return
    
    await cmd_admin(message)
    await message.answer("✅ Данные обновлены")

@dp.message(F.text == "↩️ Главное меню")
async def back_to_main_from_admin(message: Message):
    """Возврат в главное меню из админки"""
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(UserStates.waiting_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка номера телефона"""
    contact = message.contact
    user = message.from_user
    
    await db.register_user(
        telegram_id=user.id,
        username=user.username,
        full_name=f"{user.first_name} {user.last_name or ''}",
        phone=contact.phone_number
    )
    
    await message.answer(
        f"✅ Регистрация завершена!\nДобро пожаловать, {user.first_name}!",
        reply_markup=get_main_keyboard()
    )
    await show_activities(message, state)

@dp.message(F.text == "📱 Отправить номер телефона")
async def request_phone(message: Message, state: FSMContext):
    """Запрос номера телефона"""
    await message.answer(
        "Пожалуйста, нажмите кнопку ниже чтобы поделиться номером телефона:",
        reply_markup=get_registration_keyboard()
    )
    await state.set_state(UserStates.waiting_phone)

@dp.message(F.text == "🎯 Выбрать активность")
async def show_activities(message: Message, state: FSMContext):
    """Показывает список активностей"""
    user_id = message.from_user.id
    
    # Проверяем регистрацию
    if not await db.is_user_registered(user_id):
        await message.answer("Сначала нужно зарегистрироваться!", reply_markup=get_registration_keyboard())
        return
    
    # Проверяем, не голосовал ли уже пользователь
    if await db.has_user_voted(user_id):
        vote_info = await db.get_user_vote(user_id)
        if vote_info:
            activity_name, voted_at = vote_info
            await message.answer(
                f"❌ Вы уже записаны на активность!\n\n"
                f"🎯 Ваш выбор: {activity_name}\n"
                f"📅 Запись создана: {voted_at}\n\n"
                f"Один пользователь может записаться только на одну активность.",
                reply_markup=get_main_keyboard()
            )
        return
    
    keyboard = await create_activities_keyboard()
    
    await message.answer(
        "🎯 <b>Выберите активность:</b>\n\n"
        "✅ - есть свободные места\n"
        "❌ - мест нет\n\n"
        "<i>Нажмите на кнопку с названием активности для записи</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_vote)

@dp.callback_query(F.data == "refresh")
async def refresh_list(callback: CallbackQuery):
    """Обновление списка активностей"""
    keyboard = await create_activities_keyboard()
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer("✅ Список обновлен")
    except:
        await callback.answer("✅ Список актуален")

@dp.callback_query(F.data == "full")
async def handle_full(callback: CallbackQuery):
    """Обработка нажатия на заполненную активность"""
    await callback.answer("❌ На эту активность уже нет свободных мест", show_alert=True)

@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показывает статистику записей"""
    stats = await db.get_statistics()
    total_users = await db.get_total_users()
    
    if not stats:
        await message.answer("Статистика временно недоступна")
        return
    
    text = "📊 <b>Статистика записей на активности:</b>\n\n"
    
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
        activity_name, voted_at = vote_info
        await message.answer(
            f"📋 <b>Ваша запись:</b>\n\n"
            f"🎯 <b>Активность:</b> {activity_name}\n"
            f"📅 <b>Время записи:</b> {voted_at}\n\n"
            f"Ждем вас на мероприятии! 🎉",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Вы еще не записаны ни на одну активность.\n\n"
            "Нажмите «🎯 Выбрать активность» чтобы сделать запись."
        )

@dp.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показывает справку"""
    help_text = (
        "🆘 <b>Помощь по боту:</b>\n\n"
        "🎯 <b>Выбрать активность</b> - записаться на одну из доступных активностей\n"
        "📊 <b>Статистика</b> - посмотреть текущую статистику записей\n"
        "ℹ️ <b>Моя запись</b> - информация о вашей текущей записи\n\n"
        "<b>Правила:</b>\n"
        "• Один пользователь может записаться только на ОДНУ активность\n"
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
