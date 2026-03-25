from api_sheets import *
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker, declarative_base


token = '8272142309:AAGIHjAHT0iXayrPeJzUX6JM9X-OR6PPlBE'

async_engine = create_async_engine("sqlite+aiosqlite:///vpn_bot.db", echo=False)

Base = declarative_base()

class Info(Base):
    __tablename__ = "tables_names"
    id = Column(Integer, primary_key=True)
    name = Column(String)


# Создание таблиц (асинхронно)
async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Создание фабрики асинхронных сессий
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Асинхронная функция для создания/обновления info
async def create_or_update_info(name: str, user_id: int):
    async with AsyncSessionLocal() as session:
        # Ищем запись с указанным id
        result = await session.execute(select(Info).filter(Info.id == user_id))
        info = result.scalar_one_or_none()
        
        if info:
            # Если запись существует, обновляем ее
            info.name = name
            await session.commit()
            await session.refresh(info)
            print(f"Запись с id={user_id} обновлена: {name}")
        else:
            # Если записи нет, создаем новую
            info = Info(id=user_id, name=name)
            session.add(info)
            await session.commit()
            await session.refresh(info)
            print(f"Создана новая запись с id={user_id}: {name}")
        
        return info



router = Router()
async def handle_activation(user_id: int, query_text: str, call: types.CallbackQuery, bot: Bot):
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
        status = add_order(intrance, extrance)
        if status:
            await bot.edit_message_text(
                text=f"<tg-emoji emoji-id='5249448542593883237'>✅</tg-emoji> Успешно добавлено в систему учета\n\n➤ <b>Пришло:</b> {intrance}\n<b>➤ Отправлено:</b> {extrance}\n<b>➤ Итоговая прибыль:</b> {intrance - extrance}",
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
    await handle_activation(callback.from_user.id, query_text, callback, callback.bot)
    await callback.answer("Строчка записана")
    



async def main():
    try:
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