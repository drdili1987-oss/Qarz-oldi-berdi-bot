from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import ADMIN_IDS
from keyboards.inline import broadcast_confirm_keyboard
from locales.texts import TEXTS
from states import AdminBroadcast

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS or str(user_id) in [str(x) for x in ADMIN_IDS]


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
    for c, count in stats.get('top_countries', []):
        text += f" - {c}: {count} ta\n"
        
    text += "\n🏙 <b>Top shaharlar</b>:\n"
    for c, count in stats.get('top_cities', []):
        text += f" - {c}: {count} ta\n"
        
    text += "\n💼 <b>Kasb va sohalar</b>:\n"
    for occ, count in stats.get('top_occupations', []):
        text += f" - {occ}: {count} ta\n"

    await message.answer(text)


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
