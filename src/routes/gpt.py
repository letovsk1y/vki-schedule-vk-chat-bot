import traceback
from pprint import pprint

import ujson
from vkbottle.bot import BotLabeler, Message
from src import config, app

labeler = BotLabeler()
labeler.vbml_ignore_case = True

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

@labeler.chat_message()
async def gpt(message: Message):
    if not message.mention:
        return
    if message.mention.id != config.BOT_ID:
        return
    if len(message.text) < 3:
        await message.reply("Не удалось выполнить запрос, запрос слишком короткий")

    app.typing_peers.add(config.CHAT_PEER_ID)
    await app.typing_interval()
    text = ""
    try:
        response = await app.aiohttp_session.post("https://chatgpt.ddiu.me/api/generate", data=ujson.dumps({
            "messages": [
                {"role": "system", "content": config.GPT_SYSTEM_ROLE},
                {"role": "user", "content": message.text}
            ]
        }), headers=headers)
        text = await response.text()
    except Exception:
        app.typing_peers.clear()
        pprint(traceback.format_exc())
        await message.reply("Не удалось выполнить запрос, попробуйте позже")
        return

    code_braces = len(text.split("```")) - 1
    code_braces -= code_braces % 2

    if code_braces > 0:
        is_opened = False
        code_braces = text.split("```", code_braces)
        formatted_code_braces = code_braces.copy()
        for i, item in enumerate(code_braces):
            if is_opened:
                link = None
                try:
                    response = await app.aiohttp_session.post("https://pastebin.com/api/api_post.php", data={
                        "api_dev_key": config.PASTEBIN_API_KEY,
                        "api_option": "paste",
                        "api_paste_format": "cpp",
                        "api_paste_code": item,
                    })
                    link = await response.text(encoding="utf-8")
                except Exception:
                    pass

                if link:
                    formatted_code_braces.insert(i, f"\nДалее код: {link}\n")
                    formatted_code_braces.pop(i + 1)

            is_opened = not is_opened

        text = ''.join(formatted_code_braces)

    app.typing_peers.clear()
    await message.reply(message=text)
