from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards.default import cancel_keyboard, main_menu_keyboard
from keyboards.inline import payment_confirm_keyboard, person_list_keyboard
from locales.texts import TEXTS
from states import FinanceOperation

router = Router(name="finance")

ALL_BTN_INCOME = [t["btn_income"] for t in TEXTS.values()]
ALL_BTN_OUTCOME = [t["btn_outcome"] for t in TEXTS.values()]
ALL_BTN_CANCEL = [t["btn_cancel"] for t in TEXTS.values()] + ["/cancel", "Bekor qilish", "Отмена"]
ALL_BTN_MAIN_MENU = [t.get("btn_main_menu", "🏠 Asosiy menyu") for t in TEXTS.values()] + [
    "/menu", "Asosiy menyu", "Главное меню", "Басты мәзір"
]


@router.message(F.text.in_(ALL_BTN_INCOME))
async def start_income(message: Message, state: FSMContext) -> None:
    await state.clear()
    """Kirim: menga qarz qaytarildi -> men creditor bo'lgan faol qarzlar ro'yxati."""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    debts = db.get_debts_by_creditor(user_id, status="active")

    if not debts:
        await message.answer(TEXTS[lang]["no_active_debtors"], reply_markup=main_menu_keyboard(lang))
        return

    people = []
    for d in debts:
        debtor = db.get_user(d["debtor_id"])
        people.append(
            {
                "debt_id": d["debt_id"],
                "name": debtor["full_name"] if debtor else "N/A",
                "amount": d["amount"],
                "currency": d["currency"],
            }
        )

    await state.set_state(FinanceOperation.choosing_person)
    await state.update_data(direction="income")
    await message.answer(
        TEXTS[lang]["choose_person_income"], reply_markup=person_list_keyboard(people, "fin_person", lang=lang)
    )


@router.message(F.text.in_(ALL_BTN_OUTCOME))
async def start_outcome(message: Message, state: FSMContext) -> None:
    await state.clear()
    """Chiqim: men qarz to'ladim -> men debtor bo'lgan faol qarzlar ro'yxati."""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    debts = db.get_debts_by_debtor(user_id, status="active")

    if not debts:
        await message.answer(TEXTS[lang]["no_active_creditors"], reply_markup=main_menu_keyboard(lang))
        return

    people = []
    for d in debts:
        creditor = db.get_user(d["creditor_id"])
        people.append(
            {
                "debt_id": d["debt_id"],
                "name": creditor["full_name"] if creditor else "N/A",
                "amount": d["amount"],
                "currency": d["currency"],
            }
        )

    await state.set_state(FinanceOperation.choosing_person)
    await state.update_data(direction="outcome")
    await message.answer(
        TEXTS[lang]["choose_person_outcome"], reply_markup=person_list_keyboard(people, "fin_person", lang=lang)
    )


@router.callback_query(FinanceOperation.choosing_person, F.data.startswith("fin_person_"))
async def choose_person(callback: CallbackQuery, state: FSMContext) -> None:
    debt_id = callback.data.replace("fin_person_", "", 1)
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    debt = db.get_debt(debt_id)
    if not debt or debt.get("status") != "active":
        await callback.answer(TEXTS[lang]["debt_not_found"], show_alert=True)
        return

    await state.update_data(debt_id=debt_id)
    await state.set_state(FinanceOperation.entering_amount)
    await callback.message.answer(
        TEXTS[lang]["enter_payment_amount"].format(max_amount=db.format_amount(debt["amount"]), currency=debt["currency"]),
        reply_markup=cancel_keyboard(lang),
    )
    await callback.answer()


@router.message(FinanceOperation.entering_amount, F.text)
async def enter_payment_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if message.text in ALL_BTN_MAIN_MENU:
        await state.clear()
        await message.answer(TEXTS[lang]["main_menu_title"], reply_markup=main_menu_keyboard(lang))
        return

    if message.text in ALL_BTN_CANCEL:
        await state.clear()
        await message.answer(TEXTS[lang]["cancelled"], reply_markup=main_menu_keyboard(lang))
        return

    data = await state.get_data()
    debt_id = data["debt_id"]
    debt = db.get_debt(debt_id)

    if not debt or debt.get("status") != "active":
        await state.clear()
        await message.answer(TEXTS[lang]["debt_not_found"], reply_markup=main_menu_keyboard(lang))
        return

    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0 or amount > debt["amount"]:
            raise ValueError
    except ValueError:
        await message.answer(TEXTS[lang]["invalid_payment_amount"].format(max_amount=db.format_amount(debt["amount"])))
        return

    direction = data["direction"]
    other_id = debt["creditor_id"] if direction == "outcome" else debt["debtor_id"]
    other_lang = db.get_user_language(other_id)
    requester = db.get_user(user_id)
    direction_text = (
        TEXTS[other_lang]["payment_type_outcome"]
        if direction == "outcome"
        else TEXTS[other_lang]["payment_type_income"]
    )
    text = TEXTS[other_lang]["payment_confirm_request"].format(
        name=requester["full_name"], amount=db.format_amount(amount), currency=debt["currency"], type=direction_text
    )

    try:
        await bot.send_message(
            int(other_id), text, reply_markup=payment_confirm_keyboard(other_lang, debt_id, amount)
        )
        await message.answer(TEXTS[lang]["payment_request_sent"], reply_markup=main_menu_keyboard(lang))
    except Exception:
        await message.answer(TEXTS[lang]["debt_request_send_failed"], reply_markup=main_menu_keyboard(lang))

    await state.clear()


