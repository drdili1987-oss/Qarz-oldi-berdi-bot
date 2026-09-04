import database as db
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales.texts import TEXTS


def currency_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 UZS", callback_data="currency_UZS"),
                InlineKeyboardButton(text="💵 USD", callback_data="currency_USD"),
            ],
            [
                InlineKeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu"), callback_data="to_main_menu"),
            ],
        ]
    )


def debt_confirm_keyboard(lang: str, debt_id: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["btn_confirm"], callback_data=f"debt_confirm_{debt_id}"),
                InlineKeyboardButton(text=t["btn_reject"], callback_data=f"debt_reject_{debt_id}"),
            ]
        ]
    )


def payment_confirm_keyboard(lang: str, debt_id: str, amount: float) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t["btn_confirm"], callback_data=f"pay_confirm_{debt_id}_{amount}"
                ),
                InlineKeyboardButton(
                    text=t["btn_reject"], callback_data=f"pay_reject_{debt_id}_{amount}"
                ),
            ]
        ]
    )


def add_button_keyboard(lang: str, role: str, pending_debts: list = None) -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    rows = []
    if pending_debts:
        for p in pending_debts:
            btn_text = f"❌ Bekor qilish: {p['name']} ({db.format_amount(p['amount'])} {p['currency']})"
            rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"debt_cancel_creator_{p['debt_id']}")])
    rows.append([InlineKeyboardButton(text=t["btn_add_new"], callback_data=f"add_debt_{role}")])
    rows.append([InlineKeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu"), callback_data="to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def person_list_keyboard(people: list, prefix: str, lang: str = "uz") -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    rows = []
    for p in people:
        label = f"{p['name']} ({db.format_amount(p['amount'])} {p['currency']})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}_{p['debt_id']}")])
    rows.append([InlineKeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu"), callback_data="to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_inline_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu"), callback_data="to_main_menu")]
        ]
    )


def broadcast_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["btn_confirm"], callback_data="broadcast_confirm"),
                InlineKeyboardButton(text=t["btn_reject"], callback_data="broadcast_cancel"),
            ]
        ]
    )


def share_debt_keyboard(link: str, text: str, phone: str = "", lang: str = "uz", debt_id: str = "") -> InlineKeyboardMarkup:
    import urllib.parse
    t = TEXTS.get(lang, TEXTS["uz"])
    
    # Telegram ulashish
    encoded_text_tg = urllib.parse.quote_plus(text)
    share_url = f"https://t.me/share/url?url={urllib.parse.quote_plus(link)}&text={encoded_text_tg}"
    
    # SMS orqali ulashish (Veb sahifaga yo'naltirish)
    encoded_text_sms = urllib.parse.quote(text)
    sms_url = f"https://drdili1987-oss.github.io/Qarz-oldi-berdi-bot/?text={encoded_text_sms}"

    buttons = [
        [InlineKeyboardButton(text="✈️ Telegramda ulashish", url=share_url)],
        [InlineKeyboardButton(text="📱 SMS orqali ulashish", url=sms_url)],
    ]
    if debt_id:
        buttons.append([InlineKeyboardButton(text=t.get("btn_cancel_pending", "❌ So'rovni bekor qilish"), callback_data=f"debt_cancel_creator_{debt_id}")])
    buttons.append([InlineKeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu"), callback_data="to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_keyboard(lang: str = "uz", user_id: int = None) -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    buttons = [
        [InlineKeyboardButton(text=t.get("btn_invite_friends", "👥 Do'stlarga ulashish"), callback_data="invite_friends")],
        [InlineKeyboardButton(text=t["btn_change_language"], callback_data="settings_change_language")],
        [InlineKeyboardButton(text=t.get("btn_main_menu", "🏠 Asosiy menyu"), callback_data="to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def language_change_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang_uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
            [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="set_lang_kk")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")],
        ]
    )
