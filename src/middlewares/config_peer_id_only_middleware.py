from vkbottle import BaseMiddleware
from vkbottle.bot import Message
import src.config


class ConfigPeerIdOnlyMiddleware(BaseMiddleware[Message]):
    async def pre(self):
        if self.event.peer_id != src.config.CHAT_PEER_ID:
            self.stop("peer_id is not compatible for ConfigPeerIdOnlyMiddleware")
