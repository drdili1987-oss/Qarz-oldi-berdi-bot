from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    choosing_language = State()
    entering_name = State()
    entering_age = State()
    choosing_gender = State()
    entering_country = State()
    entering_city = State()
    entering_occupation = State()
    entering_phone = State()


class AddDebt(StatesGroup):
    entering_recipient = State()
    choosing_currency = State()
    entering_amount = State()
    entering_description = State()
    entering_due_date = State()


class FinanceOperation(StatesGroup):
    choosing_person = State()
    entering_amount = State()


class AdminBroadcast(StatesGroup):
    entering_message = State()
    confirming = State()
