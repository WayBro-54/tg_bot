
import sys
import os
from dotenv import load_dotenv

from tg_bot import init_db

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import html
import uuid
import json
import time
from typing import List, Optional, Dict, Any

from aiogram.dispatcher import FSMContext
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove,
    InputMediaPhoto, InputMediaVideo, ParseMode
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ✅ КОНСТАНТЫ
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MOD_CHAT_ID = int(os.getenv("MOD_CHAT_ID"))
MAX_PHOTOS = 10
AGENT_CONTACT = "@Ultanovr"

CATEGORIES = {
    "1": "Услуги",
    "2": "Пункты выдачи",
    "3": "Бьюти",
    "4": "Розница",
    "5": "Производство",
    "6": "Общепит",
    "7": "Опт",
    "8": "IT",
}

# ✅ ЛОГИРОВАНИЕ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ БОТ И ДИСПЕТЧЕР
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ✅ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
pending_submissions: Dict[str, Dict[str, Any]] = {}
mod_rejection_state: Dict[int, str] = {}
referral_data: Dict[int, Dict] = {}
referral_invites: Dict[int, list] = {}

# ✅ FSM STATES
class SellStates(StatesGroup):
    SELL_TITLE = State()
    SELL_PROFIT = State()
    SELL_MARKETING = State()
    SELL_EMPLOYEES = State()
    SELL_PREMISES = State()
    SELL_INCLUDED = State()
    SELL_EXTRA = State()
    SELL_TABLE = State()
    SELL_PHOTOS = State()
    SELL_CITY = State()
    SELL_ADDRESS = State()
    SELL_PRICE = State()
    SELL_CATEGORY = State()
    SELL_AGENT_CONFIRM = State()
    SELL_CONTACT_AGENT = State()
    SELL_PREVIEW = State()

class BuyStates(StatesGroup):
    BUY_BUDGET = State()
    BUY_CITY = State()
    BUY_CATEGORY = State()
    BUY_EXPERIENCE = State()
    BUY_PHONE = State()
    BUY_WHEN_CONTACT = State()

class ModStates(StatesGroup):
    MOD_REASON = State()

# ✅ ФУНКЦИИ ПОМОЩНИКИ
def escape_html(text: str) -> str:
    """Экранирует HTML для Telegram"""
    return html.escape(str(text))

def format_number(value) -> str:
    """Форматирует число с пробелами"""
    try:
        num = int(value)
        return f"{num:,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(value)

def safe_int(value: str) -> Optional[int]:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except:
        return None

def get_price_category(price_str: str) -> str:
    """Определяет категорию цены"""
    try:
        price = int(price_str)
        if price <= 500000:
            return "#До500тыс"
        elif price <= 1000000:
            return "#До1млн"
        elif price <= 1500000:
            return "#До1_5млн"
        elif price <= 2000000:
            return "#До2млн"
        elif price <= 3000000:
            return "#До3млн"
        elif price <= 5000000:
            return "#До5млн"
        else:
            return "#Выше5млн"
    except (ValueError, TypeError):
        return ""

def is_subscribed_status(status: str) -> bool:
    """Проверяет, является ли статус подпиской"""
    return status not in ("left", "kicked")

async def check_subscription(user_id: int) -> bool:
    """Проверяет подписку пользователя в канале"""
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        is_subscribed = is_subscribed_status(member.status)
        logger.info(f"User {user_id} subscription check: status={member.status}, subscribed={is_subscribed}")
        return is_subscribed
    except Exception as e:
        logger.exception(f"Ошибка при проверке подписки для {user_id}: {e}")
        return False

# ✅ КЛАВИАТУРЫ
def make_start_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Продать", callback_data="start:sell"))
    kb.add(InlineKeyboardButton("Купить", callback_data="start:buy"))
    return kb

def make_subscribe_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Подписаться", url="https://t.me/goodbiz54"))
    kb.add(InlineKeyboardButton("Проверить подписку", callback_data="check_sub"))
    return kb

def make_ready_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Информацию подготовил(а)", callback_data="info:ready"))
    return kb

def make_back_restart_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
        InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
    )
    return kb

def make_restart_only_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart"))
    return kb

def make_skip_back_restart_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⏭️ Пропустить", callback_data="sell:skip_current"))
    kb.add(
        InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
        InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
    )
    return kb

def make_done_back_restart_keyboard(done_callback: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("✅ Готово", callback_data=done_callback))
    kb.add(
        InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
        InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
    )
    return kb

def make_categories_keyboard(prefix="cat") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for i in range(1, 9):
        cat_name = CATEGORIES.get(str(i), f"Категория {i}")
        kb.insert(InlineKeyboardButton(cat_name, callback_data=f"{prefix}:{i}"))
    return kb

def make_confirm_agent_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Да", callback_data="sell:agree_agent"),
        InlineKeyboardButton("Нет", callback_data="sell:no_agent")
    )
    return kb

def make_mod_inline(local_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Опубликовать", callback_data=f"mod:publish:{local_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"mod:reject:{local_id}")
    )
    return kb

# =======================
# Команды
# =======================


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    """
    Начальный экран с поддержкой реферальных ссылок.
    Формат: /start ref_USER_ID
    """
    try:
        user_id = message.from_user.id
        args = message.get_args()

        # ✅ УБИРАЕМ КНОПКИ С КЛАВИАТУРЫ
        await message.answer(
            "Проверка рефералов...",
            reply_markup=ReplyKeyboardRemove()
        )

        # ✅ Обработка реферальной ссылки
        if args and args.startswith("ref_"):
            referrer_id = args.replace("ref_", "")
            try:
                referrer_id = int(referrer_id)

                if referrer_id == user_id:
                    await message.answer(
                        "Вы не можете пригласить сами себя! 😄",
                        reply_markup=make_start_keyboard()
                    )
                    return  # ✅ ДОБАВЛЕНО: выход после обработки

                if user_id in referral_data:
                    await message.answer(
                        "Вы уже помогли кому-то получить бонус! 🎁\n\n"
                        "Хотите разместить своё объявление?",
                        reply_markup=make_start_keyboard()
                    )
                    return  # ✅ ДОБАВЛЕНО: выход после обработки

                subscribed = await check_subscription(user_id)
                if not subscribed:
                    await message.answer(
                        "❌ Чтобы помочь другу, сначала подпишитесь на канал!\n\n"
                        "После подписки нажмите /start ещё раз.",
                        reply_markup=make_subscribe_keyboard()
                    )
                    return  # ✅ ДОБАВЛЕНО: выход после обработки

                # ✅ Регистрируем реферальную связь
                referral_data[user_id] = {"invited_by": referrer_id}

                if referrer_id not in referral_invites:
                    referral_invites[referrer_id] = []
                referral_invites[referrer_id].append(user_id)

                count = len(referral_invites[referrer_id])

                # ✅ Уведомляем реферера о новом приглашении
                try:
                    await bot.send_message(
                        referrer_id,
                        f"✅ Ваш друг подписался на канал и нажал START!\n"
                        f"Приглашено: {count}/5"
                    )

                    # ✅ Если достигнуто 5 приглашений
                    if count >= 5:
                        await bot.send_message(
                            referrer_id,
                            "🎉 Поздравляем! Вы пригласили 5 друзей.\n"
                            "Ваше объявление отправлено на модерацию!"
                        )

                        try:
                            state_proxy = dp.current_state(chat=referrer_id, user=referrer_id)

                            if state_proxy is None:
                                logger.warning(f"⚠️ state_proxy is None для пользователя {referrer_id}")
                                await bot.send_message(
                                    referrer_id,
                                    "Пожалуйста, оставьте контакт для связи (телефон или @username):"
                                )
                            else:
                                user_data = await state_proxy.get_data()

                                if user_data.get("waiting_for_invites"):
                                    if not user_data.get("contact"):
                                        await bot.send_message(
                                            referrer_id,
                                            "Пожалуйста, оставьте контакт для связи (телефон или @username):"
                                        )
                                        await state_proxy.set_state(SellStates.SELL_CONTACT_AGENT)
                                    else:
                                        await finalize_and_send_to_moderation(
                                            referrer_id,
                                            state_proxy,
                                            invited=True
                                        )

                        except Exception as e:
                            logger.exception(f"❌ Ошибка при обработке state_proxy для {referrer_id}: {e}")
                            await bot.send_message(
                                referrer_id,
                                "Произошла ошибка при обновлении статуса. Попробуйте позже."
                            )

                except Exception as e:
                    logger.exception(f"❌ Не удалось уведомить реферера {referrer_id}: {e}")

                # ✅ Отправляем сообщение новому пользователю
                await message.answer(
                    "🎉 Спасибо! Вы помогли другу получить бонус!\n\n"
                    "Теперь вы можете:\n"
                    "• Продать свой бизнес\n"
                    "• Найти готовый бизнес для покупки",
                    reply_markup=make_start_keyboard()
                )
                return  # ✅ ДОБАВЛЕНО: выход после обработки реферальной ссылки

            except ValueError:
                logger.warning(f"❌ Некорректный ID реферера: {args}")
                pass  # Продолжаем к обычному старту

        # ✅ Обычный старт (без реферальной ссылки)
        kb = make_start_keyboard()
        await message.answer(
            "Рады приветствовать вас! Вы хотите продать или купить бизнес?",
            reply_markup=kb
        )

    except Exception as e:
        logger.exception("Ошибка в /start: %s", e)
        await message.reply("Произошла ошибка при обработке /start.")

