import sqlite3
from typing import Optional, List, Dict
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_name: str = "travel_wallet.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Инициализация базы данных с необходимыми таблицами"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица путешествий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                trip_name TEXT NOT NULL,
                country_from TEXT NOT NULL,
                country_to TEXT NOT NULL,
                currency_from TEXT NOT NULL,
                currency_to TEXT NOT NULL,
                exchange_rate REAL NOT NULL,
                initial_amount_from REAL NOT NULL,
                balance_from REAL NOT NULL,
                balance_to REAL NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица расходов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                amount_to REAL NOT NULL,
                amount_from REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: str = None):
        """Добавить нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            conn.commit()
        finally:
            conn.close()

    def create_trip(self, user_id: int, trip_name: str, country_from: str, country_to: str,
                    currency_from: str, currency_to: str, exchange_rate: float,
                    initial_amount_from: float, balance_to: float) -> int:
        """Создать новое путешествие"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Деактивировать все другие путешествия пользователя
            cursor.execute(
                "UPDATE trips SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            # Создать новое путешествие
            cursor.execute("""
                INSERT INTO trips (user_id, trip_name, country_from, country_to, 
                                   currency_from, currency_to, exchange_rate, 
                                   initial_amount_from, balance_from, balance_to, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (user_id, trip_name, country_from, country_to, currency_from, 
                  currency_to, exchange_rate, initial_amount_from, initial_amount_from, balance_to))
            
            trip_id = cursor.lastrowid
            conn.commit()
            return trip_id
        finally:
            conn.close()

    def get_active_trip(self, user_id: int) -> Optional[Dict]:
        """Получить активное путешествие пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT trip_id, trip_name, country_from, country_to, 
                       currency_from, currency_to, exchange_rate, 
                       initial_amount_from, balance_from, balance_to
                FROM trips 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'trip_id': row[0],
                    'trip_name': row[1],
                    'country_from': row[2],
                    'country_to': row[3],
                    'currency_from': row[4],
                    'currency_to': row[5],
                    'exchange_rate': row[6],
                    'initial_amount_from': row[7],
                    'balance_from': row[8],
                    'balance_to': row[9]
                }
            return None
        finally:
            conn.close()

    def get_all_trips(self, user_id: int) -> List[Dict]:
        """Получить все путешествия пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT trip_id, trip_name, country_from, country_to, 
                       currency_from, currency_to, exchange_rate, 
                       balance_from, balance_to, is_active
                FROM trips 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            trips = []
            for row in cursor.fetchall():
                trips.append({
                    'trip_id': row[0],
                    'trip_name': row[1],
                    'country_from': row[2],
                    'country_to': row[3],
                    'currency_from': row[4],
                    'currency_to': row[5],
                    'exchange_rate': row[6],
                    'balance_from': row[7],
                    'balance_to': row[8],
                    'is_active': row[9]
                })
            return trips
        finally:
            conn.close()

    def switch_active_trip(self, user_id: int, trip_id: int) -> bool:
        """Переключить активное путешествие"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Проверить, что путешествие принадлежит пользователю
            cursor.execute(
                "SELECT trip_id FROM trips WHERE trip_id = ? AND user_id = ?",
                (trip_id, user_id)
            )
            if not cursor.fetchone():
                return False
            
            # Деактивировать все путешествия
            cursor.execute(
                "UPDATE trips SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            # Активировать выбранное
            cursor.execute(
                "UPDATE trips SET is_active = 1 WHERE trip_id = ?",
                (trip_id,)
            )
            
            conn.commit()
            return True
        finally:
            conn.close()

    def add_expense(self, trip_id: int, amount_to: float, amount_from: float, description: str = ""):
        """Добавить расход"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Добавить запись о расходе
            cursor.execute("""
                INSERT INTO expenses (trip_id, amount_to, amount_from, description)
                VALUES (?, ?, ?, ?)
            """, (trip_id, amount_to, amount_from, description))
            
            # Обновить баланс путешествия
            cursor.execute("""
                UPDATE trips 
                SET balance_from = balance_from - ?, balance_to = balance_to - ?
                WHERE trip_id = ?
            """, (amount_from, amount_to, trip_id))
            
            conn.commit()
        finally:
            conn.close()

    def get_trip_expenses(self, trip_id: int, limit: int = 10) -> List[Dict]:
        """Получить историю расходов путешествия"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT expense_id, amount_to, amount_from, description, created_at
                FROM expenses
                WHERE trip_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (trip_id, limit))
            
            expenses = []
            for row in cursor.fetchall():
                expenses.append({
                    'expense_id': row[0],
                    'amount_to': row[1],
                    'amount_from': row[2],
                    'description': row[3],
                    'created_at': row[4]
                })
            return expenses
        finally:
            conn.close()

    def update_exchange_rate(self, trip_id: int, new_rate: float) -> bool:
        """Обновить курс обмена для путешествия"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Получить текущий баланс в базовой валюте
            cursor.execute(
                "SELECT balance_from FROM trips WHERE trip_id = ?",
                (trip_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
            
            balance_from = row[0]
            
            # Пересчитать баланс в валюте назначения
            new_balance_to = balance_from * new_rate
            
            # Обновить курс и баланс
            cursor.execute("""
                UPDATE trips 
                SET exchange_rate = ?, balance_to = ?
                WHERE trip_id = ?
            """, (new_rate, new_balance_to, trip_id))
            
            conn.commit()
            return True
        finally:
            conn.close()

    def get_trip_statistics(self, trip_id: int) -> Dict:
        """Получить статистику по путешествию"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_expenses,
                    COALESCE(SUM(amount_from), 0) as total_spent_from,
                    COALESCE(SUM(amount_to), 0) as total_spent_to
                FROM expenses
                WHERE trip_id = ?
            """, (trip_id,))
            
            row = cursor.fetchone()
            return {
                'total_expenses': row[0],
                'total_spent_from': row[1],
                'total_spent_to': row[2]
            }
        finally:
            conn.close()

