from typing import List
from vkbottle.bot import BotLabeler
from . import pin_action

labelers: List[BotLabeler] = [pin_action.labeler]
