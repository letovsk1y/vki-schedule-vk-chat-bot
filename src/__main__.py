import os
os.chdir(os.path.dirname(__file__))
from src.app import bot

if __name__ == "__main__":
    bot.run_forever()
