def gender_keyboard(lang: str):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.get("btn_male", "Erkak")), KeyboardButton(text=t.get("btn_female", "Ayol"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
