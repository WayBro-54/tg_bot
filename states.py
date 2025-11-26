from aiogram.dispatcher.filters.state import StatesGroup, State


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