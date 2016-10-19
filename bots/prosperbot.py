'''prosperbot.py: bot for prosper stuff'''
from os import path
from datetime import datetime, timedelta

import pandas_datareader.web
import discord
from discord.ext import commands

from prosper.common.prosper_logging import create_logger
from prosper.common.prosper_config import get_config

HERE = path.abspath(path.dirname(__file__))
CONFIG_ABSPATH = path.join(HERE, 'prosperbot_config.cfg')
CONFIG = get_config(CONFIG_ABSPATH)
LOGGER = create_logger(
    'prosperbot',
    '.',
    CONFIG
)

bot = commands.Bot(
    command_prefix=CONFIG.get('OAUTH', 'bot_prefix'),
    description='ProsperBot is BESTBOT'
)

@bot.event
async def on_ready():
    LOGGER.info('Logged in as')
    LOGGER.info(bot.user.name)
    LOGGER.info(bot.user.id)
    LOGGER.info('------')

@bot.command(pass_context=True)
async def quote(ctx):
    await bot.say(ctx)
