import csv
import io
import re
from datetime import datetime
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from config import ADMIN_IDS
from keyboards.inline import broadcast_confirm_keyboard
from locales.texts import TEXTS
from states import AdminBroadcast

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS or str(user_id) in [str(x) for x in ADMIN_IDS]


@router.message(Command("admin"))
@router.message(Command("admin_help"))
async def cmd_admin_help(message: Message) -> None:
    user_id = message.from_user.id
    if not _is_admin(user_id):
        return

    text = (
        "👑 <b>Admin boshqaruv paneli buyruqlari:</b>\n\n"
        "📊 /stats — Umumiy statistika va aylanma\n"
        "👥 /users — Foydalanuvchilar ro'yxati\n"
        "📥 /export_users — Barcha foydalanuvchilarni Excel/CSV faylda yuklab olish\n"
        "🔍 /find &lt;so'rov&gt; — Foydalanuvchini telefon, username yoki ism orqali qidirish\n"
        "📢 /broadcast — Barcha foydalanuvchilarga ommaviy xabar yuborish"
    )
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if not _is_admin(user_id):
        await message.answer(TEXTS[lang]["not_admin"])
        return

    stats = db.get_stats()
    text = TEXTS[lang]["admin_stats"].format(
        total_users=stats["total_users"],
        active_debts=stats["active_debts_count"],
        total_uzs=db.format_amount(stats["total_uzs"]),
        total_usd=db.format_amount(stats["total_usd"]),
    )

    # Qo'shimcha demografiya
    text += "\n\n📊 <b>Demografiya (Foydalanuvchilar portreti)</b>:\n"
    text += f"👨 Erkaklar: {stats.get('male_count', 0)} ta\n"
    text += f"👩 Ayollar: {stats.get('female_count', 0)} ta\n\n"

    text += "🌍 <b>Top davlatlar</b>:\n"
    for c, count in stats.get("top_countries", []):
        text += f" - {c}: {count} ta\n"

    text += "\n🏙 <b>Top shaharlar</b>:\n"
    for c, count in stats.get("top_cities", []):
        text += f" - {c}: {count} ta\n"

    text += "\n💼 <b>Kasb va sohalar</b>:\n"
    for occ, count in stats.get("top_occupations", []):
        text += f" - {occ}: {count} ta\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Foydalanuvchilar ro'yxati", callback_data="admin_view_users")],
            [InlineKeyboardButton(text="📥 Excel (CSV) yuklab olish", callback_data="admin_export_users")],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.message(Command("users"))