@dp.message_handler(commands=["reset"])
async def cmd_reset(message: types.Message, state: FSMContext):
    """
    Сброс FSM и данных.
    """
    try:
        await state.finish()
        await message.answer("Данные сброшены. Вы можете начать заново /start.")
    except Exception as e:
        logger.exception("Ошибка /reset: %s", e)
        await message.reply("Не удалось сбросить данные.")


# =======================
# Обработчики навигации: Назад Начать сначала
# =======================


@dp.callback_query_handler(lambda c: c.data == "nav:back", state="*")
async def nav_back_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' - дублирует предыдущий шаг"""
    try:
        current_state = await state.get_state()

        if not current_state:
            await callback_query.answer("Нет предыдущего шага")
            return

        # Получаем предыдущее состояние
        previous_state = await get_previous_state(current_state)

        if previous_state is None:
            await callback_query.answer("Это первый шаг, назад вернуться нельзя")
            return

        # ✅ ИЗМЕНЕНО: удаляем текущее сообщение с кнопками
        try:
            await bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id
            )
        except Exception:
            pass  # Если не удалось удалить - не страшно

        # Устанавливаем предыдущее состояние
        await previous_state.set()

        # ✅ ИЗМЕНЕНО: отправляем вопрос как новое сообщение (дублируем шаг)
        await send_state_question(
            callback_query.from_user.id,
            str(previous_state),
            state
        )

        await callback_query.answer("◀️ Возврат назад")

    except Exception as e:
        logger.exception("Ошибка в nav:back: %s", e)
        await callback_query.answer("Ошибка при возврате назад")


@dp.callback_query_handler(lambda c: c.data == "nav:restart", state="*")
async def nav_restart_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Начать сначала'"""
    try:
        await state.finish()

        kb = make_start_keyboard()
        await bot.send_message(
            callback_query.from_user.id,
            "🔄 Начинаем сначала!\n\nВы хотите продать или купить бизнес?",
            reply_markup=kb
        )

        await callback_query.answer("🔄 Перезапуск")

    except Exception as e:
        logger.exception("Ошибка в nav:restart: %s", e)
        await callback_query.answer("Ошибка при перезапуске")


@dp.callback_query_handler(lambda c: c.data == "sell:skip_current", state=SellStates)
async def sell_skip_current_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        current_state = await state.get_state()

        if current_state == "SellStates:SELL_MARKETING":
            await state.update_data(marketing="")
            await SellStates.SELL_EMPLOYEES.set()
            await bot.send_message(
                callback_query.from_user.id,
                "Заполните информацию про сотрудников (количество, ФОТ, стаж, должности):",
                reply_markup=make_back_restart_keyboard()
            )

        elif current_state == "SellStates:SELL_EXTRA":
            await state.update_data(extra="")
            await SellStates.SELL_TABLE.set()
            await bot.send_message(
                callback_query.from_user.id,
                "Прикрепите таблицу доходности (файл) или нажмите 'Пропустить'.",
                reply_markup=make_done_back_restart_keyboard("sell:photos_done")
            )

        await callback_query.answer("⏭️ Пропущено")

    except Exception as e:
        logger.exception("Ошибка в sell:skip_current: %s", e)
        await callback_query.answer("Ошибка при пропуске")



