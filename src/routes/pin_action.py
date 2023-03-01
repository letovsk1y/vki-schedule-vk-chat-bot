from typing import List, Optional
from vkbottle.bot import BotLabeler, Message

from src import config, parser, app
from src.rules import MessagePinEventRule
from src.utils import get_message_by_id, json_read_async, AttachmentString, json_write_async

labeler = BotLabeler()


# event_message - pinned message, for reference - check MessagePinEventRule
@labeler.chat_message(MessagePinEventRule())
async def pin(message: Message, event_message: Message):
    schedule_data: dict = await json_read_async(config.SCHEDULE_DATA_PATH)

    try:
        # parse schedule file link
        link = await parser.schedule.get_link(app.aiohttp_session)
    except:
        # if link for schedule file not found, we will use old link
        link = schedule_data["link"]

    # convert list of attachment strings to our list of AttachmentString object
    schedule_attachments: List[AttachmentString] = AttachmentString.to_attachment_list(schedule_data["attachments"])
    schedule_attachments_before = []

    notify_message_id: Optional[int] = None

    # if schedule_data is empty, or link was changed
    if len(schedule_attachments) == 0 or schedule_data["link"] != link:
        data = await message.ctx_api.messages.send(
            peer_ids=[message.peer_id],
            message="ой тут обнова расписания щя погоди, качаю"
        )
        notify_message_id = data[0].conversation_message_id
        # save old schedule_attachments to remove it from pinned message
        schedule_attachments_before = schedule_attachments.copy()
        schedule_attachments = []

        _, pages = await parser.schedule.parse(app.aiohttp_session, link)
        uploaded_attachments = await parser.schedule.upload(app.photo_message_uploader, pages)

        # update schedule_data file with new schedule
        await json_write_async(config.SCHEDULE_DATA_PATH, {"link": link, "attachments": uploaded_attachments})

        # convert list of uploaded attachment strings to our list of AttachmentString object
        # and add it to schedule_attachments list
        for attachment in uploaded_attachments:
            schedule_attachments.append(AttachmentString(attachment))

    pin_attachments: List[str] = []
    for attachment in event_message.attachments:
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

    if AttachmentString.to_attachment_list(pin_attachments[:10]) == \
            AttachmentString.to_attachment_list(event_message.attachments):
        # if attachments are the same, we will not send anything
        return

    # if there is no attachments and message text we can not send message
    if len(pin_attachments) == 0 and len(event_message.text) == 0:
        await message.answer("Не могу закрепить, отсуствует доступный контент")
        return

    # this variable needed to get id of first message we send because we want to pin first message
    pin_message_id = -1
    # in one message there can be only 10 attachments, that is the reason why for loop here
    for i in range(len(pin_attachments) // 10 + 1):
        if notify_message_id:
            await message.ctx_api.messages.delete(message_id=notify_message_id, peer_id=message.peer_id, delete_for_all=True)
        # if pinned message is a reply to another message, we will send message with this reply too
        if event_message.reply_message:
            # to reply to message we need to get message object first
            reply_message = await get_message_by_id(message.ctx_api, message.peer_id, message.conversation_message_id)
            await reply_message.reply(event_message.text, ",".join(pin_attachments))

            data = await message.ctx_api.messages.send(
                peer_ids=[message.peer_id],
                message=event_message.text,
                attachment=",".join(pin_attachments[i * 10 - 1: (i + 1) * 10] if i > 0 else pin_attachments[:10]),
                random_id=0,
                reply_to=reply_message.conversation_message_id)
            message_id = data[0].conversation_message_id
        else:
            data = await message.ctx_api.messages.send(
                peer_ids=[message.peer_id],
                message=event_message.text,
                attachment=",".join(pin_attachments[i * 10 - 1: (i + 1) * 10] if i > 0 else pin_attachments[:10]),
                random_id=0)
            message_id = data[0].conversation_message_id
        if i == 0:
            pin_message_id = message_id

    if pin_message_id != -1:
        await message.ctx_api.messages.pin(
            peer_id=message.peer_id,
            conversation_message_id=pin_message_id
        )