@router.callback_query(F.data == "admin_view_users")
async def cmd_users(event: Message | CallbackQuery) -> None:
    user_id = event.from_user.id
    if not _is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("Ruxsat berilmagan!", show_alert=True)
        return

    users = db.get_all_users()
    if not users:
        text = "Hozircha ro'yxatdan o'tgan foydalanuvchilar yo'q."
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    lines = [f"👥 <b>Foydalanuvchilar ro'yxati (Jami: {len(users)} ta):</b>\n"]
    for i, (uid, u) in enumerate(list(users.items())[:25]):
        uname = f"@{u['username']}" if u.get("username") else "yo'q"
        phone = f"+{u['phone_number']}" if u.get("phone_number") else "yo'q"
        lines.append(f"{i+1}. <b>{u.get('full_name', 'N/A')}</b> ({uname})\n   📱 Tel: {phone} | ID: <code>{uid}</code>")

    if len(users) > 25:
        lines.append(f"\n<i>...va yana {len(users) - 25} nafar foydalanuvchi. To'liq ro'yxatni yuklab olish uchun quyidagi tugmani bosing:</i>")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 To'liq ro'yxatni Excel (CSV) da yuklab olish", callback_data="admin_export_users")]
        ]
    )

    msg_text = "\n".join(lines)
    if isinstance(event, CallbackQuery):
        await event.message.answer(msg_text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(msg_text, reply_markup=kb)


@router.message(Command("export_users"))
@router.callback_query(F.data == "admin_export_users")
async def cmd_export_users(event: Message | CallbackQuery) -> None:
    user_id = event.from_user.id
    if not _is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("Ruxsat berilmagan!", show_alert=True)
        return

    users = db.get_all_users()
    output = io.StringIO()
    # Excel to'g'ri ochishi uchun BOM belgisi va UTF-8
    writer = csv.writer(output, delimiter=",")
    writer.writerow(["ID", "Ism Familiya", "Telefon", "Username", "Til", "Yoshi", "Jinsi", "Davlat", "Shahar", "Kasbi", "Ro'yxatdan o'tgan sana"])

    for uid, u in users.items():
        writer.writerow([
            uid,
            u.get("full_name", ""),
            f"+{u.get('phone_number', '')}" if u.get("phone_number") else "",
            f"@{u.get('username', '')}" if u.get("username") else "",
            u.get("language", "uz"),
            u.get("age", ""),
            u.get("gender", ""),
            u.get("country", ""),
            u.get("city", ""),
            u.get("occupation", ""),
            str(u.get("created_at", ""))[:19].replace("T", " "),
        ])

    csv_data = "\ufeff" + output.getvalue()
    file_bytes = csv_data.encode("utf-8")
    doc = BufferedInputFile(file_bytes, filename=f"qarzbot_users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")

    caption = f"📊 <b>Barcha foydalanuvchilar ro'yxati</b>\nJami: <b>{len(users)} ta</b>"
    if isinstance(event, CallbackQuery):
        await event.message.answer_document(document=doc, caption=caption)
        await event.answer()
    else:
        await event.answer_document(document=doc, caption=caption)


@router.message(Command("find"))
async def cmd_find_user(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    if not _is_admin(user_id):
        return

    query = (command.args or "").strip()
    if not query:
        await message.answer("🔍 <b>Qidiruv uchun ma'lumot kiriting:</b>\nMasalan:\n• <code>/find 998901234567</code>\n• <code>/find @username</code>\n• <code>/find Dilmurod</code>\n• <code>/find 156664</code> (ID)")
        return

    users = db.get_all_users()
    matched = []
    clean_query = query.lstrip("@").lower()
    clean_digits = re.sub(r"\D", "", query)

    for uid, u in users.items():
        uid_str = str(uid)
        phone = db.normalize_phone(u.get("phone_number", ""))
        uname = str(u.get("username", "")).lstrip("@").lower()
        full_name = str(u.get("full_name", "")).lower()

        if clean_digits and (clean_digits in phone or clean_digits == uid_str):
            matched.append((uid, u))
        elif clean_query and (clean_query in uname or clean_query in full_name):
            if (uid, u) not in matched:
                matched.append((uid, u))

    if not matched:
        await message.answer(f"❌ <b>«{query}»</b> bo'yicha hech qanday foydalanuvchi topilmadi.")
        return

    for uid, u in matched[:5]:
        debts_as_debtor = [d for d in db.get_debts_by_debtor(uid) if d.get("status") == "active"]
        debts_as_creditor = [d for d in db.get_debts_by_creditor(uid) if d.get("status") == "active"]

        total_qarz = sum(float(d.get("amount", 0)) for d in debts_as_debtor if d.get("currency") == "UZS")
        total_haq = sum(float(d.get("amount", 0)) for d in debts_as_creditor if d.get("currency") == "UZS")

        res_text = (
            f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
            f"🆔 <b>ID:</b> <code>{uid}</code>\n"
            f"👤 <b>Ism:</b> {u.get('full_name', 'N/A')}\n"
            f"📱 <b>Telefon:</b> +{u.get('phone_number', 'yo`q')}\n"
            f"🔗 <b>Username:</b> @{u.get('username', 'yo`q')}\n"
            f"🌐 <b>Til:</b> {u.get('language', 'uz')}\n"
            f"📅 <b>Ro'yxatdan o'tgan:</b> {str(u.get('created_at', ''))[:10]}\n\n"
            f"💰 <b>Faol qarzlari (olgan):</b> {db.format_amount(total_qarz)} UZS ({len(debts_as_debtor)} ta)\n"
            f"💵 <b>Faol haqlari (bergan):</b> {db.format_amount(total_haq)} UZS ({len(debts_as_creditor)} ta)"
        )
        await message.answer(res_text)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if not _is_admin(user_id):
        await message.answer(TEXTS[lang]["not_admin"])
        return

    await state.set_state(AdminBroadcast.entering_message)
    await message.answer(TEXTS[lang]["broadcast_prompt"])


@router.message(AdminBroadcast.entering_message, F.text)
async def broadcast_receive_text(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminBroadcast.confirming)
    await message.answer(
        TEXTS[lang]["broadcast_preview"].format(text=message.text),
        reply_markup=broadcast_confirm_keyboard(lang),
    )


@router.callback_query(AdminBroadcast.confirming, F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    if not _is_admin(user_id):
        await callback.answer(TEXTS[lang]["not_admin"], show_alert=True)
        return

    data = await state.get_data()
    text = data.get("broadcast_text", "")

    users = db.get_all_users()
    sent, failed = 0, 0
    for uid_str in users:
        try:
            await bot.send_message(int(uid_str), text)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await callback.message.edit_text(TEXTS[lang]["broadcast_done"].format(sent=sent, failed=failed))
    await callback.answer()


@router.callback_query(AdminBroadcast.confirming, F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    await state.clear()
    await callback.message.edit_text(TEXTS[lang]["broadcast_cancelled"])
    await callback.answer()
