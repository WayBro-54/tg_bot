from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tg_bot.constants import CATEGORIES


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