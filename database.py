import aiosqlite
from config import ACTIVITIES

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
            
            # Таблица активностей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS activities (
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
                    activity_id INTEGER NOT NULL,
                    voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (activity_id) REFERENCES activities (id),
                    UNIQUE(user_id, activity_id)
                )
            ''')
            
            await db.commit()
        
        # Синхронизируем с config.py
        await self.update_activities()
    
    async def update_activities(self):
        """Обновляет список активностей в базе данных"""
        async with aiosqlite.connect(self.db_path) as db:
            for activity_id, activity_data in ACTIVITIES.items():
                # Проверяем, существует ли уже эта активность
                cursor = await db.execute(
                    'SELECT 1 FROM activities WHERE id = ?', 
                    (activity_id,)
                )
                exists = await cursor.fetchone()
                
                if exists:
                    # Обновляем существующую
                    await db.execute('''
                        UPDATE activities 
                        SET name = ?, max_slots = ?
                        WHERE id = ?
                    ''', (activity_data['name'], activity_data['max_slots'], activity_id))
                else:
                    # Добавляем новую
                    await db.execute('''
                        INSERT INTO activities (id, name, max_slots)
                        VALUES (?, ?, ?)
                    ''', (activity_id, activity_data['name'], activity_data['max_slots']))
            
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
                SELECT a.name, v.voted_at 
                FROM votes v
                JOIN activities a ON v.activity_id = a.id
                WHERE v.user_id = ?
            ''', (telegram_id,))
            return await cursor.fetchone()
    
    async def get_activities(self):
        """Получает список всех активностей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, name, max_slots, used_slots 
                FROM activities 
                ORDER BY id
            ''')
            return await cursor.fetchall()
    
    async def try_reserve_slot(self, activity_id: int, user_id: int) -> bool:
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
                    UPDATE activities 
                    SET used_slots = used_slots + 1 
                    WHERE id = ? AND used_slots < max_slots
                    RETURNING id
                ''', (activity_id,))
                
                if await cursor.fetchone():
                    # Если место занято, записываем голос
                    await db.execute(
                        'INSERT INTO votes (user_id, activity_id) VALUES (?, ?)',
                        (user_id, activity_id)
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
        """Получает статистику по всем активностям"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT name, used_slots, max_slots,
                       CASE WHEN used_slots >= max_slots THEN 1 ELSE 0 END as is_full
                FROM activities 
                ORDER BY id
            ''')
            return await cursor.fetchall()
    
    async def get_total_users(self):
        """Получает общее количество пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_all_users(self):
        """Получает всех зарегистрированных пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT telegram_id, username, full_name, phone, registered_at 
                FROM users 
                ORDER BY registered_at
            ''')
            return await cursor.fetchall()

    async def get_votes_details(self):
        """Получает детальную информацию о всех записях"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 
                    u.telegram_id,
                    u.username,
                    u.full_name,
                    u.phone,
                    a.name as activity_name,
                    v.voted_at
                FROM votes v
                JOIN users u ON v.user_id = u.telegram_id
                JOIN activities a ON v.activity_id = a.id
                ORDER BY v.voted_at
            ''')
            return await cursor.fetchall()

    async def get_activity_participants(self, activity_id: int):
        """Получает участников конкретной активности"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 
                    u.telegram_id,
                    u.username,
                    u.full_name,
                    u.phone,
                    v.voted_at
                FROM votes v
                JOIN users u ON v.user_id = u.telegram_id
                WHERE v.activity_id = ?
                ORDER BY v.voted_at
            ''', (activity_id,))
            return await cursor.fetchall()
