from typing import List
from vkbottle.bot import BotLabeler
from . import pin_action
from . import gpt

labelers: List[BotLabeler] = [pin_action.labeler, gpt.labeler]
