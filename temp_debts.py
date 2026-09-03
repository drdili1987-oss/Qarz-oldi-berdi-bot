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

    await state.update_data(description=description)
    await state.set_state(AddDebt.entering_due_date)
    
    from keyboards.default import due_date_keyboard
    await message.answer(TEXTS[lang].get("enter_due_date", "Qarz qaytarish muddatini tanlang yoki YYYY-MM-DD formatida kiriting (masalan: 2026-12-31):"), reply_markup=due_date_keyboard(lang))

@router.message(AddDebt.entering_due_date, F.text)
async def add_debt_due_date(message: Message, state: FSMContext, bot: Bot) -> None:
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
        
    text = message.text.strip()
    due_date = None
    
    from datetime import datetime, timedelta
    now = datetime.now()
    
    if text == TEXTS[lang].get("btn_1_week", "1 hafta"):
        due_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    elif text == TEXTS[lang].get("btn_1_month", "1 oy"):
        due_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    elif text == TEXTS[lang].get("btn_no_due_date", "Muddat yo'q") or text in ALL_BTN_SKIP:
        due_date = None
    else:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d")
            due_date = parsed.strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Noto'g'ri format. Iltimos quyidagi tugmalardan foydalaning yoki YYYY-MM-DD formatida kiriting:")
            return

    data = await state.get_data()
    await state.clear()
    
    description = data.get("description", "")
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
    due_line = f"\n⏳ <b>Muddat:</b> {due_date}" if due_date else ""
    due_sms = f"\nMuddat: {due_date}" if due_date else ""

    if target_id is not None:
        debt_id = db.create_debt(
            debtor_id, creditor_id, amount, currency, status="pending", phone=target_phone, description=description, due_date=due_date
        )
        other_lang = db.get_user_language(target_id)
        requester = db.get_user(user_id)
        req_name = requester["full_name"] if requester else message.from_user.full_name
        role_text = (
            TEXTS[other_lang]["role_creditor"] if role == "creditor" else TEXTS[other_lang]["role_debtor"]
        )
        
        text = (
            TEXTS[other_lang].get("debt_confirm_request", "<b>{name}</b> sizga yangi qarz so'rovi yubordi.\nMiqdor: {amount} {currency}").format(
                name=req_name, role=role_text, amount=db.format_amount(amount), currency=currency, due_date=due_date or "Belgilanmagan"
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
                user_id, None, amount, currency, status="pending", phone=target_phone, description=description, due_date=due_date
            )
        else:
            debt_id = db.create_debt(
                None, user_id, amount, currency, status="pending", phone=target_phone, description=description, due_date=due_date
            )

        link = f"https://t.me/{BOT_USERNAME}?start=debt_{debt_id}"
        requester = db.get_user(user_id)
        req_name = requester["full_name"] if requester else message.from_user.full_name

        target_entity = target_phone or target_username
        pm_text = (
            f"🤝 <b>Qarz Oldi-Berdi</b>\n\n"
            f"<b>{req_name}</b> sizga <b>{db.format_amount(amount)} {currency}</b> qarz so'rovi kiritdi.{desc_line}{due_line}\n\n"
            f"Batafsil ko'rish va tasdiqlash uchun quyidagi havola orqali botga kiring:\n🔗 {link}"
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
                    f"✅ <b>Foydalanuvchining Telegram shaxsiy chatiga (lichkasiga) taklif xabari yuborildi!</b>{desc_line}{due_line}\n\n"
                    f"U botga kirib tasdiqlagach, qarz faol holatga o'tadi.\n\n"
                    f"Taklif havolasi:\n{link}",
                    reply_markup=main_menu_keyboard(lang),
                )
                await message.answer("Tezkor amallar:", reply_markup=kb)

        if not sent_via_pm:
            if target_phone:
                sms_text = (
                    f"Qarz Oldi-Berdi: {req_name} sizga {db.format_amount(amount)} {currency} qarz kiritdi.{desc_sms}{due_sms}\n"
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
                    f"Qarz Oldi-Berdi: {req_name} sizga {db.format_amount(amount)} {currency} qarz kiritdi.{desc_sms}{due_sms}\n"
                    f"Tasdiqlash: {link}"
                )
                kb = share_debt_keyboard(link, share_text, target_phone or "", lang=lang)
                await message.answer(
                    TEXTS[lang]["debt_link_generated"].format(link=link),
                    reply_markup=main_menu_keyboard(lang),
                )
                await message.answer("Tezkor amallar:", reply_markup=kb)
