from api_sheets import *
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker, declarative_base


token = '8272142309:AAGIHjAHT0iXayrPeJzUX6JM9X-OR6PPlBE'

async_engine = create_async_engine("sqlite+aiosqlite:///vpn_bot.db", echo=False)

Base = declarative_base()

class Sheets(Base):
    __tablename__ = "tables_names"
    id = Column(Integer, primary_key=True)
    user_id  = Column(Integer)
    name = Column(String)


# Создание таблиц (асинхронно)
async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Создание фабрики асинхронных сессий
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


# FSM для добавления таблицы
class AddTableState(StatesGroup):
    waiting_for_name = State()


# Временное хранилище данных inline_query (в продакшене лучше Redis)
user_pending_data = {}


router = Router()
async def handle_activation(user_id: int, query_text: str, call: types.CallbackQuery, bot: Bot, spreadsheet_name: str = None):
    try:
        parts = query_text.split()
        if len(parts) >= 2:
            intrance = int(parts[0])
            extrance = int(parts[1])
        else:
            await bot.edit_message_text(
                text="Не верный формат ввода (нужно 2 числа через пробел)",
                inline_message_id=call.inline_message_id,
                parse_mode="HTML"
            )   
            return
        await bot.edit_message_text(
            text="<tg-emoji emoji-id='5386367538735104399'>🔄</tg-emoji> Загрузка данных в облако",
            inline_message_id=call.inline_message_id,
            parse_mode="HTML"
        )
        # Если имя таблицы не передано, используем имя из БД
        if not spreadsheet_name:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Sheets).where(Sheets.user_id == user_id)
                )
                table = result.scalars().first()
                if table:
                    spreadsheet_name = table.name
                else:
                    await bot.edit_message_text(
                        text="Ошибка: нет доступных таблиц",
                        inline_message_id=call.inline_message_id,
                        parse_mode="HTML"
                    )
                    return
        status = add_order(intrance, extrance, spreadsheet_name)
        if status:
            await bot.edit_message_text(
                text=f"<tg-emoji emoji-id='5249448542593883237'>✅</tg-emoji> Успешно добавлено в таблицу <b>{spreadsheet_name}</b>\n\n➤ <b>Пришло:</b> {intrance}\n<b>➤ Отправлено:</b> {extrance}\n<b>➤ Итоговая прибыль:</b> {intrance - extrance}",
                inline_message_id=call.inline_message_id,
                parse_mode="HTML"
            )
        else:
            await bot.edit_message_text(
                text=f"Ошибка при добавлении записи",
                inline_message_id=call.inline_message_id,
                parse_mode="HTML"
            )   
        
    except Exception as e:
        print(e)



@router.inline_query()
async def inline_echo(inline_query: types.InlineQuery):
    result_id = str(hash(inline_query.query))
    intrance = None
    extrance = None
    if inline_query.from_user.id != 1240656726:
        return
    try:
        parts = inline_query.query.split()
        if len(parts) >= 2:
            intrance = int(parts[0])
            extrance = int(parts[1])
        else:
            text = 'Не верный формат ввода (нужно 2 числа через пробел)'
            item = types.InlineQueryResultArticle(
                id=result_id,
                title=text,
                input_message_content=types.InputTextMessageContent(message_text=text),
            )
            await inline_query.answer([item], cache_time=1)
            return
    except Exception as e:
        text = 'Не верный формат ввода'
        item = types.InlineQueryResultArticle(
            id=result_id,
            title=text,
            input_message_content=types.InputTextMessageContent(message_text=text),
        )
        await inline_query.answer([item], cache_time=1)
        return
    
    text = f"Получено: {intrance}, потрачено: {extrance}"

    item = types.InlineQueryResultArticle(
        id=result_id,
        title=text,
        input_message_content=types.InputTextMessageContent(
            message_text=text,

        ),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Записать", callback_data=f"activate:{inline_query.query}")]
            ]
        )
    )
    
    await inline_query.answer([item], cache_time=1)


@router.callback_query(lambda c: c.data.startswith("activate:"))
async def handle_activate_callback(callback: types.CallbackQuery):
    query_text = callback.data.replace("activate:", "", 1)
    user_id = callback.from_user.id
    
    # Сохраняем данные для записи
    user_pending_data[user_id] = query_text
    
    # Получаем список таблиц пользователя
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Sheets).where(Sheets.user_id == user_id)
        )
        tables = result.scalars().all()
    
    if not tables:
        text = "У вас нет добавленных таблиц. Используйте /add_table чтобы добавить таблицу."
        if callback.inline_message_id:
            await callback.bot.edit_message_text(
                text=text,
                inline_message_id=callback.inline_message_id,
                parse_mode="HTML"
            )
        elif callback.message:
            await callback.message.edit_text(text)
        await callback.answer()
        return
    
    # Показываем кнопки выбора таблицы
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=table.name, callback_data=f"select_table:{table.id}")]
            for table in tables
        ]
    )
    
    text = "Выберите таблицу для записи:"
    if callback.inline_message_id:
        await callback.bot.edit_message_text(
            text=text,
            inline_message_id=callback.inline_message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    elif callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("select_table:"))