# =======================
# Обработка выбора Sell/Buy
# =======================

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("start:"))
async def process_start_choice(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    if action == "sell":
        # Проверяем подписку
        try:
            subscribed = await check_subscription(user_id)
            if not subscribed:
                # ✅ ИСПРАВЛЕНО: сохраняем действие в состояние
                await state.update_data(pending_action="sell")
                await callback_query.answer()
                await bot.send_message(
                    user_id,
                    "Чтобы выставить объявление, вы должны быть подписаны на канал @goodbiz54",
                    reply_markup=make_subscribe_keyboard()
                )
                return
            else:
                # Подписан — отправляем инструкцию
                text = (
                    "Отлично, тогда подготовьте следующую информацию:\n"

                    "1. Финансовую (Заполните <a href=\"https://docs.google.com/spreadsheets/d/1Vcn68ThO7yEWCQdLTZAsWVQc5c-V19B0wNLo0zIx_og/edit?gid=0#gid=0\">таблицу</a>)\n"
                    "2. Маркетинговую (если в вашем бизнесе это актуально)\n"
                    "3. Информацию о сотрудниках\n"
                    "4. Фото и видео бизнеса (хорошего качества, не кружки)\n"
                    "5. Оцените бизнеса (обычно 10–18 месяцев, в зависимости от бизнеса и имеющихся активов)\n"
                    "6. Информация по помещению (аренда/собственность, площадь, коммунальные платежи)\n"
                    "7. Состав бизнеса (материальные/нематериальные активы)\n"
                    "8. Доп. информация (история, причина продажи)\n\n"
                    "Нажмите 'Информацию подготовил(а)' когда будете готовы."
                )
                await bot.send_message(
                    user_id,
                    text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=make_ready_keyboard()
                )
                await callback_query.answer()
                return
        except Exception as e:
            logger.exception("Ошибка при ветке sell: %s", e)
            await callback_query.answer("Ошибка при проверке подписки. Попробуйте позже.")
            return

    elif action == "buy":
        # Проверяем подписку
        try:
            subscribed = await check_subscription(user_id)
            if not subscribed:
                # ✅ ИСПРАВЛЕНО: сохраняем действие в состояние
                await state.update_data(pending_action="buy")
                await callback_query.answer()
                await bot.send_message(
                    user_id,
                    "Чтобы отправить заявку, вы должны быть подписаны на канал @goodbiz54",
                    reply_markup=make_subscribe_keyboard()
                )
                return
            else:
                # Запускаем FSM опроса покупки
                await bot.send_message(user_id, "Отлично! Какой у вас бюджет?")
                await BuyStates.BUY_BUDGET.set()
                await callback_query.answer()
                return
        except Exception as e:
            logger.exception("Ошибка при ветке buy: %s", e)
            await callback_query.answer("Ошибка при проверке подписки. Попробуйте позже.")
            return

    else:
        await callback_query.answer("Неизвестное действие.")
# Кнопка "Проверить подписку"

# Кнопка "Проверить подписку"
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def process_check_sub(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    try:
        subscribed = await check_subscription(user_id)
        if subscribed:
            # ✅ ИСПРАВЛЕНО: получаем данные из состояния
            data = await state.get_data()
            action = data.get("pending_action")  # "sell" или "buy"

            if action == "sell":
                # Логика для продажи
                text = (
                    "Отлично, тогда подготовьте следующую информацию:\n"

                    "1. Финансовую (Заполните <a href=\"https://docs.google.com/spreadsheets/d/1Vcn68ThO7yEWCQdLTZAsWVQc5c-V19B0wNLo0zIx_og/edit?gid=0#gid=0\">таблицу</a>)\n"
                    "2. Маркетинговую (если в вашем бизнесе это актуально)\n"
                    "3. Информацию о сотрудниках\n"
                    "4. Фото и видео бизнеса (хорошего качества, не кружки)\n"
                    "5. Оцените бизнеса (обычно 10–18 месяцев, в зависимости от бизнеса и имеющихся активов)\n"
                    "6. Информация по помещению (аренда/собственность, площадь, коммунальные платежи)\n"
                    "7. Состав бизнеса (материальные/нематериальные активы)\n"
                    "8. Доп. информация (история, причина продажи)\n\n"
                    "Нажмите 'Информацию подготовил(а)' когда будете готовы."
                )
                await bot.send_message(
                    user_id,
                    text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=make_ready_keyboard()
                )

            elif action == "buy":
                # Логика для покупки
                await bot.send_message(user_id, "Отлично! Какой у вас бюджет?")
                await BuyStates.BUY_BUDGET.set()

            else:
                # Если действие не определено - показываем главное меню
                await bot.send_message(
                    user_id,
                    "Отлично — вы подписаны. Начинаем.\n\nВы хотите продать или купить бизнес?",
                    reply_markup=make_start_keyboard()
                )

            # ✅ Очищаем pending_action
            await state.update_data(pending_action=None)

        else:
            await bot.send_message(
                user_id,
                "Вы не подписаны. Пожалуйста, подпишитесь на канал.",
                reply_markup=make_subscribe_keyboard()
            )
        await callback_query.answer()
    except Exception as e:
        logger.exception("Ошибка check_sub: %s", e)
        await callback_query.answer("Ошибка при проверке. Попробуйте позже.")
# =======================
# Начало опроса Sell
# =======================
@dp.callback_query_handler(lambda c: c.data == "info:ready")
async def info_ready(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    try:
        # Инициализируем контекст
        await state.update_data(photos=[], photos_metas=[], video=None)
        await bot.send_message(user_id, "Тогда начнём с названия объявления:")
        await SellStates.SELL_TITLE.set()
        await callback_query.answer()
    except Exception as e:
        logger.exception("Ошибка info_ready: %s", e)
        await callback_query.answer("Не удалось начать опрос. Попробуйте позже.")


# =======================
# Навигация: Назад Начать сначала
# =======================

# Маппинг состояний для кнопки "Назад"
SELL_STATES_ORDER = [
    None,  # нет предыдущего для SELL_TITLE
    SellStates.SELL_TITLE,
    SellStates.SELL_PROFIT,
    SellStates.SELL_MARKETING,
    SellStates.SELL_EMPLOYEES,
    SellStates.SELL_PREMISES,
    SellStates.SELL_INCLUDED,
    SellStates.SELL_EXTRA,
    SellStates.SELL_TABLE,
    SellStates.SELL_PHOTOS,
    SellStates.SELL_CITY,
    SellStates.SELL_PRICE,
    SellStates.SELL_CATEGORY,
]

BUY_STATES_ORDER = [
    None,  # нет предыдущего для BUY_BUDGET
    BuyStates.BUY_BUDGET,
    BuyStates.BUY_CITY,
    BuyStates.BUY_CATEGORY,
    BuyStates.BUY_EXPERIENCE,
    BuyStates.BUY_PHONE,
    BuyStates.BUY_WHEN_CONTACT,
]


async def get_previous_state(current_state_name: str):
    """
    Возвращает предыдущее состояние для кнопки 'Назад'
    """
    # Определяем, в каком flow находимся
    if "SELL" in current_state_name:
        states_map = {
            "SellStates:SELL_PROFIT": SellStates.SELL_TITLE,
            "SellStates:SELL_MARKETING": SellStates.SELL_PROFIT,
            "SellStates:SELL_EMPLOYEES": SellStates.SELL_MARKETING,
            "SellStates:SELL_PREMISES": SellStates.SELL_EMPLOYEES,
            "SellStates:SELL_INCLUDED": SellStates.SELL_PREMISES,
            "SellStates:SELL_EXTRA": SellStates.SELL_INCLUDED,
            "SellStates:SELL_TABLE": SellStates.SELL_EXTRA,
            "SellStates:SELL_PHOTOS": SellStates.SELL_TABLE,
            "SellStates:SELL_CITY": SellStates.SELL_PHOTOS,
            "SellStates:SELL_PRICE": SellStates.SELL_CITY,
            "SellStates:SELL_CATEGORY": SellStates.SELL_PRICE,
            "SellStates:SELL_ADDRESS": SellStates.SELL_CITY,
        }
    elif "BUY" in current_state_name:
        states_map = {
            "BuyStates:BUY_CITY": BuyStates.BUY_BUDGET,
            "BuyStates:BUY_CATEGORY": BuyStates.BUY_CITY,
            "BuyStates:BUY_EXPERIENCE": BuyStates.BUY_CATEGORY,
            "BuyStates:BUY_PHONE": BuyStates.BUY_EXPERIENCE,
            "BuyStates:BUY_WHEN_CONTACT": BuyStates.BUY_PHONE,
        }
    else:
        return None

    return states_map.get(current_state_name)


async def send_state_question(user_id: int, state_name: str, state: FSMContext):
    """
    Отправляет вопрос для текущего состояния
    """
    data = await state.get_data()

    # SELL states
    if state_name == "SellStates:SELL_TITLE":
        await bot.send_message(user_id, "Тогда начнём с названия объявления:",
                               reply_markup=make_restart_only_keyboard())

    elif state_name == "SellStates:SELL_PROFIT":
        await bot.send_message(user_id, "Какая чистая прибыль? (Должна совпадать с таблицей)", reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_MARKETING":
        await bot.send_message(user_id, "Расскажите, как привлекаете клиентов (активные источники привлечения клиентов):",
                               reply_markup=make_skip_back_restart_keyboard())

    elif state_name == "SellStates:SELL_EMPLOYEES":
        await bot.send_message(user_id, "Заполните информацию про сотрудников (колличество, ФОТ, стаж, должности):",
                               reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_PREMISES":
        await bot.send_message(user_id, "Информация о помещении ((суб)аренда/собственность, площадь,коммунальные, ремонт и т.д.):",
                               reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_INCLUDED":
        await bot.send_message(user_id, "Что входит в стоимость бизнеса? (Материальное и не материальное, обеспечительный платеж, товарные остатки, ваше сопровождение и т.д.)", reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_EXTRA":
        await bot.send_message(user_id, "Дополнительная информация (история бизнеса, причина продажи, доп. инвестиции):",
                               reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_TABLE":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("⏭️ Пропустить", callback_data="sell:skip_table"))
        kb.add(
            InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
            InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
        )
        await bot.send_message(user_id, "Прикрепите таблицу доходности (файл) или нажмите 'Пропустить'.",
                               reply_markup=kb)

    elif state_name == "SellStates:SELL_PHOTOS":
        photos_count = len(data.get("photos", []))
        await bot.send_message(
            user_id,
            f"Прикрепите фото (до 10) и/или видео. Загружено фото: {photos_count}/{MAX_PHOTOS}\n\nПосле загрузки нажмите 'Готово'.",
            reply_markup=make_done_back_restart_keyboard("sell:photos_done")
        )

    elif state_name == "SellStates:SELL_CITY":
        await bot.send_message(user_id, "Напишите город с большой буквы (например: Новосибирск):",
                               reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_PRICE":
        await bot.send_message(user_id, "Укажите стоимость бизнеса целым числом (например: 1250700):",
                               reply_markup=make_back_restart_keyboard())

    elif state_name == "SellStates:SELL_CATEGORY":
        kb = make_categories_keyboard()
        kb.row(
            InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
            InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
        )
        await bot.send_message(user_id, "Выберите категорию:", reply_markup=kb)

    # BUY states
    elif state_name == "BuyStates:BUY_BUDGET":
        await bot.send_message(user_id, "Отлично! Какой у вас бюджет?", reply_markup=make_restart_only_keyboard())

    elif state_name == "BuyStates:BUY_CITY":
        await bot.send_message(user_id, "В каком городе? (Напишите с большой буквы)",
                               reply_markup=make_back_restart_keyboard())

    elif state_name == "BuyStates:BUY_CATEGORY":
        kb = make_categories_keyboard(prefix="buycat")
        kb.row(
            InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
            InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
        )
        await bot.send_message(user_id, "Какой вид деятельности рассматриваете? Выберите категорию:", reply_markup=kb)


    elif state_name == "BuyStates:BUY_EXPERIENCE":

        await bot.send_message(user_id, "Есть ли опыт в бизнесе? Расскажите кратко:",

                               reply_markup=make_back_restart_keyboard())


    elif state_name == "BuyStates:BUY_PHONE":

        await bot.send_message(user_id, "Номер телефона:", reply_markup=make_back_restart_keyboard())


    elif state_name == "BuyStates:BUY_WHEN_CONTACT":

        await bot.send_message(user_id, "Когда лучше связаться?", reply_markup=make_back_restart_keyboard())


# =======================
# Обработка вопросов продажи (по состояниям)
# =======================

@dp.message_handler(state=SellStates.SELL_TITLE, content_types=types.ContentTypes.TEXT)
async def sell_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await SellStates.SELL_PROFIT.set()
    await message.answer(
        "Какая чистая прибыль? (Должна совпадать с таблицей)",
        reply_markup=make_back_restart_keyboard()
    )

@dp.message_handler(state=SellStates.SELL_PROFIT, content_types=types.ContentTypes.TEXT)
async def sell_profit(message: types.Message, state: FSMContext):
    val = message.text.strip()
    # Проверим, что введено число
    if safe_int(val) is None:
        await message.answer("Пожалуйста, укажите целое число — пример: 150000")
        return

    await state.update_data(profit=int(val))
    await SellStates.SELL_MARKETING.set()
    await message.answer(
        "Расскажите, как привлекаете клиентов (активные источники привлечения клиентов):",
        reply_markup=make_skip_back_restart_keyboard()
    )


# ✅ Обработка текста (свободный ввод)
@dp.message_handler(state=SellStates.SELL_MARKETING, content_types=types.ContentTypes.TEXT)
async def process_marketing_text(message: types.Message, state: FSMContext):
    # Игнорируем служебные кнопки, которые обрабатываются отдельно
    if message.text in ["Назад", "Пропустить", "Начать сначала"]:
        return

    await state.update_data(marketing=message.text.strip())
    await SellStates.SELL_EMPLOYEES.set()
    await message.answer(
        "Заполните информацию про сотрудников (количество, ФОТ, стаж, должности):",
        reply_markup=make_back_restart_keyboard()
    )


# ✅ Обработка кнопки "Пропустить"

@dp.message_handler(state=SellStates.SELL_EMPLOYEES, content_types=types.ContentTypes.TEXT)
async def sell_employees(message: types.Message, state: FSMContext):
    await state.update_data(employees=message.text.strip())
    await SellStates.SELL_PREMISES.set()
    await message.answer(
        "Информация о помещении ((суб)аренда/собственность, площадь,коммунальные, ремонт и т.д.):",
        reply_markup=make_back_restart_keyboard()
    )


@dp.message_handler(state=SellStates.SELL_PREMISES, content_types=types.ContentTypes.TEXT)
async def sell_premises(message: types.Message, state: FSMContext):
    await state.update_data(premises=message.text.strip())
    await SellStates.SELL_INCLUDED.set()
    await message.answer(
        "Что входит в стоимость бизнеса? (Материальное и не материальное, обеспечительный платеж, товарные остатки, ваше сопровождение и т.д.)",
        reply_markup=make_back_restart_keyboard()
    )


@dp.message_handler(state=SellStates.SELL_INCLUDED, content_types=types.ContentTypes.TEXT)
async def sell_included(message: types.Message, state: FSMContext):
    await state.update_data(included=message.text.strip())
    await SellStates.SELL_EXTRA.set()
    await message.answer(
        "Дополнительная информация (история бизнеса, причина продажи, доп. инвестиции):",
        reply_markup=make_back_restart_keyboard()
    )


@dp.message_handler(state=SellStates.SELL_EXTRA, content_types=types.ContentTypes.TEXT)
async def sell_extra(message: types.Message, state: FSMContext):
    await state.update_data(extra=message.text.strip())
    await SellStates.SELL_TABLE.set()

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⏭️ Пропустить", callback_data="sell:skip_table"))
    kb.add(
        InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
        InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
    )

    await message.answer(
        "Прикрепите таблицу доходности (файл) или нажмите 'Пропустить'(не рекомендуется).",
        reply_markup=kb
    )


@dp.message_handler(state=SellStates.SELL_TABLE, content_types=types.ContentTypes.DOCUMENT)
async def sell_table_file(message: types.Message, state: FSMContext):
    file = message.document
    await state.update_data(table=file.file_id, table_name=file.file_name)
    await SellStates.SELL_PHOTOS.set()
    await message.answer(
        "Таблица принята. Теперь прикрепите фото (до 10) и/или видео без круглишков ТГ. После загрузки нажмите 'Готово'.",
        reply_markup=make_done_back_restart_keyboard("sell:photos_done")
    )


@dp.callback_query_handler(lambda c: c.data == "sell:skip_table", state=SellStates.SELL_TABLE)
async def sell_skip_table(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(table=None)
    await SellStates.SELL_PHOTOS.set()
    await bot.send_message(
        callback_query.from_user.id,
        "Хорошо. Прикрепите фото (до 10) и/или видео без круглишков ТГ. После загрузки нажмите 'Готово'.",
        reply_markup=make_done_back_restart_keyboard("sell:photos_done")
    )
    await callback_query.answer()


@dp.message_handler(state=SellStates.SELL_PHOTOS, content_types=types.ContentTypes.PHOTO)
async def sell_photos_handler(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        photos: List[str] = data.get("photos", [])
        file_id = message.photo[-1].file_id

        if len(photos) >= MAX_PHOTOS:
            await message.answer(f"Можно прикрепить максимум {MAX_PHOTOS} фото.")
            return

        photos.append(file_id)
        await state.update_data(photos=photos)
        await message.answer(
            f"Фото принято ({len(photos)}/{MAX_PHOTOS}).",
            reply_markup=make_done_back_restart_keyboard("sell:photos_done")
        )
    except Exception as e:
        logger.exception("Ошибка добавления фото: %s", e)
        await message.answer("Не удалось принять фото.")


@dp.message_handler(state=SellStates.SELL_PHOTOS, content_types=types.ContentTypes.VIDEO)
async def sell_video_handler(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        if data.get("video"):
            await message.answer("Видео уже прикреплено. Можно прикрепить только одно видео.")
            return

        await state.update_data(video=message.video.file_id)
        await message.answer(
            "Видео принято.",
            reply_markup=make_done_back_restart_keyboard("sell:photos_done")
        )
    except Exception as e:
        logger.exception("Ошибка добавления видео: %s", e)
        await message.answer("Не удалось принять видео.")


@dp.message_handler(state=SellStates.SELL_PHOTOS, content_types=types.ContentTypes.VIDEO_NOTE)
async def sell_video_note_handler(message: types.Message, state: FSMContext):
    """
    Обработчик видеокружочков (video_note)
    """
    try:
        data = await state.get_data()
        if data.get("video_note"):
            await message.answer("Видеокружочек уже прикреплён. Можно прикрепить только один.")
            return

        await state.update_data(video_note=message.video_note.file_id)
        await message.answer(
            "🎥 Видеокружочек принят.",
            reply_markup=make_done_back_restart_keyboard("sell:photos_done")
        )
    except Exception as e:
        logger.exception("Ошибка добавления видеокружочка: %s", e)
        await message.answer("Не удалось принять видеокружочек.")

@dp.callback_query_handler(lambda c: c.data == "sell:photos_done", state=SellStates.SELL_PHOTOS)
async def sell_photos_done(callback_query: types.CallbackQuery, state: FSMContext):
    await SellStates.SELL_CITY.set()
    await bot.send_message(
        callback_query.from_user.id,
        "Напишите город с большой буквы (например: Новосибирск):",
        reply_markup=make_back_restart_keyboard()
    )
    await callback_query.answer()

@dp.message_handler(state=SellStates.SELL_CITY, content_types=types.ContentTypes.TEXT)
async def sell_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(city=city)
    # 👉 Сначала спрашиваем адрес
    await SellStates.SELL_ADDRESS.set()
    await message.answer(
        "Укажите адрес бизнеса:",
        reply_markup=make_back_restart_keyboard()
    )

@dp.message_handler(state=SellStates.SELL_ADDRESS, content_types=types.ContentTypes.TEXT)
async def sell_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    # 👉 После адреса переходим к цене
    await SellStates.SELL_PRICE.set()
    await message.answer(
        "Укажите стоимость бизнеса целым числом (например: 1250700):",
        reply_markup=make_back_restart_keyboard()
    )

@dp.message_handler(state=SellStates.SELL_PRICE, content_types=types.ContentTypes.TEXT)
async def sell_price(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if safe_int(val) is None:
        await message.answer("Пожалуйста, укажите целое число — пример: 1250700")
        return

    await state.update_data(price=val)
    await SellStates.SELL_CATEGORY.set()

    kb = make_categories_keyboard()
    kb.row(
        InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
        InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
    )

    await message.answer("Выберите категорию:", reply_markup=kb)


# Строка ~1142-1165

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("cat:"), state=SellStates.SELL_CATEGORY)
async def sell_category(callback_query: types.CallbackQuery, state: FSMContext):
    cat_idx = callback_query.data.split(":")[1]
    await state.update_data(category_idx=cat_idx)

    await SellStates.SELL_PREVIEW.set()

    data = await state.get_data()
    preview_text = build_sell_preview(data)

    user_id = callback_query.from_user.id

    # ✅ ДОБАВЛЕНО: Отправляем медиа для предпросмотра
    photos = data.get("photos", [])
    video = data.get("video")
    video_note = data.get("video_note")
    table = data.get("table")

    # Отправляем медиагруппу (фото + видео)
    if photos or video:
        media_group = []
        for photo_id in photos[:10]:
            media_group.append(InputMediaPhoto(media=photo_id))
        if video and len(media_group) < 10:
            media_group.append(InputMediaVideo(media=video))

        if media_group:
            try:
                await bot.send_media_group(user_id, media_group)
            except Exception as e:
                logger.error(f"Ошибка отправки медиа в предпросмотр: {e}")

    # Отправляем видеокружочек
    if video_note:
        try:
            await bot.send_video_note(user_id, video_note)
        except Exception as e:
            logger.error(f"Ошибка отправки видеокружочка: {e}")

    # ✅ КЛЮЧЕВОЕ: Отправляем финансовую таблицу
    if table:
        try:
            await bot.send_document(
                user_id,
                table,
                caption="📊 Финансовая таблица"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки таблицы в предпросмотр: {e}")

    # Отправляем текст с кнопками подтверждения
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Да, всё верно", callback_data="preview:confirm"),
        InlineKeyboardButton("❌ Отменить", callback_data="preview:cancel")
    )

    await bot.send_message(
        user_id,
        preview_text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )

    await callback_query.answer()

# Обработка предпросмотра -> подтверждение размещения

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("preview:"), state=SellStates.SELL_PREVIEW)
async def preview_actions(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    if action == "confirm":
        # переводим в состояние подтверждения посредничества
        await SellStates.SELL_AGENT_CONFIRM.set()
        await bot.send_message(
            user_id,
            "Мы готовы разместить ваше объявление бесплатно, однако в случае заинтересованности мы выступим в качестве посредников. Вы согласны?",
            reply_markup=make_confirm_agent_keyboard()
        )
    else:
        await state.finish()
        await bot.send_message(user_id, "Окей, объявление отменено. Если захотите начать заново — /start.")

    await callback_query.answer()


# Обработка согласия на агентство
@dp.callback_query_handler(lambda c: c.data == "sell:agree_agent", state=SellStates.SELL_AGENT_CONFIRM)
async def sell_agree_agent(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(with_agent=True)
    await SellStates.SELL_CONTACT_AGENT.set()
    await bot.send_message(callback_query.from_user.id, "Оставьте контакт для связи (телефон или @username):")
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == "sell:no_agent", state=SellStates.SELL_AGENT_CONFIRM)
async def sell_no_agent(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(with_agent=False)
    await SellStates.SELL_CONTACT_AGENT.set()
    await bot.send_message(callback_query.from_user.id, "Хорошо. Укажите ваш контакт для связи (телефон или @username):")
    await callback_query.answer()


# ✅ НОВЫЙ обработчик: после получения контакта предлагаем пригласить друзей
@dp.message_handler(state=SellStates.SELL_CONTACT_AGENT, content_types=types.ContentTypes.TEXT)
async def sell_contact_agent_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(contact=message.text.strip())

    # Проверяем, согласился ли на агентство
    if data.get("with_agent"):
        # Путь с агентством: предлагаем скидку
        await message.answer(
            "Мы предоставим скидку 20% на нашу комиссию, если вы пригласите 5 друзей в канал.",
            reply_markup=make_agent_discount_keyboard()
        )
    else:
        # ✅ ИСПРАВЛЕНО: путь без посредничества - предлагаем поддержать канал
        await message.answer(
            "Очень жаль! Но мы всё равно разместим ваше объявление бесплатно, "
            "вам всего лишь нужно пригласить 5 друзей в наш канал. Согласны?",
            reply_markup=make_noagent_keyboard()
        )

# noagent flow: пользователь согласился поддержать
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("noagent:"), state=SellStates)
async def noagent_choice(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    if action == "will_invite":
        # ✅ ИСПРАВЛЕНО: генерируем ссылку на КАНАЛ + реферальную ссылку
        channel_username = "goodbiz54"
        bot_username = (await bot.get_me()).username

        channel_link = f"https://t.me/{channel_username}"
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        invite_text = (
            f"Привет! Появился новый ТГ канал, тут продают и покупают готовый бизнес. "
            f"Я свой туда выставил. Подпишись пожалуйста, хочу бонус забрать 🎁\n\n"
            f"👉 Канал: {channel_link}\n"
            f"👉 Перейди в бота и нажми 'Старт': {referral_link}"
        )

        await state.update_data(
            invite_text=invite_text,
            invited=True,
            discount=False,
            referral_link=referral_link,
            channel_link=channel_link,
            waiting_for_invites=True
        )

        # Инициализируем счётчик приглашений
        if user_id not in referral_invites:
            referral_invites[user_id] = []

        await bot.send_message(
            user_id,
            f"📨 Отправьте эти ссылки 5 друзьям:\n\n{invite_text}\n\n"
            f"Приглашено: 0/5",
            reply_markup=make_agent_invite_keyboard()
        )
        await callback_query.answer()

    else:  # noagent:decline
        # ✅ ИСПРАВЛЕНО: пользователь отказался от приглашений
        await state.update_data(invited=False, discount=False)
        await state.update_data(rejected_all=True)
        await finalize_and_send_to_moderation(user_id, state, invited=False)
        await callback_query.answer("Хорошо. Объявление отправлено на модерацию.")
# Обработка выбора агент:will_invite / agent:no_discount
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("agent:"), state=SellStates)
async def agent_choice(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    if action == "will_invite":
        channel_username = "goodbiz54"
        bot_username = (await bot.get_me()).username

        channel_link = f"https://t.me/{channel_username}"
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        invite_text = (
            f"Привет! Появился новый ТГ канал, тут продают и покупают готовый бизнес. "
            f"Я свой туда выставил. Подпишись пожалуйста, хочу бонус забрать 🎁\n\n"
            f"👉 Канал: {channel_link}\n"
            f"👉 Перейди в бота и нажми 'Старт': {referral_link}"
        )

        await state.update_data(
            invite_text=invite_text,
            discount=True,
            invited=True,
            referral_link=referral_link,
            channel_link=channel_link,
            # КЛЮЧЕВОЕ: в агентской ветке верим на слово, не считаем фактические приглашения
            waiting_for_invites=False,
            trust_agent_invites=True
        )

        await bot.send_message(
            user_id,
            f"📨 Отправьте эти ссылки друзьям:\n\n{invite_text}\n\n"
            f"Когда будете готовы — нажмите «Отправил».",
            reply_markup=make_agent_invite_keyboard()
        )
        await callback_query.answer()

    elif action == "no_discount":
        await state.update_data(discount=False, invited=False)
        # Перед отправкой — проверим контакт (если нужен), иначе отправим сразу
        data = await state.get_data()
        if not data.get("contact"):
            await SellStates.SELL_CONTACT_AGENT.set()
            await bot.send_message(user_id, "Пожалуйста, оставьте контакт для связи (телефон или @username):")
        else:
            await finalize_and_send_to_moderation(user_id, state, invited=False)
        await callback_query.answer("Спасибо! Объявление отправлено на модерацию.")

# noagent flow: пользователь согласился поддержать


# Пользователь нажал "Скопировать" приглашение

# Пользователь нажал "Скопировать" приглашение
@dp.callback_query_handler(lambda c: c.data == "invite:copy", state=SellStates)
async def invite_copy(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Отправляет текст приглашения для удобного копирования.
    """
    data = await state.get_data()
    channel_link = data.get("channel_link", "")
    referral_link = data.get("referral_link", "")

    if not channel_link or not referral_link:
        await callback_query.answer("❌ Ссылки не найдены", show_alert=True)
        return

    # ✅ ИСПРАВЛЕНО: отправляем ссылки отдельными сообщениями для удобного копирования
    await bot.send_message(
        callback_query.from_user.id,
        "📋 **Скопируйте и отправьте друзьям:**"
    )

    # Отправляем текст приглашения
    invite_text = (
        f"Привет! Появился новый ТГ канал, тут продают и покупают готовый бизнес. "
        f"Я свой туда выставил. Подпишись пожалуйста, хочу бонус забрать 🎁"
    )
    await bot.send_message(callback_query.from_user.id, invite_text)

    # Отправляем ссылку на канал
    await bot.send_message(
        callback_query.from_user.id,
        f"👉 **Канал:**\n{channel_link}"
    )

    # Отправляем реферальную ссылку
    await bot.send_message(
        callback_query.from_user.id,
        f"👉 **И нажми 'старт' в боте:**\n{referral_link}"
    )

    # Показываем подсказку
    await callback_query.answer("✅ Ссылки отправлены! Скопируйте и отправьте 5 друзьям!", show_alert=False)

# Пользователь нажал "Отправил" приглашение
@dp.callback_query_handler(lambda c: c.data == "invite:sent", state=SellStates)
async def invite_sent(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = await state.get_data()

    # Если агентская ветка со скидкой — доверяем на слово и отправляем сразу
    if data.get("with_agent") and data.get("discount") and data.get("trust_agent_invites"):
        # Убедимся, что контакт есть, иначе попросим
        if not data.get("contact"):
            await SellStates.SELL_CONTACT_AGENT.set()
            await bot.send_message(user_id, "Пожалуйста, оставьте контакт для связи (телефон или @username):")
            await callback_query.answer("Оставьте контакт, и сразу отправим на модерацию.")
            return

        await state.update_data(invited=True)
        await finalize_and_send_to_moderation(user_id, state, invited=True)
        await callback_query.answer("Спасибо! Объявление отправлено на модерацию.")
        return

    # Иначе (ветка без посредничества) — работаем по старой логике с фактическим счётом
    if data.get("waiting_for_invites"):
        count = len(referral_invites.get(user_id, []))
        if count < 5:
            await bot.send_message(
                user_id,
                f"⏳ Пока приглашено только {count}/5 друзей.\n"
                f"Отправьте ссылку ещё {5 - count} друзьям.\n\n"
                f"Как только 5 друзей подпишутся на канал и запустят бота, объявление автоматически отправится на модерацию."
            )
            await callback_query.answer(f"Приглашено: {count}/5")
            return

    # Если порог достигнут или эта ветка не требует подсчёта — отправляем
    await state.update_data(invited=True)
    # Убедимся, что контакт есть
    if not data.get("contact"):
        await SellStates.SELL_CONTACT_AGENT.set()
        await bot.send_message(user_id, "Пожалуйста, оставьте контакт для связи (телефон или @username):")
        await callback_query.answer("Оставьте контакт, и сразу отправим на модерацию.")
        return

    await finalize_and_send_to_moderation(user_id, state, invited=True)
    await callback_query.answer("Спасибо! Объявление отправлено на модерацию.")

# и после нужно запросить контакт (если не указан) и отправить в модерацию:
@dp.message_handler(state=SellStates, content_types=types.ContentTypes.TEXT)
async def generic_sell_text_handler(message: types.Message, state: FSMContext):
    """
    Обработчик любых текстовых сообщений в состоянии SellStates, если не попали в конкретный handler.
    Часто используется для получения контакта после приглашения.
    """
    data = await state.get_data()
    current_state = await state.get_state()
    # Если ожидается контакт (SELL_CONTACT_AGENT), выше есть хендлер, так что сюда попадаем редко.
    # В других состояниях просто ругаемся.
    await message.reply("Пожалуйста, используйте интерфейс бота (кнопки) или дождитесь запроса. Если хотите сбросить данные — /reset.")

# =======================
# Функция отправки на модерацию (в MOD_CHAT_ID)
# =======================


async def finalize_and_send_to_moderation(user_id: int, state: FSMContext, invited: bool = False):
    """
    Финализирует объявление и отправляет на модерацию.
    ✅ Все данные сохраняются в БД
    """
    session = None
    try:
        data = await state.get_data()
        local_id = str(uuid.uuid4())

        # ✅ СОХРАНЯЕМ В БД (асинхронно)
        session = SessionLocal()
        try:
            submission = Submission(
                id=local_id,
                user_id=user_id,
                type="sell",
                data=json.dumps(data),
                invited=invited,
                rejected_all=data.get("rejected_all", False),
                status="pending"
            )
            session.add(submission)
            session.commit()
            logger.info(f"✅ Объявление {local_id} сохранено в БД")
        except Exception as db_error:
            session.rollback()
            logger.exception(f"❌ Ошибка сохранения в БД: {db_error}")
            await bot.send_message(
                user_id,
                "❌ Ошибка при сохранении объявления. Попробуйте позже."
            )
            return
        finally:
            if session is not None:
                session.close()

        # ✅ СОХРАНЯЕМ В ПАМЯТИ (для быстрого доступа модератора)
        pending_submissions[local_id] = {
            "user_id": user_id,
            "data": data,
            "invited": invited,
            "type": "sell",
            "status": "pending"
        }

        # ✅ Формируем текст для модератора
        preview_text = build_sell_preview(data)

        # ✅ ДОБАВЛЯЕМ КОНТАКТ ПОЛЬЗОВАТЕЛЯ
        user_contact = data.get("contact", "Не указан")
        with_agent = data.get("with_agent", False)

        if with_agent:
            preview_text += f"\n\n👤 <b>Контакт продавца:</b> {escape_html(user_contact)}"
            preview_text += f"\n🤝 <b>Посредник:</b> {AGENT_CONTACT}"
        else:
            preview_text += f"\n\n👤 <b>Контакт продавца:</b> {escape_html(user_contact)}"

        if data.get("rejected_all"):
            preview_text += "\n\n⚠️ <b>Пользователь отказался от посредничества и от приглашений.</b>"

        # ✅ Отправляем медиа (если есть)
        photos = data.get("photos", [])
        video = data.get("video")
        video_note = data.get("video_note")

        if photos or video:
            media_group = []
            for photo_id in photos[:10]:
                media_group.append(InputMediaPhoto(media=photo_id))
            if video and len(media_group) < 10:
                media_group.append(InputMediaVideo(media=video))

            if media_group:
                try:
                    await bot.send_media_group(MOD_CHAT_ID, media_group)
                    logger.info(f"✅ Медиа отправлено модератору для {local_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки медиа на модерацию: {e}")

        if video_note:
            try:
                await bot.send_video_note(MOD_CHAT_ID, video_note)
                logger.info(f"✅ Видеокружочек отправлен модератору для {local_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки видеокружочка на модерацию: {e}")

        # ✅ Отправляем текст с кнопками модерации
        mod_kb = make_mod_inline(local_id)
        try:
            await bot.send_message(
                MOD_CHAT_ID,
                preview_text,
                reply_markup=mod_kb,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"✅ Текст модерации отправлен для {local_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста модерации: {e}")
            await bot.send_message(
                user_id,
                "❌ Ошибка при отправке на модерацию. Попробуйте позже."
            )
            return

        # ✅ Отправляем таблицу (если есть)
        table = data.get("table")
        if table:
            try:
                await bot.send_document(
                    MOD_CHAT_ID,
                    table,
                    caption="📊 Финансовая таблица"
                )
                logger.info(f"✅ Таблица отправлена модератору для {local_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки таблицы на модерацию: {e}")

        # ✅ Уведомляем пользователя
        await bot.send_message(
            user_id,
            "✅ Ваше объявление отправлено на модерацию!\n"
            "Мы проверим его и опубликуем в ближайшее время.\n\n"
            f"ID объявления: <code>{local_id}</code>",
            parse_mode=ParseMode.HTML
        )

        # ✅ Завершаем FSM
        await state.finish()

        logger.info(f"✅ Объявление {local_id} от пользователя {user_id} успешно отправлено на модерацию")

    except Exception as e:
        logger.exception(f"❌ Критическая ошибка при отправке на модерацию: {e}")
        try:
            await bot.send_message(
                user_id,
                "❌ Произошла ошибка при отправке объявления. Попробуйте позже или напишите администратору."
            )
        except Exception as send_error:
            logger.exception(f"❌ Не удалось отправить сообщение об ошибке пользователю: {send_error}")
    finally:
        # ✅ ВСЕГДА закрываем сессию БД
        if session is not None:
            try:
                session.close()
                logger.info("✅ Сессия БД закрыта")
            except Exception as close_error:
                logger.exception(f"❌ Ошибка при закрытии сессии БД: {close_error}")
# =======================
# BUY flow (покупка)
# =======================

# ✅ ПРАВИЛЬНО
@dp.message_handler(state=BuyStates.BUY_BUDGET, content_types=types.ContentTypes.TEXT)
async def buy_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=message.text.strip())
    await BuyStates.BUY_CITY.set()
    await message.answer("В каком городе? (Напишите с большой буквы)")


@dp.message_handler(state=BuyStates.BUY_CITY, content_types=types.ContentTypes.TEXT)
async def buy_city(message: types.Message, state: FSMContext):
    # ✅ ИСПРАВЛЕНО: убрана избыточная строка
    await state.update_data(city=message.text.strip())
    await BuyStates.BUY_CATEGORY.set()


    kb = make_categories_keyboard(prefix="buycat")
    kb.row(
        InlineKeyboardButton("◀️ Назад", callback_data="nav:back"),
        InlineKeyboardButton("🔄 Начать сначала", callback_data="nav:restart")
    )

    await message.answer(
        "Какой вид деятельности рассматриваете? Выберите категорию:",
        reply_markup=kb
    )


@dp.callback_query_handler(lambda c: c.data.startswith("buycat:"), state=BuyStates.BUY_CATEGORY)
async def buy_category_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Шаг 4: Получаем категорию, спрашиваем про опыт."""
    cat_idx = callback_query.data.split(":")[1]
    await state.update_data(category_idx=cat_idx)

    await callback_query.message.edit_text("Есть ли у вас опыт в бизнесе? (Напишите Да/Нет или опишите опыт)")
    await BuyStates.BUY_EXPERIENCE.set()
    await callback_query.answer()


# =======================
# Модерация: Publish / Reject
# =======================


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("mod:publish:"))
async def mod_publish(callback_query: types.CallbackQuery):
    """
    Обработчик кнопки публикации объявления модератором.
    ✅ Обновляет статус в БД
    ✅ Публикует в канал
    ✅ Уведомляет пользователя
    """
    session = None  # ✅ Явно инициализируем как None
    try:
        # Извлекаем local_id из callback_data
        parts = callback_query.data.split(":")
        if len(parts) < 3:
            await callback_query.answer("❌ Ошибка: неверный формат данных")
            return

        local_id = parts[2]
        submission = pending_submissions.get(local_id)

        if not submission:
            await callback_query.answer("❌ Заявка не найдена или уже обработана.")
            return

        # ✅ Получаем сессию БД
        session = SessionLocal()  # ✅ Теперь session имеет правильный тип

        try:
            # ✅ Обновляем статус в БД
            db_submission = session.query(Submission).filter(
                Submission.id == local_id
            ).first()

            if not db_submission:
                await callback_query.answer("❌ Заявка не найдена в БД")
                return

            db_submission.status = "published"
            session.commit()
            logger.info(f"✅ Статус заявки {local_id} обновлён на 'published' в БД")

        except Exception as db_error:
            session.rollback()
            logger.exception(f"❌ Ошибка обновления БД: {db_error}")
            await callback_query.answer("❌ Ошибка при обновлении статуса в БД")
            return
        finally:
            session.close()  # ✅ Закрываем внутреннюю сессию

        # ✅ Публикуем в канал
        if submission["type"] == "sell":
            try:
                await publish_sell(submission)
                logger.info(f"✅ Объявление {local_id} опубликовано в канал")
            except Exception as pub_error:
                logger.exception(f"❌ Ошибка публикации объявления {local_id}: {pub_error}")
                await callback_query.answer("❌ Ошибка при публикации объявления")
                return

        elif submission["type"] == "buy":
            await callback_query.answer("⚠️ Публикация заявок покупателей не поддерживается в общий канал.")
            return

        # ✅ Уведомляем продавца/покупателя
        user_id = submission.get("user_id")
        if user_id:
            try:
                await bot.send_message(
                    user_id,
                    "✅ Ваше объявление опубликовано!\n\n"
                    "Спасибо за использование нашего сервиса. "
                    "Ожидайте предложений от заинтересованных покупателей.",
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"✅ Уведомление отправлено пользователю {user_id}")
            except Exception as msg_error:
                logger.exception(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {msg_error}")

        # ✅ Удаляем из памяти (pending_submissions)
        pending_submissions.pop(local_id, None)
        logger.info(f"✅ Заявка {local_id} удалена из очереди pending_submissions")

        # ✅ Уведомляем модератора
        await callback_query.answer("✅ Объявление опубликовано успешно!")
        logger.info(f"✅ Модератор {callback_query.from_user.id} опубликовал заявку {local_id}")

    except ValueError as ve:
        logger.exception(f"❌ Ошибка парсинга callback_data: {ve}")
        await callback_query.answer("❌ Ошибка: неверный формат данных")

    except Exception as e:
        logger.exception(f"❌ Критическая ошибка при публикации {callback_query.data}: {e}")
        await callback_query.answer("❌ Произошла ошибка при публикации. Попробуйте позже.")

    finally:
        # ✅ ВСЕГДА закрываем сессию (если она была открыта)
        if session is not None:  # ✅ Проверяем, что session не None
            try:
                session.close()
                logger.info("✅ Сессия БД закрыта")
            except Exception as close_error:
                logger.exception(f"❌ Ошибка при закрытии сессии БД: {close_error}")
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("mod:reject:"))
async def mod_reject(callback_query: types.CallbackQuery):
    try:
        _, _, local_id = callback_query.data.split(":")
        submission = pending_submissions.get(local_id)
        if not submission:
            await callback_query.answer("Заявка не найдена или уже обработана.")
            return

        mod_id = callback_query.from_user.id
        mod_rejection_state[mod_id] = local_id

        # ✅ ИСПРАВЛЕНО: правильное получение FSMContext для модератора
        state_proxy = dp.current_state(chat=mod_id, user=mod_id)
        await state_proxy.set_state(ModStates.MOD_REASON.state)

        await bot.send_message(mod_id, f"Напишите причину отклонения для заявки {local_id}:")
        await callback_query.answer("Ожидаю причину отклонения...")

    except Exception as e:
        logger.exception("Ошибка при модерации reject: %s", e)
        await callback_query.answer("Ошибка при обработке отклонения.")

# Обработка причины отклонения от модератора


@dp.message_handler(state=ModStates.MOD_REASON, content_types=types.ContentTypes.TEXT)
async def mod_reason_input(message: types.Message, state: FSMContext):
    mod_id = message.from_user.id
    reason = message.text.strip()

    # ✅ ЛОГИРОВАНИЕ для отладки
    logger.info(f"[MOD_REASON] Модератор {mod_id} ввёл причину: {reason[:50]}...")

    local_id = mod_rejection_state.get(mod_id)
    if not local_id:
        await message.answer("❌ Не найдена заявка для отклонения. Попробуйте снова.")
        await state.finish()
        return

    submission = pending_submissions.get(local_id)
    if not submission:
        await message.answer("❌ Заявка уже обработана или не найдена.")
        await state.finish()
        mod_rejection_state.pop(mod_id, None)
        return

    # ✅ Отправляем причину отклонения пользователю
    try:
        await bot.send_message(
            submission["user_id"],
            f"❌ Ваше объявление отклонено.\n\n📝 Причина:\n{reason}"
        )
        logger.info(f"[MOD_REASON] Отправлено уведомление пользователю {submission['user_id']}")
    except Exception as e:
        logger.exception(f"Ошибка отправки причины отклонения пользователю {submission['user_id']}: {e}")

    # ✅ Удаляем заявку из очереди
    pending_submissions.pop(local_id, None)
    mod_rejection_state.pop(mod_id, None)

    # ✅ Уведомляем модератора
    await message.answer(f"✅ Заявка {local_id} отклонена. Причина отправлена пользователю.")

    # ✅ Завершаем FSM состояние модератора
    await state.finish()

@dp.message_handler(state=BuyStates.BUY_EXPERIENCE)
async def buy_experience_handler(message: types.Message, state: FSMContext):
    """Получает опыт, сохраняет и запрашивает контакт."""
    await state.update_data(experience=message.text)
    await message.answer("Отлично! Теперь, пожалуйста, оставьте ваш контакт для связи (номер телефона или @username).")
    await BuyStates.BUY_PHONE.set()



@dp.message_handler(state=BuyStates.BUY_PHONE)
async def buy_contact_handler(message: types.Message, state: FSMContext):
    """Получает контакт и переходит к вопросу о времени связи."""
    await state.update_data(contact=message.text)
    await BuyStates.BUY_WHEN_CONTACT.set()
    await message.answer(
        "Когда лучше связаться?",
        reply_markup=make_back_restart_keyboard()
    )

@dp.message_handler(state=BuyStates.BUY_WHEN_CONTACT)
async def buy_when_contact_handler(message: types.Message, state: FSMContext):
    """Получает время для связи и завершает заявку."""
    await state.update_data(when_contact=message.text.strip())
    user_data = await state.get_data()

    # Формируем текст заявки
    preview_text = build_buy_preview(user_data)

    # Отправляем на модерацию
    try:
        await bot.send_message(MOD_CHAT_ID, preview_text, parse_mode=ParseMode.HTML)
        await message.answer(
            "✅ Спасибо! Ваша заявка принята и отправлена на рассмотрение.\n\n"
            "Мы свяжемся с вами, как только появятся подходящие варианты.",
            reply_markup=make_restart_only_keyboard()
        )
    except Exception as e:
        logger.error(f"Не удалось отправить заявку на покупку на модерацию: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже или свяжитесь с администратором.",
            reply_markup=make_restart_only_keyboard()
        )

    # Завершаем сценарий
    await state.finish()
# =======================
# Запуск бота
# =======================
from aiogram import executor

from db import engine, SessionLocal, Base
from models import Submission


# =======================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =======================


def build_sell_preview(data: Dict[str, Any]) -> str:
    """Формирует текст предпросмотра объявления на продажу"""
    title = escape_html(data.get("title", ""))
    profit = format_number(data.get("profit", ""))
    city = escape_html(data.get("city", ""))
    price = format_number(data.get("price", ""))
    category = CATEGORIES.get(data.get("category_idx", ""), "")

    text = (
        f"<b>📌 {title}</b>\n\n"
        f"💰 <b>Чистая прибыль:</b> {profit} ₽\n"
        f"💵 <b>Стоимость:</b> {price} ₽\n"
        f"📍 <b>Город:</b> {city}\n"
        f"🏷️ <b>Категория:</b> {category}\n"
    )

    if data.get("marketing"):
        text += f"\n📢 <b>Маркетинг:</b> {escape_html(data.get('marketing'))}\n"

    if data.get("employees"):
        text += f"\n👥 <b>Сотрудники:</b> {escape_html(data.get('employees'))}\n"

    if data.get("premises"):
        text += f"\n🏢 <b>Помещение:</b> {escape_html(data.get('premises'))}\n"

    if data.get("included"):
        text += f"\n📦 <b>Входит в стоимость:</b> {escape_html(data.get('included'))}\n"

    if data.get("extra"):
        text += f"\n📝 <b>Доп. информация:</b> {escape_html(data.get('extra'))}\n"

    return text

def build_buy_preview(data: Dict[str, Any]) -> str:
    """Формирует текст заявки на покупку"""
    budget = escape_html(data.get("budget", ""))
    city = escape_html(data.get("city", ""))
    category = CATEGORIES.get(data.get("category_idx", ""), "")
    experience = escape_html(data.get("experience", ""))
    contact = escape_html(data.get("contact", ""))
    when_contact = escape_html(data.get("when_contact", ""))

    text = (
        f"<b>🔍 НОВАЯ ЗАЯВКА НА ПОКУПКУ</b>\n\n"
        f"💰 <b>Бюджет:</b> {budget}\n"
        f"📍 <b>Город:</b> {city}\n"
        f"🏷️ <b>Категория:</b> {category}\n"
        f"📚 <b>Опыт:</b> {experience}\n"
        f"📞 <b>Контакт:</b> {contact}\n"
        f"⏰ <b>Когда связаться:</b> {when_contact}\n"
    )

    return text


def make_agent_discount_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора: согласиться на скидку или нет"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Согласен на скидку", callback_data="agent:will_invite"),
        InlineKeyboardButton("❌ Без скидки", callback_data="agent:no_discount")
    )
    return kb


def make_noagent_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора: пригласить друзей или отказаться"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Согласен пригласить", callback_data="noagent:will_invite"),
        InlineKeyboardButton("❌ Отказываюсь", callback_data="noagent:decline")
    )
    return kb


def make_agent_invite_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отправки приглашений"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📋 Скопировать", callback_data="invite:copy"),
        InlineKeyboardButton("✅ Отправил", callback_data="invite:sent")
    )
    return kb


async def publish_sell(submission: dict):
    """
    Публикует объявление о продаже в канал.
    """
    try:
        data = submission.get("data", {})

        # Формируем текст для публикации
        preview_text = build_sell_preview(data)

        # Отправляем медиа (если есть)
        photos = data.get("photos", [])
        video = data.get("video")
        video_note = data.get("video_note")

        if photos or video:
            media_group = []
            for photo_id in photos[:10]:
                media_group.append(InputMediaPhoto(media=photo_id))
            if video and len(media_group) < 10:
                media_group.append(InputMediaVideo(media=video))

            if media_group:
                await bot.send_media_group(CHANNEL_ID, media_group)

        if video_note:
            await bot.send_video_note(CHANNEL_ID, video_note)

        # Отправляем текст объявления
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📞 Связаться с продавцом", url="https://t.me/goodbiz54"))

        await bot.send_message(
            CHANNEL_ID,
            preview_text,
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )

        logger.info(f"✅ Объявление опубликовано в канал {CHANNEL_ID}")

    except Exception as e:
        logger.exception(f"❌ Ошибка при публикации объявления: {e}")
        raise

if __name__ == "__main__":
    executor.start_polling(
        dispatcher=dp,
        startup=init_db,
    )