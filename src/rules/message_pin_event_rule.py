from vkbottle.bot import Message
from vkbottle.dispatch import rules


class MessagePinEventRule(rules.ABCRule[Message]):
    async def check(self, message: Message) -> dict | bool:
        if not message.action:
            return False
        if not message.action.type.value == "chat_pin_message":
            return False

        response = await message.ctx_api.messages.get_by_conversation_message_id(message.peer_id,
                                                                                 [message.action.conversation_message_id])
        return {"event_message": response.items[0]}
