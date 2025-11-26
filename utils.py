# какой-то мусор
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
