from src.app import bot
import loguru

if __name__ == "__main__":
    # use it, if you running it on linux
    # import uvloop
    # uvloop.install()

    bot.run_forever()
