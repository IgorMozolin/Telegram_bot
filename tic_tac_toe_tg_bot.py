"""
Bot for playing tic tac toe game with multiple CallbackQueryHandlers.
"""
from copy import deepcopy
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
import os
import random
from dotenv import load_dotenv
from typing import List


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx
# to avoid all GET and POST requests being logged
logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# get token using BotFather
load_dotenv()
TOKEN = os.getenv('TG_TOKEN')

CONTINUE_GAME, FINISH_GAME = range(2)

FREE_SPACE = '.'
CROSS = 'X'
ZERO = 'O'


DEFAULT_STATE = [[FREE_SPACE for _ in range(3)] for _ in range(3)]


def get_default_state():
    """Helper function to get default state of the game"""
    return deepcopy(DEFAULT_STATE)


def generate_keyboard(state: List[List[str]]) -> \
        List[List[InlineKeyboardButton]]:
    """Generate tic tac toe keyboard 3x3 (telegram buttons)"""
    return [
        [
            InlineKeyboardButton(state[r][c], callback_data=f'{r}{c}')
            for r in range(3)
        ]
        for c in range(3)
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    context.user_data['keyboard_state'] = get_default_state()
    keyboard = generate_keyboard(context.user_data['keyboard_state'])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "X (your) turn! Please, put X to the free place.\n"
        "To finish game please press '/stop'",
        reply_markup=reply_markup)
    return CONTINUE_GAME


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main processing of the game"""
    query = update.callback_query
    await query.answer()

    r, c = map(int, query.data)
    state = context.user_data['keyboard_state']

    # Free cell check
    if state[r][c] != FREE_SPACE:
        await query.message.reply_text(
            "This cell is already occupied! Please, choose another one.")
        return CONTINUE_GAME

    # User turn
    state[r][c] = CROSS

    # User victory check
    if won(state, CROSS):
        await query.message.reply_text(
            "You won! To play again please press '/start'\n"
            "To finish game please press '/stop'")
        return FINISH_GAME

    # AI turn (random cell)
    free_cells = [(i, j) for i in range(3) for j in range(3)
                  if state[i][j] == FREE_SPACE]
    if free_cells:
        ir, ic = random.choice(free_cells)
        state[ir][ic] = ZERO

        # AI victory check
        if won(state, ZERO):
            await query.message.reply_text(
                "AI won! To play again please press '/start'\n"
                "To finish game please press '/stop'")
            return FINISH_GAME

    # Draw check
    if not free_cells:
        await query.message.reply_text(
            "Draw! To play again please press '/start'\n"
            "To finish game please press '/stop'")
        return FINISH_GAME

    # # Updating the keyboard
    keyboard = generate_keyboard(state)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="X (your) turn! Please, put X to the free place.\n"
             "To finish game please press '/stop'",
        reply_markup=reply_markup
    )
    return CONTINUE_GAME


def won(fields: List[str], symbol: str) -> bool:
    """Check if crosses or zeros have won the game"""
    # Lines check
    for row in fields:
        if all(cell == symbol for cell in row):
            return True

    # Columns check
    for col in range(3):
        if all(fields[row][col] == symbol for row in range(3)):
            return True

    # Diagonals check
    if all(fields[i][i] == symbol for i in range(3)) or \
            all(fields[i][2 - i] == symbol for i in range(3)):
        return True

    return False


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    # reset state to default so you can play again with /start
    context.user_data['keyboard_state'] = get_default_state()
    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Command to stop the bot."""
    await update.message.reply_text("Bot is stopping... Goodbye!")
    context.user_data['keyboard_state'] = get_default_state()
    await context.application.stop()
    return ConversationHandler.END


def main() -> None:
    """Run the bot"""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Setup conversation handler with the states CONTINUE_GAME and FINISH_GAME
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONTINUE_GAME: [
                CallbackQueryHandler(game, pattern='^' + f'{r}{c}' + '$')
                for r in range(3)
                for c in range(3)
            ],
            FINISH_GAME: [
                CallbackQueryHandler(end, pattern='^' + f'{r}{c}' + '$')
                for r in range(3)
                for c in range(3)
            ],
        },
        fallbacks=[CommandHandler('stop', stop),
                   CommandHandler('start', start)],
    )

    # Add ConversationHandler to application
    # that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
