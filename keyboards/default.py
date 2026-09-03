from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from locales.texts import TEXTS

LANGUAGE_BUTTONS = {
    "🇺🇿 O'zbekcha": "uz",
    "🇷🇺 Русский": "ru",
    "🇰🇿 Қазақша": "kk",
    "🇬🇧 English": "en",
}


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha")],
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇰🇿 Қазақша")],
            [KeyboardButton(text="🇬🇧 English")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS[lang]["send_contact_btn"], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t["btn_creditors"], style="danger"), 
                KeyboardButton(text=t["btn_debtors"], style="success")
            ],
            [KeyboardButton(text=t["btn_history"], style="primary")],
            [KeyboardButton(text=t["btn_income"]), KeyboardButton(text=t["btn_outcome"])],
            [KeyboardButton(text=t["btn_settings"]), KeyboardButton(text=t["btn_donat"])],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu")),
                KeyboardButton(text=t["btn_cancel"]),
            ]
        ],
        resize_keyboard=True,
    )


def skip_description_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.get("btn_skip", "➡️ O'tkazib yuborish"))],
            [
                KeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu")),
                KeyboardButton(text=t["btn_cancel"]),
            ],
        ],
        resize_keyboard=True,
    )


def due_date_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.get("btn_1_week", "1 hafta")), KeyboardButton(text=t.get("btn_1_month", "1 oy"))],
            [KeyboardButton(text=t.get("btn_no_due_date", "Muddat yo'q"))],
            [
                KeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu")),
                KeyboardButton(text=t["btn_cancel"]),
            ],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
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

