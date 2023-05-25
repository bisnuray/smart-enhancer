"""
Author: Bisnu Ray , Nafis Muhtadi
GitHub: https://github.com/bisnuray/
GitHub: https://github.com/NafisMuhtadi
Description: A Telegram bot to enhance photos using the Remini API.
"""

import os
import base64
import hashlib
import httpx
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = Bot(token='YOUR_TOKEN_HERE')   # REPLACE YOUR TELEGRAM BOT TOKEN HERE
dp = Dispatcher(bot)

API_KEY = "REMINI_API_KEY"   # REPLACE YOUR REMINI API KEY THAT HAS CREDITS
CONTENT_TYPE = "image/jpeg"
_TIMEOUT = 60
_BASE_URL = "https://developer.remini.ai/api"

def _get_image_md5_content(file_path: str) -> tuple[str, bytes]:
    with open(file_path, "rb") as fp:
        content = fp.read()
        image_md5 = base64.b64encode(hashlib.md5(content).digest()).decode("utf-8")
    return image_md5, content

async def enhance_photo_and_send_link(file_path: str, chat_id: int):
    image_md5, content = _get_image_md5_content(file_path)

    async with httpx.AsyncClient(
        base_url=_BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
    ) as client:
        response = await client.post(
            "/tasks",
            json={
                "tools": [
                    {"type": "face_enhance", "mode": "beautify"},
                    {"type": "background_enhance", "mode": "base"}
                ],
                "image_md5": image_md5,
                "image_content_type": CONTENT_TYPE
            }
        )
        assert response.status_code == 200
        body = response.json()
        task_id = body["task_id"]

        response = await client.put(
            body["upload_url"],
            headers=body["upload_headers"],
            content=content,
            timeout=_TIMEOUT
        )
        assert response.status_code == 200

        response = await client.post(f"/tasks/{task_id}/process")
        assert response.status_code == 202

        for i in range(50):
            response = await client.get(f"/tasks/{task_id}")
            assert response.status_code == 200

            if response.json()["status"] == "completed":
                break
            else:
                await asyncio.sleep(2)  # Use asyncio.sleep() instead of sleep()

        output_url = response.json()["result"]["output_url"]
        await bot.send_message(chat_id, f"<b>Enhanced photo: </b> {output_url}", parse_mode='html')

    # Remove the downloaded photo file
    os.remove(file_path)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    # Create the inline keyboard and buttons
    keyboard = InlineKeyboardMarkup(row_width=2)
    dev_button = InlineKeyboardButton("Dev 👨‍💻", url="https://t.me/TheSmartBisnu")
    update_button = InlineKeyboardButton("Update ✅", url="https://t.me/PremiumNetworkTeam")
    keyboard.add(dev_button, update_button)

    # Send the welcome message with the inline keyboard
    await bot.send_message(
        message.chat.id,
        "<b>Welcome! I am a Smart Enhancer BOT. Please Send me a photo to enhance.</b>",
        parse_mode='html',
        reply_markup=keyboard
    )

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file_path = os.path.join(os.getcwd(), f"{photo.file_unique_id}.jpg")
    await photo.download(file_path)
    await bot.send_message(message.chat.id, "<b>Enhancing your photo...</b>", parse_mode='html')

    # Call the enhancement function and pass the file path and chat ID
    await enhance_photo_and_send_link(file_path, message.chat.id)

@dp.message_handler()
async def handle_invalid_message(message: types.Message):
    await bot.send_message(message.chat.id, "<b>I am not allowed to receive any text messages or emojis.\n\nPlease send only photos.</b>", parse_mode='html')

# Start the bot
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    loop.run_forever()
