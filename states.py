"""FSM holatlari — масъул."""

from aiogram.fsm.state import State, StatesGroup


class LoadStartStates(StatesGroup):
    car_photo = State()
    extra_photo = State()


class LoadFinishStates(StatesGroup):
    car_photo = State()
    extra_photo = State()


class AddOperatorStates(StatesGroup):
    waiting = State()
