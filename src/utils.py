import aiofiles
import ujson
from vkbottle import API
from vkbottle.bot import Message
from vkbottle_types.objects import MessagesMessageAttachment
from typing import Optional, List


async def get_message_by_id(api: API, peer_id: int, conversation_message_id: int) -> Message:
    response = await api.messages.get_by_conversation_message_id(peer_id, [conversation_message_id])
    return response.items[0]


async def json_read_async(path: str):
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        response = await f.read()

    return ujson.loads(response)


async def json_write_async(path: str, data):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(ujson.dumps(data))


# class to help work with attachments
class AttachmentString:
    type: str = ""
    id: int = -1
    owner_id: int = -1
    access_key: Optional[str] = None

    def __init__(self, attachment: MessagesMessageAttachment | str):
        try:
            if isinstance(attachment, MessagesMessageAttachment):
                attachment = attachment.dict()
                self.type = attachment["type"].value
                self.id = int(attachment[self.type]["id"])
                self.owner_id = int(attachment[self.type]["owner_id"])
                self.access_key = attachment[self.type]["access_key"] if "access_key" in attachment[self.type].keys() else None
            else:
                attachment = attachment.split("_")
                self.id = int(attachment[1])
                self.access_key = attachment[2] if len(attachment) > 1 else None
                _owner_id = ""
                for char in list(attachment[0]):
                    if char.isalpha():
                        self.type += char
                    else:
                        _owner_id += char
                self.owner_id = int(_owner_id)
        except TypeError:
            pass

    @staticmethod
    def to_attachment_list(attachments: List[MessagesMessageAttachment | str]) -> list:
        res = []
        for attachment in attachments:
            res.append(AttachmentString(attachment))
        return res

    def __eq__(self, other):
        return self.type == other.type and self.id == other.id and self.owner_id == other.owner_id

    def __str__(self):
        return "{}{}_{}_{}".format(self.type, self.owner_id, self.id, self.access_key) if self.access_key \
            else "{}{}_{}".format(self.type, self.owner_id, self.id)
