import re
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import BOT_USERNAME
from keyboards.default import (
    cancel_keyboard,
    main_menu_keyboard,
    skip_description_keyboard,
)
from keyboards.inline import (
    add_button_keyboard,
    currency_keyboard,
    debt_confirm_keyboard,
    language_change_keyboard,
    main_menu_inline_keyboard,
    settings_keyboard,
    share_debt_keyboard,
)
from locales.texts import TEXTS
from services.sms import sms_service
from services.userbot import userbot_service
from states import AddDebt

router = Router(name="debts")

ALL_BTN_CREDITORS = [t["btn_creditors"] for t in TEXTS.values()]
ALL_BTN_DEBTORS = [t["btn_debtors"] for t in TEXTS.values()]
ALL_BTN_HISTORY = [t["btn_history"] for t in TEXTS.values()]
ALL_BTN_CANCEL = [t["btn_cancel"] for t in TEXTS.values()] + ["/cancel", "Bekor qilish", "Отмена"]
ALL_BTN_MAIN_MENU = [t.get("btn_main_menu", "🏠 Asosiy menyu") for t in TEXTS.values()] + [
    "/menu", "Asosiy menyu", "Главное меню", "Басты мәзір"
]
ALL_BTN_SKIP = [t.get("btn_skip", "➡️ O'tkazib yuborish") for t in TEXTS.values()] + [
    "/skip", "O'tkazib yuborish", "Пропустить", "Өткізіп жіберу"
]
ALL_BTN_SETTINGS = [t.get("btn_settings", "⚙️ Sozlamalar") for t in TEXTS.values()]
ALL_BTN_DONAT = [t.get("btn_donat", "💝 Donat") for t in TEXTS.values()]


@router.message(F.text.in_(ALL_BTN_MAIN_MENU))
async def handle_main_menu_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    await message.answer(TEXTS[lang]["main_menu_title"], reply_markup=main_menu_keyboard(lang))


