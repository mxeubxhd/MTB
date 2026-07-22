import os
import asyncio
import json
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import database as db

BOT_TOKEN = "8890889822:AAE8TJvJvUpVHQ8BCuO22OvLhhHNJ63GLks"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

with open("lessons_data.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)


def get_subject(subject_id):
    for s in DATA["fanlar"]:
        if s["id"] == subject_id:
            return s
    return None


def get_lesson(subject_id, lesson_id):
    subject = get_subject(subject_id)
    if not subject:
        return None
    for l in subject["darslar"]:
        if l["id"] == lesson_id:
            return l
    return None


# ---------- /start ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    db.add_user(message.from_user.id, message.from_user.full_name)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s["name"], callback_data=f"subject_{s['id']}")]
            for s in DATA["fanlar"]
        ]
    )
    await message.answer(
        f"Salom, {message.from_user.full_name}! 👋\n\n"
        "Bu bepul interaktiv ta'lim botiga xush kelibsiz!\n"
        "Darslarni o'qib, testlarni yeching va reytingda yuqoriga chiqing 🏆\n\n"
        "Fanlardan birini tanlang:",
        reply_markup=kb,
    )


# ---------- /reyting ----------
@router.message(Command("reyting"))
async def cmd_leaderboard(message: Message):
    rows = db.get_leaderboard()
    if not rows:
        await message.answer("Hozircha reytingda hech kim yo'q.")
        return
    text = "🏆 Reyting (TOP 10):\n\n"
    for i, (name, score) in enumerate(rows, start=1):
        text += f"{i}. {name} — {score} ball\n"
    await message.answer(text)


# ---------- /profil ----------
@router.message(Command("profil"))
async def cmd_profile(message: Message):
    user, lessons_done = db.get_user_stats(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosing.")
        return
    name, score = user
    await message.answer(
        f"👤 {name}\n"
        f"✅ Tugatilgan darslar: {lessons_done}\n"
        f"⭐ Umumiy ball: {score}"
    )


# ---------- Fan tanlanganda darslar ro'yxati ----------
@router.callback_query(F.data.startswith("subject_"))
async def show_lessons(callback: CallbackQuery):
    subject_id = callback.data.split("_", 1)[1]
    subject = get_subject(subject_id)
    completed = db.get_completed_lessons(callback.from_user.id, subject_id)

    kb_buttons = []
    for l in subject["darslar"]:
        mark = "✅ " if l["id"] in completed else "📘 "
        kb_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}{l['id']}. {l['title']}",
                    callback_data=f"lesson_{subject_id}_{l['id']}",
                )
            ]
        )
    kb_buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(
        f"{subject['name']} — darslar ro'yxati:", reply_markup=kb
    )
    await callback.answer()


# ---------- Bosh menyuga qaytish ----------
@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s["name"], callback_data=f"subject_{s['id']}")]
            for s in DATA["fanlar"]
        ]
    )
    await callback.message.edit_text("Fanlardan birini tanlang:", reply_markup=kb)
    await callback.answer()


# ---------- Dars matnini ko'rsatish ----------
@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    _, subject_id, lesson_id = callback.data.split("_")
    lesson_id = int(lesson_id)
    lesson = get_lesson(subject_id, lesson_id)

    text = f"📖 {lesson['title']}\n\n{lesson['text']}"
    if lesson.get("video"):
        text += f"\n\n🎥 Video: {lesson['video']}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Testni boshlash",
                    callback_data=f"quiz_{subject_id}_{lesson_id}_0_0",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"subject_{subject_id}")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ---------- Test savolini ko'rsatish / yakunlash ----------
@router.callback_query(F.data.startswith("quiz_"))
async def quiz_handler(callback: CallbackQuery):
    _, subject_id, lesson_id, q_index, score = callback.data.split("_")
    lesson_id = int(lesson_id)
    q_index = int(q_index)
    score = int(score)

    lesson = get_lesson(subject_id, lesson_id)
    questions = lesson["savollar"]

    # Barcha savollar tugagan bo'lsa — natijani ko'rsatish
    if q_index >= len(questions):
        db.save_result(callback.from_user.id, subject_id, lesson_id, score, len(questions))
        percent = round(score / len(questions) * 100)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Darslarga qaytish", callback_data=f"subject_{subject_id}")],
                [InlineKeyboardButton(text="🏆 Reytingni ko'rish", callback_data="show_rating")],
            ]
        )
        await callback.message.edit_text(
            f"✅ Test yakunlandi!\n\n"
            f"Natijangiz: {score}/{len(questions)} ({percent}%)\n"
            f"Ball umumiy hisobingizga qo'shildi!",
            reply_markup=kb,
        )
        await callback.answer()
        return

    q = questions[q_index]
    kb_buttons = []
    for i, variant in enumerate(q["variantlar"]):
        kb_buttons.append(
            [
                InlineKeyboardButton(
                    text=variant,
                    callback_data=f"answer_{subject_id}_{lesson_id}_{q_index}_{score}_{i}",
                )
            ]
        )
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(
        f"❓ Savol {q_index + 1}/{len(questions)}:\n\n{q['savol']}",
        reply_markup=kb,
    )
    await callback.answer()


# ---------- Javobni tekshirish ----------
@router.callback_query(F.data.startswith("answer_"))
async def answer_handler(callback: CallbackQuery):
    _, subject_id, lesson_id, q_index, score, chosen = callback.data.split("_")
    lesson_id = int(lesson_id)
    q_index = int(q_index)
    score = int(score)
    chosen = int(chosen)

    lesson = get_lesson(subject_id, lesson_id)
    q = lesson["savollar"][q_index]
    correct = q["javob"]

    if chosen == correct:
        score += 1
        feedback = "✅ To'g'ri javob!"
    else:
        feedback = f"❌ Noto'g'ri. To'g'ri javob: {q['variantlar'][correct]}"

    await callback.answer(feedback, show_alert=True)

    next_index = q_index + 1
    next_text = (
        "➡️ Keyingi savol"
        if next_index < len(lesson["savollar"])
        else "🏁 Natijani ko'rish"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=next_text,
                    callback_data=f"quiz_{subject_id}_{lesson_id}_{next_index}_{score}",
                )
            ]
        ]
    )
    await callback.message.edit_text(
        "Javobingiz qabul qilindi. Davom etish uchun tugmani bosing 👇",
        reply_markup=kb,
    )


# ---------- Natija sahifasidan reytingga o'tish ----------
@router.callback_query(F.data == "show_rating")
async def show_rating_cb(callback: CallbackQuery):
    rows = db.get_leaderboard()
    text = "🏆 Reyting (TOP 10):\n\n"
    if not rows:
        text += "Hozircha hech kim yo'q."
    for i, (name, score) in enumerate(rows, start=1):
        text += f"{i}. {name} — {score} ball\n"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="back_main")]]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


async def main():
    db.init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())