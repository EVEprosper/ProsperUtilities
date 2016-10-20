'''prosperbot.py: bot for prosper stuff'''
from os import path
from datetime import datetime, timedelta

#import requests
import pandas as pd
import pandas_datareader.data as web
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
    CONFIG,
    'DEBUG'
)

TICKER_FORMAT = CONFIG.get('PD_DATAREADER', 'ticker_format')
TICKER_LOOKUP = CONFIG.get('PD_DATAREADER', 'ticker_lookup')
def get_company_name(ticker, ticker_format=TICKER_FORMAT):
    '''Resolve TICKER->company name for easy readability'''
    cached_name = check_company_cache(symbol)
    if cached_name:
        return cached_name

    ticker_url = '{base_url}?s={ticker}&f={ticker_format}'.format(
        base_url=TICKER_LOOKUP,
        ticker=ticker,
        ticker_format=ticker_format
    )
    ticker_data = pd.read_csv(ticker_url)
    return ticker_data.columns.values[0] #only fetch one company name

QUOTE_SOURCE = CONFIG.get('PD_DATAREADER', 'quote_source')
DATERANGE = CONFIG.get('PD_DATAREADER', 'DATERANGE')
def get_stock_data(ticker, quote_source=QUOTE_SOURCE, daterange=DATERANGE):
    '''fetch OHLC data for plotting'''
    start_date = datetime.today() - timedelta(days=int(daterange))
    end_date = datetime.today()

    try:
        LOGGER.info('Fetching data for: ' + str(ticker))
        LOGGER.debug(
            '\r\tticker={0}'.format(ticker) +
            '\r\tquote_source={0}'.format(ticker) +
            '\r\tstart_date={0}'.format(start_date) +
            '\r\tend_date={0}'.format(end_date)
        )
        stock_data = web.DataReader(ticker, quote_source, start_date, end_date)
    except Exception as err_message:
        raise err_message

    return stock_data

PNG_HEIGHT = CONFIG.get('PD_DATAREADER', 'png_height')
PNG_WIDTH  = CONFIG.get('PD_DATAREADER', 'png_width')
def make_plot(data, ticker, filepath, png_height=PNG_HEIGHT, png_width=PNG_WIDTH):
    '''make a plot of the OHLC data'''
    company_name = get_company_name(ticker)
    pass
CHART_CACHE_TIME = None
def get_plot(ticker, filepath=None, chart_cache_time=CHART_CACHE_TIME):
    '''check to see if file is already generated'''
    #TODO: tinyDB records of plots on file
    return None

COMPANY_CACHE_TIME = None #TODO CONFIG.get()
def check_company_cache(ticker, company_cache_time=COMPANY_CACHE_TIME):
    '''check to see if we already know what the name is'''
    #TODO: tinyDB records
    return None

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
async def quote(ctx, symbol:str):
    plot_file = get_plot(symbol)
    if get_plot:
        #if cached, return plot ezpz
        await bot.upload(plot_file)
    try:
        data = get_stock_data(symbol)
    except Exception as err_message:
        LOGGER.warning('Invalid stock ticker: ' + symbol)
        await bot.say('Unable to resolve stock ticker: ' + symbol)
        return


    await bot.say(get_company_name(symbol)) #TODO: get_company_name moved into plotting func

@bot.command()
async def who(symbol:str):
    '''!who [TICKER] returns company name'''
    company_name = get_company_name(symbol)

    if company_name == 'N/A':
        await bot.say('Unable to resolve stock ticker: ' + symbol)
    else:
        await bot.say(company_name)

@bot.command(pass_context=True)
async def echo(ctx):
    await bot.say('echo: {0}'.format(ctx.message.content))

BOT_TOKEN = CONFIG.get('OAUTH', 'bot_token')
bot.run(BOT_TOKEN)
