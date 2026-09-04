"""
Firebase Realtime Database bilan ishlash uchun barcha funksiyalar.
Kesh (In-memory caching) bilan tezlashtirilgan.

Baza strukturasi:
    users/{user_id}   -> user_id, full_name, phone_number, username, language, created_at
    debts/{debt_id}   -> debt_id, debtor_id, creditor_id, amount, currency,
                          status ('pending'|'active'|'closed'), last_notified_at, created_at
    history/{trans_id}-> trans_id, debt_id, from_user, to_user,
                          type ('borrow'|'lend'|'income'|'outcome'),
                          amount, currency, status, timestamp
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, db

from config import FIREBASE_CREDENTIALS_JSON, FIREBASE_CREDENTIALS_PATH, FIREBASE_DB_URL

logger = logging.getLogger(__name__)

USERS_REF = "users"
DEBTS_REF = "debts"
HISTORY_REF = "history"

# ==================== IN-MEMORY KESH ====================
_USERS_CACHE: dict = {}
_USER_LANGS: dict = {}
_PHONES_CACHE: dict = {}
_USERNAMES_CACHE: dict = {}

_DEBTS_CACHE: Optional[dict] = None
_DEBTS_CACHE_TIME: float = 0.0

_HISTORY_CACHE: Optional[dict] = None
_HISTORY_CACHE_TIME: float = 0.0

CACHE_TTL = 15.0  # Debts va History uchun kesh vaqti (soniya)


def format_amount(amount) -> str:
    try:
        val = float(amount)
        if val == int(val):
            return f"{int(val):,}".replace(",", " ")
        return f"{val:,.2f}".replace(",", " ")
    except (ValueError, TypeError):
        return str(amount)


def _init_firebase() -> None:
    if firebase_admin._apps:
        return

    if FIREBASE_CREDENTIALS_JSON:
        cred_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_dict)
    elif os.path.exists(FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    else:
        raise RuntimeError(
            "Firebase credentials topilmadi. FIREBASE_CREDENTIALS_JSON "
            "(to'liq JSON matn) yoki FIREBASE_CREDENTIALS_PATH (fayl yo'li) "
            "environment variable'larini sozlang."
        )

    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})


_init_firebase()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==================== USERS ====================

def get_user(user_id: int) -> Optional[dict]:
    if not user_id:
        return None
    uid_str = str(user_id)
    if uid_str in _USERS_CACHE:
        return _USERS_CACHE[uid_str]

    user_data = db.reference(f"{USERS_REF}/{uid_str}").get()
    if user_data:
        _USERS_CACHE[uid_str] = user_data
        if "language" in user_data:
            _USER_LANGS[uid_str] = user_data["language"]
        if "phone_number" in user_data:
            clean = normalize_phone(user_data["phone_number"])
            if clean:
                _PHONES_CACHE[clean] = uid_str
        if "username" in user_data and user_data["username"]:
            _USERNAMES_CACHE[user_data["username"].lstrip("@").lower()] = uid_str
    return user_data


def user_exists(user_id: int) -> bool:
    return get_user(user_id) is not None


def create_user(
    user_id: int,
    full_name: str,
    phone_number: str,
    language: str,
    username: str = "",
    age: int = 0,
    gender: str = "",
    country: str = "",
    city: str = "",
    occupation: str = "",
) -> None:
    uid_str = str(user_id)
    user_data = {
        "user_id": uid_str,
        "full_name": full_name,
        "phone_number": phone_number,
        "username": username or "",
        "language": language,
        "age": age,
        "gender": gender,
        "country": country,
        "city": city,
        "occupation": occupation,
        "created_at": _now_iso(),
    }
    # Keshga saqlash
    _USERS_CACHE[uid_str] = user_data
    _USER_LANGS[uid_str] = language
    clean_phone = normalize_phone(phone_number)
    if clean_phone:
        _PHONES_CACHE[clean_phone] = uid_str
    if username:
        _USERNAMES_CACHE[username.lstrip("@").lower()] = uid_str

    # Firebase'ga yozish
    db.reference(f"{USERS_REF}/{uid_str}").set(user_data)
    if username:
        db.reference(f"usernames/{username.lstrip('@').lower()}").set(uid_str)
    if clean_phone:
        db.reference(f"phones/{clean_phone}").set(uid_str)


def update_user_language(user_id: int, language: str) -> None:
    uid_str = str(user_id)
    _USER_LANGS[uid_str] = language
    if uid_str in _USERS_CACHE:
        _USERS_CACHE[uid_str]["language"] = language
    db.reference(f"{USERS_REF}/{uid_str}/language").set(language)


def delete_user(user_id: int) -> None:
    uid_str = str(user_id)
    user = _USERS_CACHE.pop(uid_str, None) or db.reference(f"{USERS_REF}/{uid_str}").get()
    _USER_LANGS.pop(uid_str, None)
    if user:
        phone = normalize_phone(user.get("phone_number", ""))
        username = str(user.get("username", "")).lstrip("@").lower()
        if phone:
            _PHONES_CACHE.pop(phone, None)
            db.reference(f"phones/{phone}").delete()
        if username:
            _USERNAMES_CACHE.pop(username, None)
            db.reference(f"usernames/{username}").delete()
    db.reference(f"{USERS_REF}/{uid_str}").delete()


def get_user_language(user_id: int) -> str:
    uid_str = str(user_id)
    if uid_str in _USER_LANGS:
        return _USER_LANGS[uid_str]
    user = get_user(user_id)
    if user and "language" in user:
        lang = user["language"]
        return lang if lang in ("uz", "ru", "kk", "en") else "uz"
    return "uz"


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 9:
        digits = "998" + digits
    return digits


def find_user_by_phone(phone: str) -> Optional[dict]:
    clean = normalize_phone(phone)
    if not clean:
        return None

    if clean in _PHONES_CACHE:
        return get_user(int(_PHONES_CACHE[clean]))

    uid = db.reference(f"phones/{clean}").get()
    if uid:
        _PHONES_CACHE[clean] = str(uid)
        return get_user(int(uid))

    all_users = get_all_users()
    for uid_str, udata in all_users.items():
        if normalize_phone(udata.get("phone_number", "")) == clean:
            _PHONES_CACHE[clean] = uid_str
            return udata
    return None


def find_user_by_username(username: str) -> Optional[dict]:
    username = username.lstrip("@").lower()
    if not username:
        return None

    if username in _USERNAMES_CACHE:
        return get_user(int(_USERNAMES_CACHE[username]))

    uid = db.reference(f"usernames/{username}").get()
    if uid:
        _USERNAMES_CACHE[username] = str(uid)
        return get_user(int(uid))

    all_users = get_all_users()
    for uid_str, udata in all_users.items():
        if str(udata.get("username", "")).lower() == username:
            _USERNAMES_CACHE[username] = uid_str
            return udata
    return None


def get_all_users() -> dict:
    global _USERS_CACHE
    users = db.reference(USERS_REF).get() or {}
    for uid_str, udata in users.items():
        _USERS_CACHE[uid_str] = udata
        if "language" in udata:
            _USER_LANGS[uid_str] = udata["language"]
        if "phone_number" in udata:
            clean = normalize_phone(udata["phone_number"])
            if clean:
                _PHONES_CACHE[clean] = uid_str
        if "username" in udata and udata["username"]:
            _USERNAMES_CACHE[udata["username"].lstrip("@").lower()] = uid_str
    return users


# ==================== DEBTS ====================

def get_all_debts() -> dict:
    global _DEBTS_CACHE, _DEBTS_CACHE_TIME
    now = time.time()
    if _DEBTS_CACHE is not None and (now - _DEBTS_CACHE_TIME) < CACHE_TTL:
        return _DEBTS_CACHE

    debts = db.reference(DEBTS_REF).get() or {}
    _DEBTS_CACHE = debts
    _DEBTS_CACHE_TIME = now
    return _DEBTS_CACHE


def create_debt(
    debtor_id: Optional[int],
    creditor_id: Optional[int],
    amount: float,
    currency: str,
    status: str = "pending",
    phone: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    global _DEBTS_CACHE
    debt_id = str(uuid.uuid4())
    debt_data = {
        "debt_id": debt_id,
        "debtor_id": debtor_id,
        "creditor_id": creditor_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "description": description or "",
        "due_date": due_date,
        "last_notified_at": _now_iso(),
        "created_at": _now_iso(),
    }
    if phone:
        debt_data["phone"] = phone

    if _DEBTS_CACHE is not None:
        _DEBTS_CACHE[debt_id] = debt_data

    db.reference(f"{DEBTS_REF}/{debt_id}").set(debt_data)
    return debt_id


def get_debt(debt_id: str) -> Optional[dict]:
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        d = dict(_DEBTS_CACHE[debt_id])
        d["debt_id"] = debt_id
        return d
    debt = db.reference(f"{DEBTS_REF}/{debt_id}").get()
    if debt:
        debt["debt_id"] = debt_id
        if _DEBTS_CACHE is not None:
            _DEBTS_CACHE[debt_id] = debt
    return debt


def update_debt_status(debt_id: str, status: str) -> None:
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        _DEBTS_CACHE[debt_id]["status"] = status
    db.reference(f"{DEBTS_REF}/{debt_id}/status").set(status)


def update_debt_amount(debt_id: str, new_amount: float) -> None:
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        _DEBTS_CACHE[debt_id]["amount"] = new_amount
    db.reference(f"{DEBTS_REF}/{debt_id}/amount").set(new_amount)


def update_debt_notified(debt_id: str) -> None:
    iso_now = _now_iso()
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        _DEBTS_CACHE[debt_id]["last_notified_at"] = iso_now
    db.reference(f"{DEBTS_REF}/{debt_id}/last_notified_at").set(iso_now)


def set_debt_debtor(debt_id: str, debtor_id: int) -> None:
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        _DEBTS_CACHE[debt_id]["debtor_id"] = debtor_id
    db.reference(f"{DEBTS_REF}/{debt_id}/debtor_id").set(debtor_id)


def set_debt_creditor(debt_id: str, creditor_id: int) -> None:
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        _DEBTS_CACHE[debt_id]["creditor_id"] = creditor_id
    db.reference(f"{DEBTS_REF}/{debt_id}/creditor_id").set(creditor_id)


def delete_debt(debt_id: str) -> None:
    if _DEBTS_CACHE is not None and debt_id in _DEBTS_CACHE:
        _DEBTS_CACHE.pop(debt_id, None)
    db.reference(f"{DEBTS_REF}/{debt_id}").delete()


def get_debts_by_debtor(user_id: int, status: Optional[str] = None) -> list:
    all_debts = get_all_debts()
    result = []
    for debt_id, d in all_debts.items():
        if str(d.get("debtor_id")) == str(user_id) and (status is None or d.get("status") == status):
            d = dict(d)
            d["debt_id"] = debt_id
            result.append(d)
    return result


def get_debts_by_creditor(user_id: int, status: Optional[str] = None) -> list:
    all_debts = get_all_debts()
    result = []
    for debt_id, d in all_debts.items():
        if str(d.get("creditor_id")) == str(user_id) and (status is None or d.get("status") == status):
            d = dict(d)
            d["debt_id"] = debt_id
            result.append(d)
    return result


# ==================== HISTORY ====================

def get_all_history() -> dict:
    global _HISTORY_CACHE, _HISTORY_CACHE_TIME
    now = time.time()
    if _HISTORY_CACHE is not None and (now - _HISTORY_CACHE_TIME) < CACHE_TTL:
        return _HISTORY_CACHE

    history = db.reference(HISTORY_REF).get() or {}
    _HISTORY_CACHE = history
    _HISTORY_CACHE_TIME = now
    return _HISTORY_CACHE


def add_history(
    debt_id: str,
    from_user: int,
    to_user: int,
    type_: str,
    amount: float,
    currency: str,
    status: str = "confirmed",
) -> str:
    global _HISTORY_CACHE
    trans_id = str(uuid.uuid4())
    data = {
        "trans_id": trans_id,
        "debt_id": debt_id,
        "from_user": str(from_user),
        "to_user": str(to_user),
        "type": type_,
        "amount": amount,
        "currency": currency,
        "status": status,
        "timestamp": _now_iso(),
    }
    if _HISTORY_CACHE is not None:
        _HISTORY_CACHE[trans_id] = data

    db.reference(f"{HISTORY_REF}/{trans_id}").set(data)
    return trans_id


def get_history_by_user(user_id: int) -> list:
    all_history = get_all_history()
    result = []
    uid_str = str(user_id)
    for trans_id, h in all_history.items():
        if str(h.get("from_user")) == uid_str or str(h.get("to_user")) == uid_str:
            h = dict(h)
            h["trans_id"] = trans_id
            result.append(h)
    result.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return result


# ==================== ADMIN STATISTIKA ====================

def get_stats() -> dict:
    users = get_all_users()
    debts = get_all_debts()

    male_count = 0
    female_count = 0
    countries = {}
    cities = {}
    occupations = {}

    for u in users.values():
        g = u.get("gender", "").lower()
        if g in ["erkak", "мужской", "еркек", "male"]:
            male_count += 1
        elif g in ["ayol", "женский", "әйел", "female"]:
            female_count += 1

        c = u.get("country", "").strip().title()
        if c:
            countries[c] = countries.get(c, 0) + 1

        city = u.get("city", "").strip().title()
        if city:
            cities[city] = cities.get(city, 0) + 1

        occ = u.get("occupation", "").strip().title()
        if occ:
            occupations[occ] = occupations.get(occ, 0) + 1

    top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]
    top_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]
    top_occupations = sorted(occupations.items(), key=lambda x: x[1], reverse=True)[:5]

    active_debts = [d for d in debts.values() if d.get("status") == "active"]
    total_uzs = sum(float(d.get("amount", 0)) for d in active_debts if d.get("currency") == "UZS")
    total_usd = sum(float(d.get("amount", 0)) for d in active_debts if d.get("currency") == "USD")

    return {
        "total_users": len(users),
        "male_count": male_count,
        "female_count": female_count,
        "top_countries": top_countries,
        "top_cities": top_cities,
        "top_occupations": top_occupations,
        "active_debts_count": len(active_debts),
        "total_uzs": total_uzs,
        "total_usd": total_usd,
    }
