# O'rnatish: pip install aiogram aiosqlite
# Ishga tushirish: python bot_all.py

import asyncio
import datetime
import aiosqlite

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

BOT_TOKEN = "8555630882:AAGqeRiq1jU6W-fqjr_soJTH0168B7Iclsg"
ADMIN_ID = 1999635628
VPN_LINK = "https://hirbilon.net/open?sub_url=https://g3.hirbilon.net:443/yessub/p5ln8k1qld9nf0sa"
SBP_LINK = "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111"
TON_WALLET = "UQCe2TzE4kDy9dTgiESd_xCTX9FLrVGm29JX-RqaYKhEr0kT"
USDT_WALLET = "TWJwXNwMYrGXcnbzs2Q6YeBWm4i8XkBHoh"
SUPPORT = "@Husnijan_Axi"
TRIAL_DAYS = 3
TARIFFS = {
    "1": {"name": "1 месяц", "price": 75},
    "3": {"name": "3 месяца", "price": 200},
    "6": {"name": "6 месяцев", "price": 350},
    "12": {"name": "12 месяцев", "price": 500},
}
REF_BONUS = 10
PAYMENT_REF_BONUS = 30
MIN_WITHDRAW = 200
DB = "vpn.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, referrer INTEGER,
            balance INTEGER DEFAULT 0, trial_start TEXT, trial_end TEXT, paid INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tariff TEXT,
            amount INTEGER, method TEXT, screenshot TEXT, status TEXT DEFAULT 'pending')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS withdraws (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            amount INTEGER, wallet TEXT, status TEXT DEFAULT 'pending')""")
        await db.commit()

async def add_user(user_id, username, referrer=None):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not await cursor.fetchone():
            t = datetime.datetime.now()
            await db.execute(
                "INSERT INTO users (user_id, username, referrer, trial_start, trial_end) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, referrer, t.isoformat(), (t + datetime.timedelta(days=TRIAL_DAYS)).isoformat()))
            await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cursor.fetchone()

async def get_user_referrer(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT referrer FROM users WHERE user_id=?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def add_payment(user_id, tariff, amount, method, screenshot=None):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO payments (user_id, tariff, amount, method, screenshot) VALUES (?, ?, ?, ?, ?)",
            (user_id, tariff, amount, method, screenshot))
        await db.commit()

async def get_pending_payments():
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM payments WHERE status='pending'")
        return await cursor.fetchall()

async def get_payment_by_id(payment_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        return await cursor.fetchone()

async def confirm_payment(payment_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payments SET status='confirmed' WHERE id=?", (payment_id,))
        await db.commit()

async def reject_payment(payment_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
        await db.commit()

async def activate_vpn(user_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET paid=1 WHERE user_id=?", (user_id,))
        await db.commit()

async def add_balance(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def get_balance(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0

async def create_withdraw(user_id, amount, wallet):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO withdraws (user_id, amount, wallet) VALUES (?, ?, ?)", (user_id, amount, wallet))
        await db.commit()

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Купить VPN")],
        [KeyboardButton(text="💰 Тарифы"), KeyboardButton(text="👥 Рефералы")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📤 Вывести деньги")],
        [KeyboardButton(text="📖 Инструкция"), KeyboardButton(text="🆘 Поддержка")]
    ], resize_keyboard=True)

def tariffs_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for key, tariff in TARIFFS.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{tariff['name']} — {tariff['price']} ₽", callback_data=f"tariff_{key}")])
    return kb

def payment_methods_keyboard(tariff_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 СБП", callback_data=f"sbp_{tariff_id}")],
        [InlineKeyboardButton(text="💎 TON", callback_data=f"ton_{tariff_id}")],
        [InlineKeyboardButton(text="💎 USDT", callback_data=f"usdt_{tariff_id}")]
    ])

def payment_admin_kb(payment_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{payment_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{payment_id}")
    ]])

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="💳 Платежи", callback_data="payments")],
        [InlineKeyboardButton(text="📤 Выводы", callback_data="withdraws")]
    ])

class PaymentStates(StatesGroup):
    waiting_screenshot = State()

class WithdrawStates(StatesGroup):
    waiting_wallet = State()
    waiting_amount = State()

router = Router()

def is_admin(user_id):
    return user_id == ADMIN_ID

@router.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    referrer = None
    if len(args) > 1:
        try: referrer = int(args[1])
        except: pass
    await add_user(message.from_user.id, message.from_user.username, referrer)
    user = await get_user(message.from_user.id)
    trial_end = datetime.datetime.fromisoformat(user[5])
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        f"🎁 Вам доступен бесплатный VPN на {TRIAL_DAYS} дня(дней).\n"
        f"Активен до: {trial_end.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Нажмите кнопку ниже, чтобы подключить VPN.",
        reply_markup=main_menu())

@router.message(F.text == "🛒 Купить VPN")
async def buy_vpn(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await add_user(message.from_user.id, message.from_user.username)
        user = await get_user(message.from_user.id)
    now = datetime.datetime.now()
    trial_end = datetime.datetime.fromisoformat(user[5])
    if user[6]:
        await message.answer(f"✅ Ваша подписка VPN активна!\n\n🔗 Ссылка для подключения:\n{VPN_LINK}", reply_markup=main_menu())
    elif now < trial_end:
        await message.answer(
            f"🎁 У вас активен пробный период!\nДействует до: {trial_end.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔗 Ссылка для подключения:\n{VPN_LINK}\n\nВыберите тариф:", reply_markup=tariffs_keyboard())
    else:
        await message.answer("❌ У вас нет активной подписки VPN.\n\nВыберите тариф:", reply_markup=tariffs_keyboard())

@router.message(F.text == "💰 Тарифы")
async def show_tariffs(message: types.Message):
    text = "📋 <b>Доступные тарифы:</b>\n\n"
    for key, tariff in TARIFFS.items():
        text += f"• {tariff['name']} — <b>{tariff['price']} ₽</b>\n"
    text += "\nДля покупки нажмите «🛒 Купить VPN»."
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())

@router.message(F.text == "👥 Рефералы")
async def referral_info(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (user_id,))
        ref_count = (await cursor.fetchone())[0]
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={link}&text=Подключайся%20к%20VPN!")
    ]])
    await message.answer(
        f"👥 <b>Реферальная программа</b>\n\nПриглашайте друзей и получайте бонусы!\n\n"
        f"🎁 За каждого зарегистрированного друга: <b>{REF_BONUS} ₽</b>\n"
        f"💳 Если друг оплатит подписку: <b>{PAYMENT_REF_BONUS} ₽</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{link}</code>\n\n"
        f"📊 Приглашено друзей: <b>{ref_count}</b>",
        parse_mode="HTML", reply_markup=kb)

@router.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    balance = await get_balance(message.from_user.id)
    await message.answer(
        f"💰 <b>Ваш баланс:</b> {balance} ₽\n\nМинимальная сумма вывода: <b>{MIN_WITHDRAW} ₽</b>",
        parse_mode="HTML", reply_markup=main_menu())

@router.message(F.text == "📤 Вывести деньги")
async def withdraw_start(message: types.Message, state: FSMContext):
    balance = await get_balance(message.from_user.id)
    if balance < MIN_WITHDRAW:
        await message.answer(f"❌ Недостаточно средств.\nБаланс: <b>{balance} ₽</b>\nМинимум: <b>{MIN_WITHDRAW} ₽</b>",
            parse_mode="HTML", reply_markup=main_menu())
        return
    await state.set_state(WithdrawStates.waiting_wallet)
    await message.answer(f"💸 <b>Вывод средств</b>\n\nБаланс: <b>{balance} ₽</b>\n\nВведите адрес кошелька (TON или USDT TRC-20):", parse_mode="HTML")

@router.message(WithdrawStates.waiting_wallet)
async def withdraw_wallet(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    await state.set_state(WithdrawStates.waiting_amount)
    balance = await get_balance(message.from_user.id)
    await message.answer(f"Введите сумму для вывода (максимум: {balance} ₽):")

@router.message(WithdrawStates.waiting_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    try: amount = int(message.text)
    except: await message.answer("❌ Пожалуйста, введите число."); return
    balance = await get_balance(message.from_user.id)
    if amount > balance: await message.answer(f"❌ Недостаточно средств. Баланс: {balance} ₽"); return
    if amount < MIN_WITHDRAW: await message.answer(f"❌ Минимальная сумма: {MIN_WITHDRAW} ₽"); return
    data = await state.get_data()
    wallet = data["wallet"]
    await create_withdraw(message.from_user.id, amount, wallet)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, message.from_user.id))
        await db.commit()
    await message.bot.send_message(ADMIN_ID,
        f"💸 <b>Новая заявка на вывод!</b>\n\n👤 @{message.from_user.username} (ID: {message.from_user.id})\n"
        f"💰 Сумма: <b>{amount} ₽</b>\n💳 Кошелёк: <code>{wallet}</code>", parse_mode="HTML")
    await state.clear()
    await message.answer(f"✅ Заявка принята!\nСумма: <b>{amount} ₽</b>\nКошелёк: <code>{wallet}</code>\n\nОбработаем в ближайшее время.",
        parse_mode="HTML", reply_markup=main_menu())

@router.message(F.text == "📖 Инструкция")
async def instruction(message: types.Message):
    await message.answer(
        "📖 <b>Инструкция по подключению VPN</b>\n\n"
        "1️⃣ Нажмите «🛒 Купить VPN»\n2️⃣ Выберите тариф\n3️⃣ Выберите способ оплаты\n"
        "4️⃣ Произведите оплату\n5️⃣ Отправьте скриншот чека\n6️⃣ Дождитесь подтверждения\n\n"
        "📱 <b>Приложения:</b>\n• iOS: «V2Box» или «Shadowrocket» (App Store)\n• Android: «V2RayNG» (Play Market)\n\n"
        f"❓ По вопросам: {SUPPORT}", parse_mode="HTML", reply_markup=main_menu())

@router.message(F.text == "🆘 Поддержка")
async def support(message: types.Message):
    await message.answer(f"🆘 <b>Поддержка</b>\n\nОбратитесь к администратору:\n\n👤 {SUPPORT}",
        parse_mode="HTML", reply_markup=main_menu())

@router.callback_query(F.data.startswith("tariff_"))
async def tariff_selected(callback: types.CallbackQuery):
    tariff_id = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_id)
    if not tariff: await callback.answer("Тариф не найден"); return
    await callback.message.edit_text(
        f"✅ Вы выбрали: <b>{tariff['name']}</b>\n💰 Стоимость: <b>{tariff['price']} ₽</b>\n\nВыберите способ оплаты:",
        parse_mode="HTML", reply_markup=payment_methods_keyboard(tariff_id))
    await callback.answer()

@router.callback_query(F.data.startswith("sbp_"))
async def payment_sbp(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_id)
    await state.update_data(tariff_id=tariff_id, method="sbp", amount=tariff["price"])
    await state.set_state(PaymentStates.waiting_screenshot)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Перейти к оплате через СБП", url=SBP_LINK)]])
    await callback.message.edit_text(
        f"💳 <b>Оплата через СБП</b>\n\nСумма: <b>{tariff['price']} ₽</b>\n\n"
        f"Нажмите кнопку ниже для перехода к оплате.\n\nПосле оплаты отправьте <b>скриншот чека</b>:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("ton_"))
async def payment_ton(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_id)
    await state.update_data(tariff_id=tariff_id, method="ton", amount=tariff["price"])
    await state.set_state(PaymentStates.waiting_screenshot)
    await callback.message.edit_text(
        f"💎 <b>Оплата через TON</b>\n\nСумма: <b>{tariff['price']} ₽</b> (в эквиваленте TON)\n\n"
        f"📬 Адрес TON кошелька:\n<code>{TON_WALLET}</code>\n\nПосле оплаты отправьте <b>скриншот чека</b>:",
        parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("usdt_"))
async def payment_usdt(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_id)
    await state.update_data(tariff_id=tariff_id, method="usdt", amount=tariff["price"])
    await state.set_state(PaymentStates.waiting_screenshot)
    await callback.message.edit_text(
        f"💎 <b>Оплата через USDT (TRC-20)</b>\n\nСумма: <b>{tariff['price']} ₽</b> (в эквиваленте USDT)\n\n"
        f"📬 Адрес USDT кошелька:\n<code>{USDT_WALLET}</code>\n\nПосле оплаты отправьте <b>скриншот чека</b>:",
        parse_mode="HTML")
    await callback.answer()

@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tariff = TARIFFS.get(data["tariff_id"])
    photo_id = message.photo[-1].file_id
    await add_payment(message.from_user.id, data["tariff_id"], data["amount"], data["method"], photo_id)
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT id FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 1", (message.from_user.id,))
        payment_id = (await cursor.fetchone())[0]
    methods = {"sbp": "СБП", "ton": "TON", "usdt": "USDT (TRC-20)"}
    await message.bot.send_photo(ADMIN_ID, photo=photo_id,
        caption=(f"💳 <b>Новая заявка на оплату!</b>\n\n🆔 ID: #{payment_id}\n"
            f"👤 @{message.from_user.username} (ID: {message.from_user.id})\n"
            f"📦 Тариф: {tariff['name']}\n💰 Сумма: {data['amount']} ₽\n"
            f"💳 Способ: {methods.get(data['method'], data['method'])}"),
        parse_mode="HTML", reply_markup=payment_admin_kb(payment_id))
    await state.clear()
    await message.answer("✅ <b>Чек отправлен!</b>\n\nАдминистратор активирует подписку в течение 5–15 минут.",
        parse_mode="HTML", reply_markup=main_menu())

@router.message(PaymentStates.waiting_screenshot)
async def wrong_screenshot(message: types.Message):
    await message.answer("📸 Пожалуйста, отправьте <b>фото</b> чека об оплате.", parse_mode="HTML")

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): await message.answer("❌ У вас нет доступа."); return
    await message.answer("👨‍💼 <b>Панель администратора</b>\n\nВыберите раздел:", parse_mode="HTML", reply_markup=admin_panel_kb())

@router.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("Нет доступа", show_alert=True); return
    async with aiosqlite.connect(DB) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        paid = (await (await db.execute("SELECT COUNT(*) FROM users WHERE paid=1")).fetchone())[0]
        pending = (await (await db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")).fetchone())[0]
        confirmed = (await (await db.execute("SELECT COUNT(*) FROM payments WHERE status='confirmed'")).fetchone())[0]
        income = (await (await db.execute("SELECT SUM(amount) FROM payments WHERE status='confirmed'")).fetchone())[0] or 0
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n👤 Всего пользователей: <b>{total}</b>\n✅ С активной подпиской: <b>{paid}</b>\n\n"
        f"⏳ Ожидают подтверждения: <b>{pending}</b>\n✅ Подтверждённых: <b>{confirmed}</b>\n💰 Доход: <b>{income} ₽</b>",
        parse_mode="HTML", reply_markup=admin_panel_kb())
    await callback.answer()

@router.callback_query(F.data == "payments")
async def show_payments(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("Нет доступа", show_alert=True); return
    payments = await get_pending_payments()
    text = "💳 Ожидающих платежей нет." if not payments else f"💳 <b>Ожидающих платежей: {len(payments)}</b>\n\nЧеки отправлены отдельными сообщениями."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_kb())
    await callback.answer()

@router.callback_query(F.data == "withdraws")
async def show_withdraws(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("Нет доступа", show_alert=True); return
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM withdraws WHERE status='pending'")
        withdraws = await cursor.fetchall()
    if not withdraws:
        await callback.message.edit_text("📤 Заявок на вывод нет.", reply_markup=admin_panel_kb())
    else:
        text = f"📤 <b>Заявки на вывод: {len(withdraws)}</b>\n\n"
        for w in withdraws:
            text += f"🆔 #{w[0]} | 👤 ID: {w[1]} | 💰 {w[2]} ₽ | 💳 <code>{w[3]}</code>\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_payment_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("Нет доступа", show_alert=True); return
    payment_id = int(callback.data.split("_")[1])
    payment = await get_payment_by_id(payment_id)
    if not payment: await callback.answer("Платёж не найден", show_alert=True); return
    user_id = payment[1]
    tariff = TARIFFS.get(payment[2], {})
    await confirm_payment(payment_id)
    await activate_vpn(user_id)
    referrer_id = await get_user_referrer(user_id)
    if referrer_id:
        await add_balance(referrer_id, PAYMENT_REF_BONUS)
        try: await callback.bot.send_message(referrer_id, f"🎉 Ваш друг оплатил подписку! Вам начислено <b>{PAYMENT_REF_BONUS} ₽</b>.", parse_mode="HTML")
        except: pass
    try: await callback.bot.send_message(user_id,
        f"✅ <b>Платёж подтверждён!</b>\n\n📦 Тариф: {tariff.get('name', '')}\n\n🔗 Ссылка для подключения:\n{VPN_LINK}", parse_mode="HTML")
    except: pass
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>ПОДТВЕРЖДЁН</b>", parse_mode="HTML")
    await callback.answer("✅ Платёж подтверждён!")

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): await callback.answer("Нет доступа", show_alert=True); return
    payment_id = int(callback.data.split("_")[1])
    payment = await get_payment_by_id(payment_id)
    if not payment: await callback.answer("Платёж не найден", show_alert=True); return
    await reject_payment(payment_id)
    try: await callback.bot.send_message(payment[1], "❌ <b>Ваш платёж отклонён.</b>\n\nПо вопросам обратитесь в поддержку.", parse_mode="HTML")
    except: pass
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЁН</b>", parse_mode="HTML")
    await callback.answer("❌ Платёж отклонён!")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Админ панель")
    ])
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
