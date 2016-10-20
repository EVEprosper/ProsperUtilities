'''prosperbot.py: bot for prosper stuff'''
from os import path, makedirs
from datetime import datetime, timedelta

#import requests
import pandas as pd
import pandas_datareader.data as web
import discord
from discord.ext import commands
from tinydb import TinyDB, Query
import ujson as json

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
CACHE_ABSPATH = path.join(HERE, CONFIG.get('CACHE', 'cache_path'))
if not path.exists(CACHE_ABSPATH):
    makedirs(CACHE_ABSPATH)
def update_cache(db, insertobj, query_field):
    '''single func for updating tinydb cache'''
    u_query = Query()
    try:
        db.remove(u_query.ticker == query_field) #TODO: make this more dynamic
        db.insert(insertobj)
    except Exception as err_message:
        LOGGER.error(
            'EXCEPTION: unable to update tinydb ' +
            '\r\texception={0}'.format(err_message) +
            '\r\tinsertobj={0}'.format(insertobj) +
            '\r\tquery_field={0}'.format(query_field)
        )

COMPANY_CACHE_TIME = int(CONFIG.get('CACHE', 'company_cache_time')) * 3600 #seconds
COMPANY_CACHE_FILE = path.join(CACHE_ABSPATH, CONFIG.get('CACHE', 'company_cache_file'))
COMPANY_DB = TinyDB(COMPANY_CACHE_FILE)
def check_company_cache(ticker, company_cache_time=COMPANY_CACHE_TIME):
    '''check to see if we already know what the name is'''
    #TODO: tinyDB records
    LOGGER.info('checking tinydb for ' + ticker)
    now = datetime.now()
    c_query = Query()
    record = COMPANY_DB.search(c_query.ticker == ticker)
    if record:
        company_info = record[0]
        LOGGER.debug(company_info)
        LOGGER.info('--record found')
        cache_time = datetime.strptime(company_info['cache_time'], '%Y-%m-%d %H:%M:%S')
        company_name = company_info['company_name']
        record_age = now - cache_time

        if record_age.total_seconds() > COMPANY_CACHE_TIME:
            LOGGER.info('--cache too old, refreshing record')
            return None
        else:
            LOGGER.info('--company name found in cache: ' + company_name)
            return company_name
    else:
        LOGGER.info('ticker not found in cache: ' + ticker)
        return None

def update_company_cache(ticker, company_name):
    '''push updates to cache for later'''
    if company_name == 'N/A':
        return
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    insertobj = {
        'ticker':ticker,
        'company_name':company_name,
        'cache_time':now_str
    }
    LOGGER.info('pushing update to company_cache')
    update_cache(COMPANY_DB, insertobj, ticker)


TICKER_FORMAT = CONFIG.get('PD_DATAREADER', 'ticker_format')
TICKER_LOOKUP = CONFIG.get('PD_DATAREADER', 'ticker_lookup')
def get_company_name(ticker, cache_override=False, ticker_format=TICKER_FORMAT):
    '''Resolve TICKER->company name for easy readability'''
    ticker = ticker.upper()
    cached_name = check_company_cache(ticker)
    if cached_name and not cache_override:
        return cached_name

    LOGGER.info('fetching ticker from internet: ' + ticker)
    ticker_url = '{base_url}?s={ticker}&f={ticker_format}'.format(
        base_url=TICKER_LOOKUP,
        ticker=ticker,
        ticker_format=ticker_format
    )
    LOGGER.debug('URL:' + ticker_url)
    ticker_data = pd.read_csv(ticker_url)
    company_name = ticker_data.columns.values[0] #only fetch one company name
    update_company_cache(ticker, company_name)
    return company_name

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
async def who(symbol:str, cache_override:str):
    '''!who [TICKER] returns company name'''
    cache_override_bool = False
    if cache_override.lower() == 'please':
        cache_override_bool = True
    lookup_start = datetime.now()
    company_name = get_company_name(symbol, cache_override_bool)
    lookup_elapsed = datetime.now() - lookup_start

    if company_name == 'N/A':
        await bot.say('Unable to resolve stock ticker: ' + symbol +
            '\truntime=' + str(lookup_elapsed)
        )
    else:
        await bot.say(company_name +
            '\truntime=' + str(lookup_elapsed)
        )

@bot.command(pass_context=True)
async def echo(ctx):
    await bot.say('echo: {0}'.format(ctx.message.content))

BOT_TOKEN = CONFIG.get('OAUTH', 'bot_token')
bot.run(BOT_TOKEN)
