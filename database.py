
import aiosqlite
import datetime
import json
import logging

class DatabaseManager:
    def __init__(self, db_name="kitobxon_pro.db"):
        self.db_name = db_name

    async def create_tables(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS users 
                (user_id INTEGER PRIMARY KEY, fullname TEXT, quiz_points INTEGER DEFAULT 0, 
                streak INTEGER DEFAULT 0, last_active DATE, clan TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS books 
                (id INTEGER PRIMARY KEY, title TEXT, author TEXT, desc TEXT, questions TEXT, category TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS read_books 
                (id INTEGER PRIMARY KEY, user_id INTEGER, book_name TEXT, date TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS library_files 
                (id INTEGER PRIMARY KEY, title TEXT, file_id TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS tracker 
                (id INTEGER PRIMARY KEY, user_id INTEGER, pages INTEGER, date DATE)''')
            await db.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, content TEXT, file_id TEXT, file_type TEXT)")
            
            # Migration: Add category column if missing
            try:
                await db.execute("ALTER TABLE books ADD COLUMN category TEXT")
            except:
                pass # Column likely exists
            
            await db.commit()

    async def add_user(self, user_id, fullname):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    await db.execute("INSERT INTO users (user_id, fullname, quiz_points, streak, last_active) VALUES (?, ?, 0, 0, ?)", 
                                          (user_id, fullname, datetime.date.today()))
                    await db.commit()

    async def get_user_stats(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
                return await cursor.fetchone()

    async def update_points(self, user_id, points):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("UPDATE users SET quiz_points = quiz_points + ? WHERE user_id=?", (points, user_id))
            await db.commit()

    # --- BOOK & QUIZ METHODS ---
    async def add_book_with_quiz(self, title, author, desc, questions_json, category="General"):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO books (title, author, desc, questions, category) VALUES (?, ?, ?, ?, ?)", 
                                  (title, author, desc, questions_json, category))
            await db.commit()

    async def get_all_books(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT id, title, author FROM books") as cursor:
                return await cursor.fetchall()


    async def get_book_details(self, book_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT * FROM books WHERE id=?", (book_id,)) as cursor:
                return await cursor.fetchone()

    async def get_books_count(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT COUNT(*) FROM books") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    async def search_books(self, query):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT id, title, author, desc FROM books WHERE title LIKE ? OR author LIKE ?", (f'%{query}%', f'%{query}%')) as cursor:
                return await cursor.fetchall()
    
    async def get_recommendations(self, user_id):
        # Intelligent recommendation logic
        async with aiosqlite.connect(self.db_name) as db:
            # 1. Get user's read history
            async with db.execute("SELECT book_name FROM read_books WHERE user_id=?", (user_id,)) as cursor:
                read_books = [row[0] for row in await cursor.fetchall()]
            
            # 2. Analyze categories (Simple heuristic: find category of read books)
            # Since read_books only stores names, we try to match names in 'books' table to get categories.
            favorite_category = None
            if read_books:
                placeholders = ','.join('?' for _ in read_books)
                query = f"SELECT category, COUNT(*) as cnt FROM books WHERE title IN ({placeholders}) GROUP BY category ORDER BY cnt DESC LIMIT 1"
                async with db.execute(query, read_books) as cursor:
                    res = await cursor.fetchone()
                    if res: favorite_category = res[0]
            
            # 3. Recommend
            if favorite_category:
                # Recommend unread books from same category
                placeholders = ','.join('?' for _ in read_books) if read_books else "''"
                query = f"SELECT title, author, desc FROM books WHERE category=? AND title NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT 1"
                params = [favorite_category] + read_books
                async with db.execute(query, params) as cursor:
                    rec = await cursor.fetchone()
                    if rec: return f"🎯 <b>Siz uchun maxsus:</b>\n\n📘 {rec[0]}\n✍️ {rec[1]}\n\n{rec[2]}"

            # Fallback: Random book not read
            placeholders = ','.join('?' for _ in read_books) if read_books else "''"
            query = f"SELECT title, author, desc FROM books WHERE title NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT 1"
            async with db.execute(query, read_books) as cursor:
                rec = await cursor.fetchone()
                if rec: return f"🎲 <b>Tasodifiy tavsiya:</b>\n\n📘 {rec[0]}\n✍️ {rec[1]}\n\n{rec[2]}"
            
            return "📭 Hozircha barcha kitoblarni o'qib bo'ldingiz!"

    async def force_migrate(self, library_data):
        print("⏳ Force aligning database with LIBRARY_DATA...")
        async with aiosqlite.connect(self.db_name) as db:
            # 1. Clear books table to prevent duplicates/stale data
            await db.execute("DELETE FROM books")
            # 2. Reset AutoIncrement (optional but cleaner)
            try:
                await db.execute("DELETE FROM sqlite_sequence WHERE name='books'")
            except Exception:
                pass # Table might not exist yet if no autoincrement usage
            
            # 3. Insert all books
            count = 0
            for _, data in library_data.items():
                try:
                    q_json = json.dumps(data['quiz'], ensure_ascii=False)
                    cat = data.get('category', 'Badiiy')
                    await db.execute("INSERT INTO books (title, author, desc, questions, category) VALUES (?, ?, ?, ?, ?)", 
                                          (data['title'], data['author'], data['desc'], q_json, cat))
                    count += 1
                except Exception as e:
                    print(f"❌ Error adding book {data.get('title')}: {e}")
            
            await db.commit()
        print(f"✅ Migration complete! {count} books added/updated.")

    async def clear_library(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM library_files")
            await db.commit()


    # --- TRACKER & READ BOOKS ---
    async def get_user_books_list(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT book_name, date FROM read_books WHERE user_id=? ORDER BY date DESC", (user_id,)) as cursor:
                return await cursor.fetchall()

    async def add_read_book(self, user_id, book_name):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO read_books (user_id, book_name, date) VALUES (?, ?, ?)", (user_id, book_name, datetime.date.today()))
            await db.commit()
            
    async def add_tracker_log(self, user_id, pages):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO tracker (user_id, pages, date) VALUES (?, ?, ?)", (user_id, pages, datetime.date.today()))
            await db.commit()

    async def get_today_pages(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT SUM(pages) FROM tracker WHERE user_id=? AND date=?", (user_id, datetime.date.today())) as cursor:
                res = await cursor.fetchone()
                return res[0] if res[0] else 0

    # --- LIBRARY FILES (PDFs) ---
    async def clear_library(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM library_files")
            await db.commit()

    async def add_pdf(self, title, file_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO library_files (title, file_id) VALUES (?, ?)", (title, file_id))
            await db.commit()

    async def get_all_pdfs(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT id, title FROM library_files") as cursor:
                return await cursor.fetchall()
            
    async def get_pdf_by_id(self, file_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT file_id, title FROM library_files WHERE id=?", (file_id,)) as cursor:
                return await cursor.fetchone()

    # --- MEMORY / OTHER ---
    async def add_memory(self, user_id, title, content, file_id, file_type):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO memory (user_id, title, content, file_id, file_type) VALUES (?, ?, ?, ?, ?)", (user_id, title, content, file_id, file_type))
            await db.commit()

    async def get_leaderboard(self):
        async with aiosqlite.connect(self.db_name) as db:
            query = "SELECT fullname, quiz_points, streak, (SELECT COUNT(*) FROM read_books WHERE read_books.user_id = users.user_id) as book_count FROM users ORDER BY quiz_points DESC LIMIT 10"
            async with db.execute(query) as cursor:
                return await cursor.fetchall()

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                return await cursor.fetchall()
