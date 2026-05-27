import asyncio
import logging
import uuid

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from .cards import create_prediction_card
from .config import DEFAULT_BIAS_STRENGTH, DEFAULT_CANDIDATE_K, DEFAULT_SELECTION, DEFAULT_TEMPERATURE, TMP_DIR
from .matcher import MatchSettings, SpaceObjectMatcher


class UserFlow(StatesGroup):
    """Finite-state flow for choosing a language and waiting for a user photo."""

    choosing_language = State()
    waiting_for_photo = State()


LANG_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Русский'), KeyboardButton(text='English')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

LANG_BY_TEXT = {
    'русский': 'ru',
    'ru': 'ru',
    'russian': 'ru',
    'english': 'en',
    'en': 'en',
}

WELCOME_TEXT = (
    '✨ Привет! Это GalaxyMatchBot: научный космический оракул.\n\n'
    'Отправь свое фото, я сравню изображение с настоящими галактиками, туманностями, планетами и другими объектами космоса. '
    'В ответ ты получишь карточку с объектом, который ближе всего по визуальному сходству.\n\n'
    '✨ Hi! This is GalaxyMatchBot: a scientific cosmic oracle.\n\n'
    'Send a portrait photo, and I will compare the image with real galaxies, nebulae, planets, and other space objects. '
    'You will get a card with the object that is closest by visual similarity.\n\n'
    '👇 First, choose the card language:'
)


def build_router(matcher: SpaceObjectMatcher):
    """Create Telegram handlers bound to a preloaded space-object matcher."""
    router = Router()

    async def ask_language(message: Message, state: FSMContext):
        """Reset the user flow and ask for the output card language."""
        await state.set_state(UserFlow.choosing_language)
        await message.answer(WELCOME_TEXT, reply_markup=LANG_KEYBOARD)

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext):
        """Start a new user flow by asking for the output card language."""
        await ask_language(message, state)

    @router.message(F.text.lower().in_({'start', 'старт'}))
    async def text_start(message: Message, state: FSMContext):
        """Start the flow when the user sends start as plain text."""
        await ask_language(message, state)

    @router.message(UserFlow.choosing_language)
    async def choose_language(message: Message, state: FSMContext):
        """Store the selected language and ask the user to send a photo."""
        text = (message.text or '').strip().lower()
        lang = LANG_BY_TEXT.get(text)
        if lang is None:
            await message.answer('Нажми Русский или English.', reply_markup=LANG_KEYBOARD)
            return

        await state.update_data(lang=lang)
        await state.set_state(UserFlow.waiting_for_photo)
        if lang == 'en':
            await message.answer('Send me a portrait photo and I will return your space-object card.', reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer('Пришли фото человека, а я верну карточку с космическим объектом.', reply_markup=ReplyKeyboardRemove())

    @router.message(UserFlow.waiting_for_photo, F.photo)
    async def handle_photo(message: Message, state: FSMContext, bot: Bot):
        """Download a Telegram photo, generate a card, send it back, and clean up."""
        data = await state.get_data()
        lang = data.get('lang', 'ru')
        TMP_DIR.mkdir(parents=True, exist_ok=True)

        photo_id = uuid.uuid4().hex
        input_path = TMP_DIR / f'{photo_id}.jpg'
        output_path = TMP_DIR / f'{photo_id}_card.jpg'

        try:
            await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            await bot.download_file(file.file_path, destination=input_path)

            settings = MatchSettings(
                candidate_k=DEFAULT_CANDIDATE_K,
                bias_strength=DEFAULT_BIAS_STRENGTH,
                selection=DEFAULT_SELECTION,
                temperature=DEFAULT_TEMPERATURE,
            )
            best, _, _ = await asyncio.to_thread(matcher.predict_space_object_raw, input_path, settings)
            card_path = await asyncio.to_thread(create_prediction_card, input_path, best, lang, output_path)

            card_bytes = card_path.read_bytes()
            filename = 'space_card.jpg' if lang == 'en' else 'kosmicheskaya_kartochka.jpg'
            await message.answer_photo(BufferedInputFile(card_bytes, filename=filename))
        except Exception:
            logging.exception('Cannot process Telegram photo')
            if lang == 'en':
                await message.answer('Something went wrong. Please try another photo.')
            else:
                await message.answer('Что-то пошло не так. Попробуй отправить другое фото.')
        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    @router.message(UserFlow.waiting_for_photo)
    async def ask_for_photo(message: Message, state: FSMContext):
        """Handle non-photo messages while the bot is waiting for an image."""
        data = await state.get_data()
        if data.get('lang') == 'en':
            await message.answer('Please send a photo, not text or a file.')
        else:
            await message.answer('Пришли именно фото, не текст и не файл.')

    @router.message()
    async def fallback_start(message: Message, state: FSMContext):
        """Start the flow for any first message that did not match other handlers."""
        await ask_language(message, state)

    return router


async def run_bot(token: str, matcher: SpaceObjectMatcher):
    """Start aiogram polling with the provided bot token and loaded matcher."""
    bot = Bot(token=token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(matcher))
    await dispatcher.start_polling(bot)