@router.callback_query(F.data == "to_main_menu")
async def handle_main_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.message.answer(TEXTS[lang]["main_menu_title"], reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.message(F.text.in_(ALL_BTN_SETTINGS))
async def show_settings(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    await message.answer(TEXTS[lang]["settings_title"], reply_markup=settings_keyboard(lang, user_id=user_id))


@router.message(F.text.in_(ALL_BTN_DONAT))
async def show_donat(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    await message.answer(TEXTS[lang]["donat_text"], reply_markup=main_menu_inline_keyboard(lang))


@router.callback_query(F.data == "settings_change_language")
async def settings_change_language(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.message.edit_text(
        TEXTS[lang]["choose_new_language"], reply_markup=language_change_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "invite_friends")
async def process_invite_friends(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    bot_username = BOT_USERNAME or "bot"
    
    invite_text = f"Salom! Qarz va pullarni oson hisob-kitob qilish uchun Qarzbot'ga kiring: https://t.me/{bot_username}?start=ref_{user_id}"
    msg_text = (
        "Matnni ustiga bitta bosib nusxalang va do'stlaringizga (Telegram, SMS yoki boshqa joyda) yuboring:\n\n"
        f"`{invite_text}`"
    )
    
    await callback.message.answer(msg_text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    new_lang = callback.data.replace("set_lang_", "", 1)
    if new_lang not in ("uz", "ru", "kk", "en"):
        await callback.answer("Noto'g'ri til!", show_alert=True)
        return
    db.update_user_language(user_id, new_lang)
    await callback.message.edit_text(TEXTS[new_lang]["language_changed"])
    await callback.message.answer(
        TEXTS[new_lang]["main_menu_title"], reply_markup=main_menu_keyboard(new_lang)
    )
    await callback.answer()


@router.message(F.text.in_(ALL_BTN_CREDITORS))
async def show_creditors(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    debts = [d for d in db.get_debts_by_debtor(user_id) if d.get("status") in ("active", "pending")]

    if not debts:
        await message.answer(TEXTS[lang]["no_creditors"], reply_markup=add_button_keyboard(lang, "creditor"))
        return

    lines = [TEXTS[lang]["creditors_title"]]
    for d in debts:
        creditor = db.get_user(d["creditor_id"]) if d.get("creditor_id") else None
        if creditor:
            name = creditor["full_name"]
        elif d.get("phone"):
            name = f"+{d['phone']} ({TEXTS[lang]['pending_person']})"
        else:
            name = TEXTS[lang]["pending_person"]
        status_text = (
            TEXTS[lang]["status_pending"] if d["status"] == "pending" else TEXTS[lang]["status_active"]
        )
        desc_text = f" — <i>{d['description']}</i>" if d.get("description") else ""
        lines.append(f"• {name}: {db.format_amount(d['amount'])} {d['currency']} [{status_text}]{desc_text}")

    await message.answer("\n".join(lines), reply_markup=add_button_keyboard(lang, "creditor"))


@router.message(F.text.in_(ALL_BTN_DEBTORS))
async def show_debtors(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    debts = [d for d in db.get_debts_by_creditor(user_id) if d.get("status") in ("active", "pending")]

    if not debts:
        await message.answer(TEXTS[lang]["no_debtors"], reply_markup=add_button_keyboard(lang, "debtor"))
        return

    lines = [TEXTS[lang]["debtors_title"]]
    for d in debts:
        debtor = db.get_user(d["debtor_id"]) if d.get("debtor_id") else None
        if debtor:
            name = debtor["full_name"]
        elif d.get("phone"):
            name = f"+{d['phone']} ({TEXTS[lang]['pending_person']})"
        else:
            name = TEXTS[lang]["pending_person"]
        status_text = (
            TEXTS[lang]["status_pending"] if d["status"] == "pending" else TEXTS[lang]["status_active"]
        )
        desc_text = f" — <i>{d['description']}</i>" if d.get("description") else ""
        lines.append(f"• {name}: {db.format_amount(d['amount'])} {d['currency']} [{status_text}]{desc_text}")

    await message.answer("\n".join(lines), reply_markup=add_button_keyboard(lang, "debtor"))


@router.message(F.text.in_(ALL_BTN_HISTORY))
async def show_history(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    # To'lov tarixi
    history = db.get_history_by_user(user_id)

    # Barcha qarzlar (yakunlangan va faol)
    all_debts_as_debtor = db.get_debts_by_debtor(user_id)
    all_debts_as_creditor = db.get_debts_by_creditor(user_id)

    if not history and not all_debts_as_debtor and not all_debts_as_creditor:
        await message.answer(TEXTS[lang]["no_history"], reply_markup=main_menu_inline_keyboard(lang))
        return

    lines = [TEXTS[lang]["history_title"]]

    # 1) Qarzlar tarixi (kim olgan / kimga bergan)
    debt_lines = []
    for d in all_debts_as_debtor:
        creditor = db.get_user(d["creditor_id"]) if d.get("creditor_id") else None
        creditor_name = creditor["full_name"] if creditor else (f"+{d['phone']}" if d.get("phone") else "Noma'lum")
        status = d.get("status", "")
        if status == "active":
            status_emoji = "🟢"
            status_text = TEXTS[lang]["status_active"]
        elif status == "pending":
            status_emoji = "🟡"
            status_text = TEXTS[lang]["status_pending"]
        elif status == "closed":
            status_emoji = "🔴"
            status_text = "yopilgan"
        else:
            status_emoji = "⚪"
            status_text = status
        desc = f" — <i>{d['description']}</i>" if d.get("description") else ""
        ts_raw = d.get("created_at") or d.get("timestamp") or ""
        ts = str(ts_raw)[:10] if ts_raw else ""
        date_str = f" ({ts})" if ts else ""
        debt_lines.append(
            f"{status_emoji} ⬆️ <b>{creditor_name}</b>dan oldim: "
            f"<b>{db.format_amount(d['amount'])} {d['currency']}</b> [{status_text}]{desc}{date_str}"
        )

    for d in all_debts_as_creditor:
        debtor = db.get_user(d["debtor_id"]) if d.get("debtor_id") else None
        debtor_name = debtor["full_name"] if debtor else (f"+{d['phone']}" if d.get("phone") else "Noma'lum")
        status = d.get("status", "")
        if status == "active":
            status_emoji = "🟢"
            status_text = TEXTS[lang]["status_active"]
        elif status == "pending":
            status_emoji = "🟡"
            status_text = TEXTS[lang]["status_pending"]
        elif status == "closed":
            status_emoji = "🔴"
            status_text = "yopilgan"
        else:
            status_emoji = "⚪"
            status_text = status
        desc = f" — <i>{d['description']}</i>" if d.get("description") else ""
        ts_raw = d.get("created_at") or d.get("timestamp") or ""
        ts = str(ts_raw)[:10] if ts_raw else ""
        date_str = f" ({ts})" if ts else ""
        debt_lines.append(
            f"{status_emoji} ⬇️ <b>{debtor_name}</b>ga berdim: "
            f"<b>{db.format_amount(d['amount'])} {d['currency']}</b> [{status_text}]{desc}{date_str}"
        )

    if debt_lines:
        lines.append("")
        lines.append("📋 <b>Qarzlar:</b>")
        lines.extend(debt_lines[:20])

    # 2) To'lovlar tarixi
    if history:
        lines.append("")
        lines.append("💰 <b>To'lovlar:</b>")
        for h in history[:20]:
            from_id = h.get("from_user")
            to_id = h.get("to_user")
            if str(from_id) == str(user_id):
                other = db.get_user(to_id)
                other_name = other["full_name"] if other else "N/A"
                direction = f"➡️ <b>{other_name}</b>ga to'ladim"
            else:
                other = db.get_user(from_id)
                other_name = other["full_name"] if other else "N/A"
                direction = f"⬅️ <b>{other_name}</b>dan oldim"

            # Qarz izohi
            debt = db.get_debt(h.get("debt_id", ""))
            desc = ""
            if debt and debt.get("description"):
                desc = f" — <i>{debt['description']}</i>"

            status_text = "✅" if h.get("status") == "confirmed" else "⏳"
            ts_raw = h.get("timestamp") or ""
            ts = str(ts_raw)[:10] if ts_raw else ""
            date_str = f" ({ts})" if ts else ""
            lines.append(
                f"{status_text} {direction}: <b>{db.format_amount(h['amount'])} {h['currency']}</b>{desc}{date_str}"
            )

    await message.answer("\n".join(lines), reply_markup=main_menu_inline_keyboard(lang))


@router.callback_query(F.data.startswith("add_debt_"))
async def start_add_debt(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.replace("add_debt_", "", 1)  # "creditor" yoki "debtor"
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    await state.update_data(role=role)
    await state.set_state(AddDebt.entering_recipient)
    await callback.message.answer(TEXTS[lang]["enter_recipient"], reply_markup=cancel_keyboard(lang))
    await callback.answer()


async def _process_recipient(
    message: Message, state: FSMContext, target_id, target_phone: Optional[str] = None
) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if target_id is not None and str(target_id) == str(user_id):
        await message.answer(TEXTS[lang]["cannot_add_self"])
        return

    if target_phone:
        my_user = db.get_user(user_id)
        if my_user and db.normalize_phone(my_user.get("phone_number", "")) == db.normalize_phone(target_phone):
            await message.answer(TEXTS[lang]["cannot_add_self"])
            return

    await state.update_data(target_id=target_id, target_phone=target_phone)
    await state.set_state(AddDebt.choosing_currency)
    await message.answer(TEXTS[lang]["choose_currency"], reply_markup=currency_keyboard(lang))


@router.message(AddDebt.entering_recipient, F.content_type == ContentType.CONTACT)
async def add_debt_recipient_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    phone = db.normalize_phone(contact.phone_number)
    target_id = contact.user_id

    if not target_id and phone:
        found = db.find_user_by_phone(phone)
        if found:
            target_id = found.get("user_id")

    await _process_recipient(message, state, target_id, target_phone=phone)


@router.message(AddDebt.entering_recipient, F.text)
async def add_debt_recipient_text(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if message.text in ALL_BTN_MAIN_MENU:
        await state.clear()
        await message.answer(TEXTS[lang]["main_menu_title"], reply_markup=main_menu_keyboard(lang))
        return

    if message.text in ALL_BTN_CREDITORS:
        await state.clear()
        await show_creditors(message, state)
        return

    if message.text in ALL_BTN_DEBTORS:
        await state.clear()
        await show_debtors(message, state)
        return

    if message.text in ALL_BTN_HISTORY:
        await state.clear()
        await show_history(message, state)
        return

    if message.text in ALL_BTN_CANCEL:
        await state.clear()
        await message.answer(TEXTS[lang]["cancelled"], reply_markup=main_menu_keyboard(lang))
        return

    text = message.text.strip()
    target_id = None
    target_phone = None

    if text.startswith("@"):
        found = db.find_user_by_username(text)
        if found:
            target_id = found["user_id"]
            target_phone = db.normalize_phone(found.get("phone_number", ""))
        await state.update_data(target_username=text)
        await _process_recipient(message, state, target_id, target_phone=target_phone)
        return

    clean_digits = re.sub(r"\D", "", text)

    # 1. '+' belgisi yoki ajratuvchilar bilan yozilgan bo'lsa (masalan: +998901234567, +998 90 123 45 67):
    if text.startswith("+") or any(char in text for char in " ()-."):
        if len(clean_digits) in (9, 12):
            target_phone = db.normalize_phone(clean_digits)
            found = db.find_user_by_phone(target_phone)
            if found:
                target_id = found.get("user_id")
            await _process_recipient(message, state, target_id, target_phone=target_phone)
            return

    # 2. 9 ta raqam bo'lsa va O'zbekiston kodi bilan boshlansa (masalan: 901234567, 977774311):
    if len(clean_digits) == 9 and clean_digits[:2] in (
        "90", "91", "93", "94", "95", "97", "98", "99", "88", "33", "77", "50", "20", "29", "71", "78"
    ):
        target_phone = "998" + clean_digits
        found = db.find_user_by_phone(target_phone)
        if found:
            target_id = found.get("user_id")
        await _process_recipient(message, state, target_id, target_phone=target_phone)
        return

    # 3. 12 ta raqam bo'lsa va 998 bilan boshlansa (masalan: 998977774311):
    if len(clean_digits) == 12 and clean_digits.startswith("998"):
        target_phone = clean_digits
        found = db.find_user_by_phone(target_phone)
        if found:
            target_id = found.get("user_id")
        await _process_recipient(message, state, target_id, target_phone=target_phone)
        return

    # 4. Aks holda Telegram ID yoki bazadagi mavjud telefon/user tekshiruvi:
    if text.lstrip("-").isdigit():
        found_by_phone = db.find_user_by_phone(text)
        if found_by_phone:
            target_id = found_by_phone.get("user_id")
            target_phone = db.normalize_phone(found_by_phone.get("phone_number", ""))
        else:
            target_id = int(text)
            existing_user = db.get_user(target_id)
            if existing_user:
                target_phone = db.normalize_phone(existing_user.get("phone_number", ""))

    await _process_recipient(message, state, target_id, target_phone=target_phone)


@router.callback_query(AddDebt.choosing_currency, F.data.startswith("currency_"))
async def add_debt_currency(callback: CallbackQuery, state: FSMContext) -> None:
    currency = callback.data.replace("currency_", "", 1)
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    await state.update_data(currency=currency)
    await state.set_state(AddDebt.entering_amount)
    await callback.message.answer(TEXTS[lang]["enter_amount"], reply_markup=cancel_keyboard(lang))
    await callback.answer()


@router.message(AddDebt.entering_amount, F.text)
async def add_debt_amount(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if message.text in ALL_BTN_MAIN_MENU:
        await state.clear()
        await message.answer(TEXTS[lang]["main_menu_title"], reply_markup=main_menu_keyboard(lang))
        return

    if message.text in ALL_BTN_CREDITORS:
        await state.clear()
        await show_creditors(message, state)
        return

    if message.text in ALL_BTN_DEBTORS:
        await state.clear()
        await show_debtors(message, state)
        return

    if message.text in ALL_BTN_HISTORY:
        await state.clear()
        await show_history(message, state)
        return

    if message.text in ALL_BTN_CANCEL:
        await state.clear()
        await message.answer(TEXTS[lang]["cancelled"], reply_markup=main_menu_keyboard(lang))
        return

    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(TEXTS[lang]["invalid_amount"], reply_markup=cancel_keyboard(lang))
        return

    await state.update_data(amount=amount)
    await state.set_state(AddDebt.entering_description)
    await message.answer(
        TEXTS[lang]["enter_description"],
        reply_markup=skip_description_keyboard(lang),
    )


@router.message(AddDebt.entering_description, F.text)
async def add_debt_description(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if message.text in ALL_BTN_MAIN_MENU:
        await state.clear()
        await message.answer(TEXTS[lang]["main_menu_title"], reply_markup=main_menu_keyboard(lang))
        return

    if message.text in ALL_BTN_CREDITORS:
        await state.clear()
        await show_creditors(message, state)
        return

    if message.text in ALL_BTN_DEBTORS:
        await state.clear()
        await show_debtors(message, state)
        return

    if message.text in ALL_BTN_HISTORY:
        await state.clear()
        await show_history(message, state)
        return

    if message.text in ALL_BTN_CANCEL:
        await state.clear()
        await message.answer(TEXTS[lang]["cancelled"], reply_markup=main_menu_keyboard(lang))
        return

    description = ""
    if message.text not in ALL_BTN_SKIP:
        description = message.text.strip()

    data = await state.get_data()
    await state.clear()
    role = data["role"]
    target_id = data.get("target_id")
    target_phone = data.get("target_phone")
    target_username = data.get("target_username")
    currency = data["currency"]
    amount = data["amount"]

    if role == "creditor":
        debtor_id, creditor_id = user_id, target_id
    else:
        debtor_id, creditor_id = target_id, user_id

    desc_line = f"\n📝 <b>Izoh:</b> {description}" if description else ""
    desc_sms = f"\nIzoh: {description}" if description else ""

    if target_id is not None:
        debt_id = db.create_debt(
            debtor_id, creditor_id, amount, currency, status="pending", phone=target_phone, description=description
        )
        other_lang = db.get_user_language(target_id)
        requester = db.get_user(user_id)
        req_name = requester["full_name"] if requester else message.from_user.full_name
        role_text = (
            TEXTS[other_lang]["role_creditor"] if role == "creditor" else TEXTS[other_lang]["role_debtor"]
        )
        text = (
            TEXTS[other_lang]["debt_confirm_request"].format(
                name=req_name, role=role_text, amount=db.format_amount(amount), currency=currency
            )
            + desc_line
        )
        try:
            await bot.send_message(int(target_id), text, reply_markup=debt_confirm_keyboard(other_lang, debt_id))
            await message.answer(TEXTS[lang]["debt_request_sent"], reply_markup=main_menu_keyboard(lang))
        except Exception:
            await message.answer(
                TEXTS[lang]["debt_request_send_failed"], reply_markup=main_menu_keyboard(lang)
            )
    else:
        if role == "creditor":
            debt_id = db.create_debt(
                user_id, None, amount, currency, status="pending", phone=target_phone, description=description
            )
        else:
            debt_id = db.create_debt(
                None, user_id, amount, currency, status="pending", phone=target_phone, description=description
            )

        link = f"https://t.me/{BOT_USERNAME}?start=debt_{debt_id}"
        requester = db.get_user(user_id)
        req_name = requester["full_name"] if requester else message.from_user.full_name

        target_entity = target_phone or target_username
        pm_text = (
            f"🔔 <b>Qarz Oldi-Berdi</b>\n\n"
            f"<b>{req_name}</b> sizga <b>{db.format_amount(amount)} {currency}</b> qarz so'rovi kiritdi.{desc_line}\n\n"
            f"Batafsil ko'rish va tasdiqlash uchun quyidagi havola orqali botga kiring:\n👉 {link}"
        )

        sent_via_pm = False
        if userbot_service.is_active() and target_entity:
            ok, status_msg, found_uid = await userbot_service.send_pm(target_entity, pm_text)
            if ok:
                sent_via_pm = True
                if found_uid:
                    if role == "creditor":
                        db.set_debt_debtor(debt_id, found_uid)
                    else:
                        db.set_debt_creditor(debt_id, found_uid)

                kb = share_debt_keyboard(link, pm_text, target_phone or "", lang=lang)
                await message.answer(
                    f"✅ <b>Foydalanuvchining Telegram shaxsiy chatiga (lichkasiga) taklif xabari yuborildi!</b>{desc_line}\n\n"
                    f"U botga kirib tasdiqlagach, qarz faol holatga o'tadi.\n\n"
                    f"Taklif havolasi:\n{link}",
                    reply_markup=main_menu_keyboard(lang),
                )
                await message.answer("Tezkor amallar:", reply_markup=kb)

        if not sent_via_pm:
            if target_phone:
                sms_text = (
                    f"Qarz Oldi-Berdi: {req_name} sizga {db.format_amount(amount)} {currency} qarz kiritdi.{desc_sms}\n"
                    f"Tasdiqlash uchun botga kiring: {link}"
                )
                ok, res = await sms_service.send_sms(target_phone, sms_text)
                kb = share_debt_keyboard(link, sms_text, target_phone, lang=lang)
                if ok:
                    await message.answer(
                        TEXTS[lang]["sms_sent"].format(phone=target_phone, link=link),
                        reply_markup=main_menu_keyboard(lang),
                    )
                    await message.answer("Tezkor amallar:", reply_markup=kb)
                else:
                    await message.answer(
                        TEXTS[lang]["sms_not_sent"].format(reason=res, link=link),
                        reply_markup=main_menu_keyboard(lang),
                    )
                    await message.answer("Tezkor amallar:", reply_markup=kb)
            else:
                share_text = (
                    f"Qarz Oldi-Berdi: {req_name} sizga {db.format_amount(amount)} {currency} qarz kiritdi.{desc_sms}\n"
                    f"Tasdiqlash: {link}"
                )
                kb = share_debt_keyboard(link, share_text, lang=lang)
                await message.answer(
                    TEXTS[lang]["debt_link_generated"].format(link=link),
                    reply_markup=main_menu_keyboard(lang),
                )
                await message.answer("Tezkor amallar:", reply_markup=kb)

    await state.clear()


@router.callback_query(F.data.startswith("debt_confirm_"))
async def confirm_debt(callback: CallbackQuery, bot: Bot) -> None:
    debt_id = callback.data.replace("debt_confirm_", "", 1)
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    debt = db.get_debt(debt_id)
    if not debt or debt.get("status") != "pending":
        await callback.answer(TEXTS[lang]["debt_not_found"], show_alert=True)
        return

    amount = debt["amount"]
    currency = debt["currency"]
    description = debt.get("description", "")
    desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""

    db.update_debt_status(debt_id, "active")

    other_id = debt["creditor_id"] if str(debt.get("debtor_id")) == str(user_id) else debt["debtor_id"]
    other_user = db.get_user(other_id) if other_id else None
    other_name = other_user["full_name"] if other_user else "N/A"

    await callback.message.edit_text(
        TEXTS[lang]["debt_confirmed_by_you"].format(
            name=other_name,
            amount=db.format_amount(amount),
            currency=currency,
            desc_line=desc_line,
        )
    )
    await callback.answer()

    if other_id:
        other_lang = db.get_user_language(other_id)
        confirmer = db.get_user(user_id)
        confirmer_name = confirmer["full_name"] if confirmer else "N/A"
        other_desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""
        try:
            await bot.send_message(
                int(other_id),
                TEXTS[other_lang]["debt_confirmed_by_other"].format(
                    name=confirmer_name,
                    amount=db.format_amount(amount),
                    currency=currency,
                    desc_line=other_desc_line,
                ),
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("debt_reject_"))
async def reject_debt(callback: CallbackQuery, bot: Bot) -> None:
    debt_id = callback.data.replace("debt_reject_", "", 1)
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    debt = db.get_debt(debt_id)
    if not debt or debt.get("status") != "pending":
        await callback.answer(TEXTS[lang]["debt_not_found"], show_alert=True)
        return

    amount = debt["amount"]
    currency = debt["currency"]
    description = debt.get("description", "")
    desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""

    db.update_debt_status(debt_id, "closed")

    other_id = debt["creditor_id"] if str(debt.get("debtor_id")) == str(user_id) else debt["debtor_id"]
    other_user = db.get_user(other_id) if other_id else None
    other_name = other_user["full_name"] if other_user else "N/A"

    await callback.message.edit_text(
        TEXTS[lang]["debt_rejected_by_you"].format(
            name=other_name,
            amount=db.format_amount(amount),
            currency=currency,
            desc_line=desc_line,
        )
    )
    await callback.answer()

    if other_id:
        other_lang = db.get_user_language(other_id)
        rejecter = db.get_user(user_id)
        rejecter_name = rejecter["full_name"] if rejecter else "N/A"
        other_desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""
        try:
            await bot.send_message(
                int(other_id),
                TEXTS[other_lang]["debt_rejected_by_other"].format(
                    name=rejecter_name,
                    amount=db.format_amount(amount),
                    currency=currency,
                    desc_line=other_desc_line,
                ),
            )
        except Exception:
            pass

