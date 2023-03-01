from vkbottle import Bot, CtxStorage, PhotoMessageUploader, LoopWrapper
from typing import Optional, List

from src import parser
from src.routes import labelers
from src.middlewares import NoBotMiddleware, ConfigPeerIdOnlyMiddleware
import aiohttp
import config
from src.utils import json_read_async, AttachmentString, json_write_async, get_message_by_id


async def on_startup():
    global photo_message_uploader
    photo_message_uploader = PhotoMessageUploader(api=bot.api)
    await schedule_check(True)


async def on_shutdown():
    await bot.api.messages.send(peer_ids=[config.CHAT_PEER_ID], message="Пизда я упал", random_id=0)
    await aiohttp_session.close()


aiohttp_session = aiohttp.ClientSession()
photo_message_uploader: Optional[PhotoMessageUploader] = None
ctx_storage = CtxStorage()
lw = LoopWrapper(on_startup=[on_startup()], on_shutdown=[on_shutdown()])

bot = Bot(config.BOT_TOKEN, loop_wrapper=lw)

for labeler in labelers:
    bot.labeler.load(labeler)

bot.labeler.message_view.register_middleware(NoBotMiddleware)
bot.labeler.message_view.register_middleware(ConfigPeerIdOnlyMiddleware)


# first_time arg, needed to send custom messages for first start
@lw.interval(minutes=config.SCHEDULE_CHECK_INTERVAL)
async def schedule_check(first_time: bool = False):
    schedule_data: dict = await json_read_async(config.SCHEDULE_DATA_PATH)

    try:
        # parse schedule file link
        link = await parser.schedule.get_link(aiohttp_session)
    except KeyError:
        # if link for schedule file not found, we will use old link
        link = schedule_data["link"]

    # convert list of attachment strings to our list of AttachmentString object
    schedule_attachments: List[AttachmentString] = AttachmentString.to_attachment_list(schedule_data["attachments"])
    schedule_attachments_before = []

    # if schedule_data is empty, or link was changed
    if len(schedule_attachments) == 0 or schedule_data["link"] != link:
        # save old schedule_attachments to remove it from pinned message
        schedule_attachments_before = schedule_attachments.copy()
        schedule_attachments = []

        # parse attachments and upload to vk server
        _, pages = await parser.schedule.parse(aiohttp_session, link)
        uploaded_attachments = await parser.schedule.upload(photo_message_uploader, pages)

        # update schedule_data file with new schedule
        await json_write_async(config.SCHEDULE_DATA_PATH, {"link": link, "attachments": uploaded_attachments})

        # convert list of uploaded attachment strings to our list of AttachmentString object
        # and add it to schedule_attachments list
        for attachment in uploaded_attachments:
            schedule_attachments.append(AttachmentString(attachment))

    # getting chat information about pinned message id
    chat_info = await bot.api.messages.get_conversations_by_id([config.CHAT_PEER_ID])
    chat_info = chat_info.items[0]
    if chat_info.chat_settings.pinned_message is None:
        # if pinned message not found, we will not send anything,
        # but if this function was called first time, we will notify about it
        if first_time:
            await bot.api.messages.send(
                peer_ids=[config.CHAT_PEER_ID],
                message="Я поднялся",
                random_id=0
            )
        return

    # getting message object from pinned message id
    pinned_message = await get_message_by_id(
        bot.api,
        config.CHAT_PEER_ID,
        chat_info.chat_settings.pinned_message.conversation_message_id
    )

    pin_attachments: List[str] = []
    for attachment in pinned_message.attachments:
        # converting every pinned message attachment to our Attachment String object
        attachment = AttachmentString(attachment)
        # some vk attachments have a specific data, and that the reason why we need to skip it, for example - link
        if attachment.type not in config.INCLUDED_ATTACHMENTS:
            continue

        # skip attachments with old or current schedule
        if attachment in schedule_attachments or attachment in schedule_attachments_before:
            continue

        # converting attachments to string due to vk format - "{type}{owner_id}_{id}_{access_key},..."
        pin_attachments.append(str(attachment))

    # adding to the end of attachment list schedule attachments
    # converting schedule attachments to string due to vk format - "{type}{owner_id}_{id}_{access_key},..."
    pin_attachments += [str(i) for i in schedule_attachments]

    # if there is no attachments and message text we can not send message
    if len(pin_attachments) == 0 and len(pinned_message.text) == 0:
        return

    if AttachmentString.to_attachment_list(pin_attachments[:10]) == \
            AttachmentString.to_attachment_list(pinned_message.attachments):
        # if attachments are the same, we will not send anything,
        # but if this function was called first time, we will notify about it
        if first_time:
            await bot.api.messages.send(
                peer_ids=[config.CHAT_PEER_ID],
                message="Я поднялся, обновлений расписания не было",
                random_id=0
            )
        return

    # this variable needed to get id of first message we send because we want to pin first message
    pin_message_id = -1
    # in one message there can be only 10 attachments, that is the reason why for loop here
    for i in range(len(pin_attachments) // 10 + 1):
        # if pinned message is a reply to another message, we will send message with this reply too
        if pinned_message.reply_message:
            # to reply to message we need to get message object first
            reply_message = await get_message_by_id(bot.api, config.CHAT_PEER_ID, pinned_message.conversation_message_id)
            await reply_message.reply(pinned_message.text, ",".join(pin_attachments))

            data = await bot.api.messages.send(
                peer_ids=[config.CHAT_PEER_ID],
                message=pinned_message.text,
                attachment=",".join(pin_attachments[i * 10 - 1: (i + 1) * 10] if i > 0 else pin_attachments[:10]),
                random_id=0,
                reply_to=reply_message.conversation_message_id)
            message_id = data[0].conversation_message_id
        else:
            data = await bot.api.messages.send(
                peer_ids=[config.CHAT_PEER_ID],
                message=pinned_message.text,
                attachment=",".join(pin_attachments[i * 10 - 1: (i + 1) * 10] if i > 0 else pin_attachments[:10]),
                random_id=0)
            message_id = data[0].conversation_message_id
        if i == 0:
            pin_message_id = message_id

    if pin_message_id == -1:
        return

    await bot.api.messages.pin(
        peer_id=config.CHAT_PEER_ID,
        conversation_message_id=pin_message_id
    )

    await bot.api.messages.send(
        peer_ids=[config.CHAT_PEER_ID],
        message="Расписание было обновлено" if not first_time else "Я поднялся, расписание было обновлено",
        random_id=0
    )
