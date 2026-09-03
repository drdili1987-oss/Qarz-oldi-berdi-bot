import logging
from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database as db
from config import REMINDER_CHECK_INTERVAL_HOURS, REMINDER_INTERVAL_DAYS
from locales.texts import TEXTS

logger = logging.getLogger(__name__)

async def _check_and_notify(bot: Bot) -> None:
    debts = db.get_all_debts()
    now = datetime.now(timezone.utc)
    
    # Faqat kunni o'zini solishtirish uchun
    now_date = now.date()

    for debt_id, debt in debts.items():
        if debt.get("status") != "active":
            continue

        debtor_id = debt.get("debtor_id")
        creditor_id = debt.get("creditor_id")
        if not debtor_id or not creditor_id:
            continue

        # Oxirgi marta qachon ogohlantirilgani
        last_notified = debt.get("last_notified_at")
        last_dt = None
        if isinstance(last_notified, str):
            try:
                last_dt = datetime.fromisoformat(last_notified).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        
        # Agar bugun ogohlantirilgan bo'lsa, o'tkazib yuboramiz
        if last_dt and last_dt.date() == now_date:
            continue

        due_date_str = debt.get("due_date")
        should_notify = False
        
        if due_date_str:
            # Muddat bor bo'lsa
            try:
                due_date_obj = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_left = (due_date_obj - now_date).days
                
                # Eslatma kunlari: 10, 3, 1, 0, yoki muddat o'tib ketgan bo'lsa (< 0) har kuni
                if days_left in [10, 3, 1, 0] or days_left < 0:
                    should_notify = True
            except ValueError:
                should_notify = False
        else:
            # Muddat yo'q bo'lsa, eski mantiq bo'yicha (har REMINDER_INTERVAL_DAYS kunda)
            if last_dt:
                days_passed = (now_date - last_dt.date()).days
                if days_passed >= REMINDER_INTERVAL_DAYS:
                    should_notify = True
            else:
                should_notify = True

        if not should_notify:
            continue

        creditor = db.get_user(creditor_id)
        if not creditor:
            continue

        lang = db.get_user_language(debtor_id)
        
        # Muddat haqida qo'shimcha matn
        due_text = f"\n⏳ Qaytarish muddati: <b>{due_date_str}</b>" if due_date_str else ""
        
        text = TEXTS[lang]["debt_reminder"].format(
            name=creditor["full_name"], amount=db.format_amount(debt["amount"]), currency=debt["currency"]
        ) + due_text

        try:
            await bot.send_message(int(debtor_id), text)
            db.update_debt_notified(debt_id)
        except Exception as exc:
            logger.warning("Eslatma yuborilmadi (debt_id=%s): %s", debt_id, exc)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _check_and_notify,
        trigger=IntervalTrigger(hours=REMINDER_CHECK_INTERVAL_HOURS),
        args=(bot,),
        id="debt_reminder_job",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    return scheduler
