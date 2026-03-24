from api_sheets import *
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
import asyncio


token = '8272142309:AAGIHjAHT0iXayrPeJzUX6JM9X-OR6PPlBE'


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