@router.callback_query(F.data.startswith("pay_confirm_"))
async def confirm_payment(callback: CallbackQuery, bot: Bot) -> None:
    _, _, debt_id, amount_str = callback.data.split("_", 3)
    amount = float(amount_str)
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    debt = db.get_debt(debt_id)
    if not debt or debt.get("status") != "active":
        await callback.answer(TEXTS[lang]["debt_not_found"], show_alert=True)
        return

    payer_id = debt["debtor_id"]
    receiver_id = debt["creditor_id"]
    old_total = debt["amount"]
    new_amount = round(old_total - amount, 2)
    description = debt.get("description", "")
    desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""

    if new_amount <= 0:
        db.update_debt_amount(debt_id, 0)
        db.update_debt_status(debt_id, "closed")
    else:
        db.update_debt_amount(debt_id, new_amount)

    db.add_history(debt_id, payer_id, receiver_id, "outcome", amount, debt["currency"], status="confirmed")

    status_line = (
        TEXTS[lang]["debt_fully_closed"] + "\n"
        if new_amount <= 0
        else TEXTS[lang]["debt_partially_closed"].format(remaining=db.format_amount(new_amount), currency=debt["currency"]) + "\n"
    )

    # Tasdiqlagan odamga batafsil xabar
    other_id = payer_id if str(user_id) == str(receiver_id) else receiver_id
    other_user = db.get_user(other_id)
    other_name = other_user["full_name"] if other_user else "N/A"

    await callback.message.edit_text(
        TEXTS[lang]["payment_confirmed_by_you"].format(
            name=other_name,
            amount=db.format_amount(amount),
            currency=debt["currency"],
            total=old_total,
            desc_line=desc_line,
            status_line=status_line,
        )
    )
    await callback.answer()

    # Ikkinchi tomonga batafsil xabar
    other_lang = db.get_user_language(other_id)
    confirmer = db.get_user(user_id)
    confirmer_name = confirmer["full_name"] if confirmer else "N/A"

    other_desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""
    other_status_line = (
        TEXTS[other_lang]["debt_fully_closed"] + "\n"
        if new_amount <= 0
        else TEXTS[other_lang]["debt_partially_closed"].format(remaining=db.format_amount(new_amount), currency=debt["currency"]) + "\n"
    )

    try:
        await bot.send_message(
            int(other_id),
            TEXTS[other_lang]["payment_confirmed_by_other"].format(
                name=confirmer_name,
                amount=db.format_amount(amount),
                currency=debt["currency"],
                total=old_total,
                desc_line=other_desc_line,
                status_line=other_status_line,
            ),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot) -> None:
    _, _, debt_id, amount_str = callback.data.split("_", 3)
    amount = float(amount_str)
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)

    debt = db.get_debt(debt_id)
    if not debt:
        await callback.answer(TEXTS[lang]["debt_not_found"], show_alert=True)
        return

    total = debt["amount"]
    description = debt.get("description", "")
    desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""

    other_id = debt["debtor_id"] if str(user_id) == str(debt["creditor_id"]) else debt["creditor_id"]
    other_user = db.get_user(other_id)
    other_name = other_user["full_name"] if other_user else "N/A"

    await callback.message.edit_text(
        TEXTS[lang]["payment_rejected_by_you"].format(
            name=other_name,
            amount=db.format_amount(amount),
            currency=debt["currency"],
            total=db.format_amount(total),
            desc_line=desc_line,
        )
    )
    await callback.answer()

    other_lang = db.get_user_language(other_id)
    rejecter = db.get_user(user_id)
    rejecter_name = rejecter["full_name"] if rejecter else "N/A"
    other_desc_line = f"📝 Izoh: <b>{description}</b>\n" if description else ""

    try:
        await bot.send_message(
            int(other_id),
            TEXTS[other_lang]["payment_rejected_by_other"].format(
                name=rejecter_name,
                amount=db.format_amount(amount),
                currency=debt["currency"],
                total=db.format_amount(total),
                desc_line=other_desc_line,
            ),
        )
    except Exception:
        pass

