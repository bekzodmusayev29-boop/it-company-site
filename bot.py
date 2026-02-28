import logging
import asyncio
import json
import random
from io import BytesIO

import telebot
from telebot import types

# Local imports
from data import LIBRARY_DATA
from database import DatabaseManager
from utils import generate_profile_card

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
BOT_TOKEN = "7623963043:AAG9INqRwqEa9WhynbN3hkZva6fLISx5ROY"
ADMIN_ID = 6361665798
DEV_USERNAME = "bekzodmusayev29"
BOT_NAME = "@OnlineKitobxonBot"

# Logging setup
logging.basicConfig(level=logging.INFO)

# Initialize Bot and Database
bot = telebot.TeleBot(BOT_TOKEN)
db = DatabaseManager()

# Quiz Session Storage
quiz_session = {}

# ==========================================
# 2. KEYBOARDS & UI HELPERS
# ==========================================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🏛 Ziyo Maskani (Test)"),
        types.KeyboardButton("✍️ Kitob Qo'shish")
    )
    kb.add(
        types.KeyboardButton("📅 Kundalik"),
        types.KeyboardButton("🏆 Peshiqadamlar")
    )
    kb.add(
        types.KeyboardButton("👤 Mening Profilim"),
        types.KeyboardButton("📥 Elektron Kutubxona")
    )
    kb.add(
        types.KeyboardButton("📚 O'qilgan Kitoblar"),
        types.KeyboardButton("🎲 Tasodifiy Kitob")
    )
    return kb

def get_pagination_kb(page, total_pages, prefix):
    kb = types.InlineKeyboardMarkup(row_width=3)
    row = []
    
    if page > 1:
        row.append(types.InlineKeyboardButton("⬅️", callback_data=f"{prefix}_prev_{page}"))
    
    row.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        row.append(types.InlineKeyboardButton("➡️", callback_data=f"{prefix}_next_{page}"))
    
    kb.add(*row)
    return kb

