from aiogram.fsm.state import State, StatesGroup


class TrainerStates(StatesGroup):
    adding_exercise_description = State()
    adding_exercise_set_count = State()
    adding_set_reps = State()
    adding_set_weight = State()


class TraineeStates(StatesGroup):
    logging_set_reps = State()
    logging_set_weight = State()
    adding_comment = State()