async def handle_select_table_callback(callback: types.CallbackQuery):
    table_id = int(callback.data.replace("select_table:", "", 1))
    user_id = callback.from_user.id
    
    # Получаем сохраненные данные для записи
    query_text = user_pending_data.get(user_id)
    
    if not query_text:
        text = "Данные для записи не найдены. Попробуйте снова."
        if callback.inline_message_id:
            await callback.bot.edit_message_text(
                text=text,
                inline_message_id=callback.inline_message_id,
                parse_mode="HTML"
            )
        elif callback.message:
            await callback.message.edit_text(text)
        await callback.answer()
        return
    
    # Записываем данные в таблицу
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Sheets).where(Sheets.id == table_id)
        )
        table = result.scalars().first()
        
        if table:
            # Записываем данные в выбранную таблицу
            await handle_activation(user_id, query_text, callback, callback.bot, table.name)
        else:
            text = "Таблица не найдена"
            if callback.inline_message_id:
                await callback.bot.edit_message_text(
                    text=text,
                    inline_message_id=callback.inline_message_id,
                    parse_mode="HTML"
                )
            elif callback.message:
                await callback.message.edit_text(text)
            await callback.answer()
            return
    
    # Очищаем сохраненные данные
    user_pending_data.pop(user_id, None)
    await callback.answer()


# Команда добавления таблицы
@router.message(Command("add_table"))
async def cmd_add_table(message: types.Message, state: FSMContext):
    await message.answer("Введите название таблицы (как она называется в Google Sheets):")
    await state.set_state(AddTableState.waiting_for_name)

@router.message(AddTableState.waiting_for_name)
async def process_table_name(message: types.Message, state: FSMContext):
    table_name = message.text.strip()
    user_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Проверяем, нет ли уже такой таблицы у пользователя
        result = await session.execute(
            select(Sheets).where(Sheets.user_id == user_id, Sheets.name == table_name)
        )
        existing = result.scalars().first()
        
        if existing:
            await message.answer(f"Таблица '{table_name}' уже добавлена.")
        else:
            # Добавляем новую таблицу
            new_table = Sheets(user_id=user_id, name=table_name)
            session.add(new_table)
            await session.commit()
            await message.answer(f"Таблица '{table_name}' успешно добавлена!")
    
    await state.clear()


# Команда просмотра таблиц
@router.message(Command("my_tables"))
async def cmd_my_tables(message: types.Message):
    user_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Sheets).where(Sheets.user_id == user_id)
        )
        tables = result.scalars().all()
    
    if not tables:
        await message.answer("У вас пока нет добавленных таблиц. Используйте /add_table чтобы добавить.")
    else:
        text = "Ваши таблицы:\n\n"
        for i, table in enumerate(tables, 1):
            text += f"{i}. {table.name} (ID: {table.id})\n"
        await message.answer(text)


# Команда удаления таблицы
@router.message(Command("delete_table"))
async def cmd_delete_table(message: types.Message):
    user_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Sheets).where(Sheets.user_id == user_id)
        )
        tables = result.scalars().all()
    
    if not tables:
        await message.answer("У вас нет таблиц для удаления.")
        return
    
    # Показываем кнопки удаления
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=f"❌ {table.name}", callback_data=f"delete_table:{table.id}")]
            for table in tables
        ]
    )
    
    await message.answer("Выберите таблицу для удаления:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("delete_table:"))
async def handle_delete_table_callback(callback: types.CallbackQuery):
    table_id = int(callback.data.replace("delete_table:", "", 1))
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Sheets).where(Sheets.id == table_id, Sheets.user_id == user_id)
        )
        table = result.scalars().first()
        
        if table:
            await session.delete(table)
            await session.commit()
            await callback.message.edit_text(f"Таблица '{table.name}' удалена.")
        else:
            await callback.message.edit_text("Таблица не найдена или нет доступа.")
    
    await callback.answer()


async def main():
    try:
        # Создаем таблицы БД при старте
        await create_tables()
        
        bot = Bot(token=token)
        dp = Dispatcher()

        dp.include_router(router)
        
    
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        print(e)
        await main()

if __name__ == "__main__":
    asyncio.run(main())