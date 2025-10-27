import sqlite3
import aiosqlite
from config import MASTER_CLASSES

class Database:
    def __init__(self, db_path='votes.db'):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    phone TEXT,
                    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица мастер-классов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS master_classes (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    max_slots INTEGER NOT NULL,
                    used_slots INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица голосов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    master_class_id INTEGER NOT NULL,
                    voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (master_class_id) REFERENCES master_classes (id),
                    UNIQUE(user_id, master_class_id)
                )
            ''')
            
            # Заполняем мастер-классы
            for mc_id, mc_data in MASTER_CLASSES.items():
                await db.execute('''
                    INSERT OR REPLACE INTO master_classes (id, name, max_slots, used_slots)
                    VALUES (?, ?, ?, ?)
                ''', (mc_id, mc_data['name'], mc_data['max_slots'], mc_data['used_slots']))
            
            await db.commit()
    
    async def register_user(self, telegram_id: int, username: str, full_name: str, phone: str = None):
        """Регистрация пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO users (telegram_id, username, full_name, phone)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, full_name, phone))
            await db.commit()
    
    async def is_user_registered(self, telegram_id: int) -> bool:
        """Проверка регистрации пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT 1 FROM users WHERE telegram_id = ?', 
                (telegram_id,)
            )
            return await cursor.fetchone() is not None
    
    async def has_user_voted(self, telegram_id: int) -> bool:
        """Проверяет, голосовал ли уже пользователь"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT 1 FROM votes WHERE user_id = ?', 
                (telegram_id,)
            )
            return await cursor.fetchone() is not None
    
    async def get_user_vote(self, telegram_id: int):
        """Получает информацию о голосе пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT mc.name, v.voted_at 
                FROM votes v
                JOIN master_classes mc ON v.master_class_id = mc.id
                WHERE v.user_id = ?
            ''', (telegram_id,))
            return await cursor.fetchone()
    
    async def get_master_classes(self):
        """Получает список всех мастер-классов"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, name, max_slots, used_slots 
                FROM master_classes 
                ORDER BY id
            ''')
            return await cursor.fetchall()
    
    async def try_reserve_slot(self, master_class_id: int, user_id: int) -> bool:
        """Пытается забронировать место (с транзакцией)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Начинаем транзакцию
            await db.execute('BEGIN TRANSACTION')
            
            try:
                # Проверяем, не голосовал ли уже пользователь
                cursor = await db.execute(
                    'SELECT 1 FROM votes WHERE user_id = ?', 
                    (user_id,)
                )
                if await cursor.fetchone():
                    await db.execute('ROLLBACK')
                    return False
                
                # Пытаемся занять место
                cursor = await db.execute('''
                    UPDATE master_classes 
                    SET used_slots = used_slots + 1 
                    WHERE id = ? AND used_slots < max_slots
                    RETURNING id
                ''', (master_class_id,))
                
                if await cursor.fetchone():
                    # Если место занято, записываем голос
                    await db.execute(
                        'INSERT INTO votes (user_id, master_class_id) VALUES (?, ?)',
                        (user_id, master_class_id)
                    )
                    await db.execute('COMMIT')
                    return True
                else:
                    await db.execute('ROLLBACK')
                    return False
                    
            except Exception as e:
                await db.execute('ROLLBACK')
                print(f"Error in transaction: {e}")
                return False
    
    async def get_statistics(self):
        """Получает статистику по всем мастер-классам"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT name, used_slots, max_slots,
                       CASE WHEN used_slots >= max_slots THEN 1 ELSE 0 END as is_full
                FROM master_classes 
                ORDER BY id
            ''')
            return await cursor.fetchall()
    
    async def get_total_users(self):
        """Получает общее количество пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            result = await cursor.fetchone()
            return result[0] if result else 0
