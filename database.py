"""
Firebase Realtime Database bilan ishlash uchun barcha funksiyalar.

Baza strukturasi:
    users/{user_id}   -> user_id, full_name, phone_number, username, language, created_at
    debts/{debt_id}   -> debt_id, debtor_id, creditor_id, amount, currency,
                          status ('pending'|'active'|'closed'), last_notified_at, created_at
    history/{trans_id}-> trans_id, debt_id, from_user, to_user,
                          type ('borrow'|'lend'|'income'|'outcome'),
                          amount, currency, status, timestamp
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, db

from config import FIREBASE_CREDENTIALS_JSON, FIREBASE_CREDENTIALS_PATH, FIREBASE_DB_URL

USERS_REF = "users"
DEBTS_REF = "debts"
HISTORY_REF = "history"


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
    return db.reference(f"{USERS_REF}/{user_id}").get()


def user_exists(user_id: int) -> bool:
    return get_user(user_id) is not None


def create_user(
    user_id: int,
    full_name: str,
    phone_number: str,
    language: str,
    username: str = "",
) -> None:
    db.reference(f"{USERS_REF}/{user_id}").set(
        {
            "user_id": str(user_id),
            "full_name": full_name,
            "phone_number": phone_number,
            "username": username or "",
            "language": language,
            "created_at": _now_iso(),
        }
    )
    if username:
        db.reference(f"usernames/{username.lstrip('@').lower()}").set(str(user_id))
    clean_phone = normalize_phone(phone_number)
    if clean_phone:
        db.reference(f"phones/{clean_phone}").set(str(user_id))


def update_user_language(user_id: int, language: str) -> None:
    db.reference(f"{USERS_REF}/{user_id}/language").set(language)


def get_user_language(user_id: int) -> str:
    lang = db.reference(f"{USERS_REF}/{user_id}/language").get()
    return lang if lang in ("uz", "ru", "kk", "en") else "uz"


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 9:
        digits = "998" + digits
    return digits


def find_user_by_phone(phone: str) -> Optional[dict]:
    clean = normalize_phone(phone)
    if not clean:
        return None
    uid = db.reference(f"phones/{clean}").get()
    if uid:
        user = get_user(uid)
        if user:
            return user
    all_users = get_all_users()
    for _, udata in all_users.items():
        if normalize_phone(udata.get("phone_number", "")) == clean:
            return udata
    return None


def find_user_by_username(username: str) -> Optional[dict]:
    username = username.lstrip("@").lower()
    if not username:
        return None
    uid = db.reference(f"usernames/{username}").get()
    if uid:
        user = get_user(uid)
        if user:
            return user
    all_users = db.reference(USERS_REF).get() or {}
    for _, udata in all_users.items():
        if str(udata.get("username", "")).lower() == username:
            return udata
    return None


def get_all_users() -> dict:
    return db.reference(USERS_REF).get() or {}


# ==================== DEBTS ====================

def create_debt(
    debtor_id: Optional[int],
    creditor_id: Optional[int],
    amount: float,
    currency: str,
    status: str = "pending",
    phone: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    debt_id = str(uuid.uuid4())
    debt_data = {
        "debt_id": debt_id,
        "debtor_id": debtor_id,
        "creditor_id": creditor_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "description": description or "",
        "last_notified_at": _now_iso(),
        "created_at": _now_iso(),
    }
    if phone:
        debt_data["phone"] = phone
    db.reference(f"{DEBTS_REF}/{debt_id}").set(debt_data)
    return debt_id


def get_debt(debt_id: str) -> Optional[dict]:
    debt = db.reference(f"{DEBTS_REF}/{debt_id}").get()
    if debt:
        debt["debt_id"] = debt_id
    return debt


def update_debt_status(debt_id: str, status: str) -> None:
    db.reference(f"{DEBTS_REF}/{debt_id}/status").set(status)


def update_debt_amount(debt_id: str, new_amount: float) -> None:
    db.reference(f"{DEBTS_REF}/{debt_id}/amount").set(new_amount)


def update_debt_notified(debt_id: str) -> None:
    db.reference(f"{DEBTS_REF}/{debt_id}/last_notified_at").set(_now_iso())


def set_debt_debtor(debt_id: str, debtor_id: int) -> None:
    db.reference(f"{DEBTS_REF}/{debt_id}/debtor_id").set(debtor_id)


def set_debt_creditor(debt_id: str, creditor_id: int) -> None:
    db.reference(f"{DEBTS_REF}/{debt_id}/creditor_id").set(creditor_id)


def delete_debt(debt_id: str) -> None:
    db.reference(f"{DEBTS_REF}/{debt_id}").delete()


def get_all_debts() -> dict:
    return db.reference(DEBTS_REF).get() or {}


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

def add_history(
    debt_id: str,
    from_user: int,
    to_user: int,
    type_: str,
    amount: float,
    currency: str,
    status: str = "confirmed",
) -> str:
    trans_id = str(uuid.uuid4())
    db.reference(f"{HISTORY_REF}/{trans_id}").set(
        {
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
    )
    return trans_id


def get_history_by_user(user_id: int) -> list:
    all_history = db.reference(HISTORY_REF).get() or {}
    result = []
    for trans_id, h in all_history.items():
        if str(h.get("from_user")) == str(user_id) or str(h.get("to_user")) == str(user_id):
            h = dict(h)
            h["trans_id"] = trans_id
            result.append(h)
    result.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return result


# ==================== ADMIN STATISTIKA ====================

def get_stats() -> dict:
    users = get_all_users()
    debts = get_all_debts()
    active_debts = [d for d in debts.values() if d.get("status") == "active"]
    total_uzs = sum(d.get("amount", 0) for d in active_debts if d.get("currency") == "UZS")
    total_usd = sum(d.get("amount", 0) for d in active_debts if d.get("currency") == "USD")
    return {
        "total_users": len(users),
        "active_debts_count": len(active_debts),
        "total_uzs": total_uzs,
        "total_usd": total_usd,
    }