def get_test_page_markup(books, page=1):
    ITEMS_PER_PAGE = 10
    total_pages = (len(books) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_books = books[start_idx:end_idx]
    
    # 1-Column Layout
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for book in current_books:
        b_id, title, author = book
        # Truncate title if too long
        display_title = title if len(title) < 35 else title[:33] + "..."
        kb.add(types.InlineKeyboardButton(f"📘 {display_title}", callback_data=f"startquiz_{b_id}"))
    
    # Pagination
    if total_pages > 1:
        nav_kb = get_pagination_kb(page, total_pages, "test")
        for row in nav_kb.keyboard:
            kb.add(*row)
    
    return kb

def get_library_page_markup(pdfs, page=1):
    ITEMS_PER_PAGE = 10
    total_pages = (len(pdfs) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_pdfs = pdfs[start_idx:end_idx]
    
    # 1-Column Layout
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for pdf in current_pdfs:
        p_id, title = pdf
        # Truncate
        display_title = title if len(title) < 35 else title[:33] + "..."
        kb.add(types.InlineKeyboardButton(f"📥 {display_title}", callback_data=f"getpdf_{p_id}"))
    
    # Pagination
    if total_pages > 1:
        nav_kb = get_pagination_kb(page, total_pages, "lib")
        for row in nav_kb.keyboard:
            kb.add(*row)
    
    return kb

# ==========================================
# 3. HANDLERS
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    asyncio.run(db.add_user(message.from_user.id, message.from_user.full_name))
    
    bot.reply_to(
        message,
        f"👋 Assalomu alaykum, {message.from_user.full_name}!\n\n"
        f"🧠 <b>Kitobxon Pro</b> botiga xush kelibsiz.\n"
        f"Bu yerda siz kitoblar asosida bilimingizni sinashingiz, yangi asarlar o'qishingiz va sovg'alar yutishingiz mumkin!",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['clear_library'])
def clear_library_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    asyncio.run(db.clear_library())
    bot.reply_to(message, "🗑 <b>Kutubxona tozalandi!</b>\nBarcha PDF fayllar bazadan o'chirildi.", parse_mode="HTML")

# --- DOCUMENT UPLOAD ---
@bot.message_handler(content_types=['document'])
def handle_document_upload(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    doc = message.document
    
    if doc.mime_type == 'application/pdf':
        file_id = doc.file_id
        file_name = doc.file_name
        clean_name = file_name.replace('.pdf', '').replace('_', ' ')
        
        asyncio.run(db.add_pdf(clean_name, file_id))
        bot.reply_to(message, f"✅ <b>Kitob bazaga qo'shildi!</b>\n\nNomi: {clean_name}", parse_mode="HTML")
    
    elif doc.mime_type == 'application/json':
        try:
            file_info = bot.get_file(doc.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            content = downloaded_file.decode('utf-8')
            data = json.loads(content)
            
            title = data.get('title')
            author = data.get('author')
            desc = data.get('desc')
            questions = data.get('quiz')
            category = data.get('category', 'Badiiy')
            
            if title and author and questions:
                asyncio.run(db.add_book_with_quiz(title, author, desc, json.dumps(questions, ensure_ascii=False), category))
                bot.reply_to(message, f"✅ <b>\"{title}\"</b> muvaffaqiyatli qo'shildi!", parse_mode="HTML")
            else:
                bot.reply_to(message, "❌ JSON fayl tuzilishi noto'g'ri!")
        except Exception as e:
            bot.reply_to(message, f"❌ Xatolik yuz berdi: {e}")
    else:
        bot.reply_to(message, "⚠️ Iltimos, faqat PDF yoki JSON (test) fayl yuklang.")

# --- MAIN MENU NAVIGATION ---

@bot.message_handler(func=lambda m: m.text == "🏛 Ziyo Maskani (Test)")
def ziyo_maskani(message):
    books = asyncio.run(db.get_all_books())
    if not books:
        bot.reply_to(message, "Hozircha testlar yo'q.")
        return
    
    kb = get_test_page_markup(books, 1)
    bot.send_message(message.chat.id, "📚 <b>Qaysi asar bo'yicha bilimingizni sinamoqchisiz?</b>", parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "✍️ Kitob Qo'shish")
def add_book_guide(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(
            message,
            "👨‍💻 <b>Admin panel:</b>\n\n"
            "1. <b>Test yuklash:</b> .json fayl yuboring.\n"
            "2. <b>PDF Kitob yuklash:</b> .pdf fayl yuboring.\n"
            "3. <b>Tozalash:</b> /clear_library",
            parse_mode="HTML"
        )
    else:
        bot.reply_to(message, "Bu bo'lim faqat adminlar uchun!")

@bot.message_handler(func=lambda m: m.text == "📥 Elektron Kutubxona")
def ebook_library(message):
    pdfs = asyncio.run(db.get_all_pdfs())
    if not pdfs:
        bot.reply_to(message, "📭 Kutubxona hozircha bo'sh.")
        return
    
    kb = get_library_page_markup(pdfs, 1)
    bot.send_message(message.chat.id, "📚 <b>Elektron Kutubxona:</b>\nMarhamat, o'qish uchun kitob tanlang:", parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🏆 Peshiqadamlar")
def leaderboard(message):
    leaders = asyncio.run(db.get_leaderboard())
    
    medals = ["🥇", "🥈", "🥉"]
    txt = "🏆 <b>Eng faol kitobxonlar</b>\n\n"
    
    for idx, user in enumerate(leaders):
        name, score, streak, books_read = user
        rank = medals[idx] if idx < 3 else f"<b>{idx+1}.</b>"
        txt += f"{rank} {name}\n"
        txt += f"   └ ⭐️ {score} | 📚 {books_read} | 🔥 {streak}\n"
        
        if idx == 2:
            txt += "➖➖➖➖➖➖➖➖➖➖\n"
    
    bot.reply_to(message, txt, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👤 Mening Profilim")
def my_profile(message):
    stats = asyncio.run(db.get_user_stats(message.from_user.id))
    if not stats:
        bot.reply_to(message, "Ma'lumot topilmadi.")
        return
    
    user_id, fullname, points, streak, _, _ = stats
    
    # Fetch User Avatar
    avatar_bytes = None
    try:
        photos = bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            file_info = bot.get_file(file_id)
            avatar_bytes = bot.download_file(file_info.file_path)
    except Exception as e:
        print(f"Profile photo error: {e}")
    
    # Generate Image
    img_io = generate_profile_card(fullname, "Kitobxon", points, streak, avatar_bytes)
    
    caption = (
        f"👤 <b>Foydalanuvchi:</b> {fullname}\n"
        f"⭐️ <b>Ballar:</b> {points}\n"
        f"🔥 <b>Davomiylik:</b> {streak} kun"
    )
    
    bot.send_photo(message.chat.id, img_io, caption=caption, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎲 Tasodifiy Kitob")
def random_book(message):
    recommendation = asyncio.run(db.get_recommendations(message.from_user.id))
    bot.reply_to(message, recommendation, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📚 O'qilgan Kitoblar")
def my_read_books(message):
    books = asyncio.run(db.get_user_books_list(message.from_user.id))
    if not books:
        bot.reply_to(message, "Siz hali hech qanday kitob o'qimadingiz.")
        return
    
    txt = "📚 <b>Siz o'qigan kitoblar:</b>\n\n"
    for b_name, date in books:
        txt += f"✅ {b_name} ({date})\n"
    
    bot.reply_to(message, txt, parse_mode="HTML")

# --- QUIZ CALLBACKS ---

@bot.callback_query_handler(func=lambda call: call.data.startswith("startquiz_"))
def start_quiz_callback(call):
    book_id = int(call.data.split("_")[1])
    book = asyncio.run(db.get_book_details(book_id))
    
    if not book:
        bot.answer_callback_query(call.id, "Kitob topilmadi!", show_alert=True)
        return
    
    questions = json.loads(book[4])
    random.shuffle(questions)
    
    quiz_session[call.from_user.id] = {
        'book_id': book_id,
        'book_title': book[1],
        'score': 0,
        'q_idx': 0,
        'questions': questions
    }
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_quiz_question(call.message.chat.id, call.from_user.id)

def send_quiz_question(chat_id, user_id):
    session = quiz_session.get(user_id)
    if not session:
        return
    
    q_idx = session['q_idx']
    questions = session['questions']
    
    if q_idx >= len(questions) or q_idx >= 10:
        finish_quiz(chat_id, user_id)
        return
    
    q_data = questions[q_idx]
    opts = q_data['opts'].copy()
    random.shuffle(opts)
    
    correct_opt = q_data['ans']
    correct_idx = -1
    for i, o in enumerate(opts):
        if o == correct_opt:
            correct_idx = i
            break
    
    labels = ["A", "B", "C"]
    display_opts = opts[:3]
    
    txt = f"❓ <b>{q_idx+1}-savol:</b>\n\n{q_data['q']}\n\n"
    for i, opt in enumerate(display_opts):
        txt += f"<b>{labels[i]})</b> {opt}\n"
    
    kb = types.InlineKeyboardMarkup(row_width=3)
    row_btns = []
    for i in range(len(display_opts)):
        is_correct = "1" if i == correct_idx else "0"
        row_btns.append(types.InlineKeyboardButton(f"[ {labels[i]} ]", callback_data=f"ans_{is_correct}"))
    
    kb.add(*row_btns)
    bot.send_message(chat_id, txt, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def answer_callback(call):
    is_correct = call.data.split("_")[1] == "1"
    session = quiz_session.get(call.from_user.id)
    
    if not session:
        bot.answer_callback_query(call.id, "Sessiya tugagan.", show_alert=True)
        return
    
    if is_correct:
        session['score'] += 1
        bot.answer_callback_query(call.id, "✅ To'g'ri!")
    else:
        bot.answer_callback_query(call.id, "❌ Xato!")
    
    session['q_idx'] += 1
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_quiz_question(call.message.chat.id, call.from_user.id)

def finish_quiz(chat_id, user_id):
    session = quiz_session.get(user_id)
    if not session:
        return
    
    score = session['score']
    total = min(len(session['questions']), 10)
    
    asyncio.run(db.update_points(user_id, score * 10))
    if score >= total / 2:
        asyncio.run(db.add_read_book(user_id, session['book_title']))
    
    msg = f"🏁 <b>Test yakunlandi!</b>\n\n✅ Natija: {score}/{total}\n⭐️ Ballar: +{score * 10}"
    quiz_session[user_id] = None
    bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=main_menu())

# --- PDF DOWNLOAD ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("getpdf_"))
def get_pdf_callback(call):
    file_id_record = asyncio.run(db.get_pdf_by_id(int(call.data.split("_")[1])))
    
    if file_id_record:
        file_id, title = file_id_record
        bot.send_document(call.message.chat.id, file_id, caption=f"📕 <b>{title}</b>", parse_mode="HTML")
        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id, "❌ Fayl topilmadi.", show_alert=True)

# --- PAGINATION HANDLERS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("test_"))
def test_pagination(call):
    action, page = call.data.split("_")[1], int(call.data.split("_")[2])
    new_page = page - 1 if action == "prev" else page + 1
    
    books = asyncio.run(db.get_all_books())
    kb = get_test_page_markup(books, new_page)
    
    bot.edit_message_text(
        "📚 <b>Qaysi asar bo'yicha bilimingizni sinamoqchisiz?</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("lib_"))
def lib_pagination(call):
    action, page = call.data.split("_")[1], int(call.data.split("_")[2])
    new_page = page - 1 if action == "prev" else page + 1
    
    pdfs = asyncio.run(db.get_all_pdfs())
    kb = get_library_page_markup(pdfs, new_page)
    
    bot.edit_message_text(
        "� <b>Elektron Kutubxona:</b>\nMarhamat, o'qish uchun kitob tanlang:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "noop")
def noop_callback(call):
    bot.answer_callback_query(call.id)

# ==========================================
# 4. MAIN EXECUTION
# ==========================================

def main():
    # Force migrate data on startup
    asyncio.run(db.create_tables())
    asyncio.run(db.force_migrate(LIBRARY_DATA))
    
    # Aggressively clear webhooks and wait
    try:
        bot.remove_webhook()
        import time
        time.sleep(1)
        print("✅ Webhook tozalandi")
    except Exception as e:
        print(f"⚠️ Webhook xatosi: {e}")
    
    print("🚀 Bot ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi")
    except Exception as e:
        print(f"\n❌ Xatolik: {e}")
