import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()


async def main():
    print("=" * 60)
    print("      QARZ BOT - TELEGRAM USERBOTGA KIRISH")
    print("=" * 60)

    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()

    if not api_id or not api_hash:
        print("\nDIQQAT: TELEGRAM_API_ID yoki TELEGRAM_API_HASH .env faylida topilmadi.")
        print("Ularni https://my.telegram.org saytidan olishingiz mumkin.\n")
        api_id = input("Telegram API ID ni kiriting: ").strip()
        api_hash = input("Telegram API HASH ni kiriting: ").strip()

        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nTELEGRAM_API_ID={api_id}\nTELEGRAM_API_HASH={api_hash}\n")
        print(".env fayliga saqlandi!\n")

    phone = input("Userbot sifatida ulanadigan telefon raqamingizni kiriting (+998901234567): ").strip()

    client = TelegramClient("userbot", int(api_id), api_hash)
    await client.start(phone=phone)

    me = await client.get_me()
    print("\n" + "=" * 60)
    print("TABRIKLAYMIZ! Userbot muvaffaqiyatli ulandi!")
    print(f"Akkaunt: {me.first_name} (@{me.username or 'username mavjud emas'})")
    print("Sessiya fayli yaratildi: userbot.session")
    print("Endi bot har safar ishga tushganda shaxsiy chatlarga avtomatik yoza oladi!")
    print("=" * 60)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
