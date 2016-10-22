'''prosperbot.py: bot for prosper stuff'''
from os import path, makedirs
from datetime import datetime, timedelta

import requests
import demjson
from nltk import download as nltk_download
import nltk.sentiment as sentiment
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

TEXT_ANALYZER = None
if not nltk_download('vader_lexicon'):
    LOGGER.error('unable to load vader_lexicon for text analysis')
else:
    TEXT_ANALYZER = sentiment.vader.SentimentIntensityAnalyzer()

TOP_ENTRIES = int(CONFIG.get('PD_DATAREADER', 'articles_top_entries'))
ARTICLES_URI = CONFIG.get('PD_DATAREADER', 'articles_uri')
ARTICLES_EXCLUDE = CONFIG.get('PD_DATAREADER', 'articles_exclude').split(',')
def get_news(ticker:str, percent:float, top_entries=TOP_ENTRIES):
    '''fetch google news and return most relevant entry
        NOTE: using nltk sentiment analysis on headlines
    '''
    if not TEXT_ANALYZER:
        return 'Sentiment analyzer broken, ask again later'
    ## Get relevant articles from google finance endpoint ##
    params = {
        'q':ticker,
        'output':'json'
    }

    req = requests.get(
        ARTICLES_URI,
        params=params
    )
    articles = demjson.decode(req.text) #fix poorly formatted result

    ## Pick a few articles off the endpoint ##
    article_dict = {} #headline_str:url_str
    for block in articles['clusters']:
        #LOGGER.debug(block)
        if int(block['id']) == -1:
            LOGGER.debug(
                '-- found end of list ' + str(len(article_dict)) + ' hits'
            )
            continue
        if 'a' in block:
            for article in block['a']:
                LOGGER.debug(article)
                if article['s'] in ARTICLES_EXCLUDE:
                    LOGGER.debug('-- skipping because of source')
                    continue
                headline = article['t']
                url = article['u']
                article_dict[headline] = url

                if len(article_dict) >= TOP_ENTRIES:
                    LOGGER.debug(
                        '-- enough entries' + str(len(article_dict)) + ' hits'
                    )
                    break

    ## Grade the headlines gathered ##
    positive = True
    if percent < 0:
        positive = False
    best_headline = ''
    best_url = ''
    best_score = 0.0
    for headline, url in article_dict.items():
        score_obj = TEXT_ANALYZER.polarity_scores(headline)
        bool_update = False
        if positive and score_obj['compound'] > best_score:
            bool_update = True
        elif (not positive) and score_obj['compound'] < best_score:
            bool_update = True

        if bool_update:
            #ties go to first entry in items() list
            best_score = score_obj['compound']
            best_headline = headline
            best_url = url
    LOGGER.debug(
        'results' +
        '\r\tbest_headline={0}'.format(best_headline) +
        '\r\tbest_url={0}'.format(best_url) +
        '\r\tbest_score={0}'.format(best_score)
    )
    result_str = best_url + '\t(' + str(best_score) + ')'
    return result_str

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
async def price(symbol:str, cache_override='nope'):
    '''!price [TICKER] returns 'last' and 'change_prct' of stock'''
    cache_override_bool = False
    if cache_override.lower() == 'please':
        cache_override_bool = True
    lookup_start = datetime.now()
    company_name = get_company_name(symbol, cache_override_bool)

    if company_name == 'N/A':
        await bot.say('Unable to resolve stock ticker: ' + symbol)
        return
    else:
        price_data = web.get_quote_yahoo([symbol])
        percent = str(price_data.get_value(symbol, 'change_pct'))
        percent = float(percent.replace('%',''))
        news_url = get_news(symbol, percent)
        #await bot.say(price_data[0])
        await bot.say(
            '`$' + symbol.upper() + '`\t' + company_name +
            '\n$' + str(price_data.get_value(symbol, 'last')) +
            '\t' + str(price_data.get_value(symbol, 'change_pct')) +
            '\t@' + str(price_data.get_value(symbol, 'time')) +
            '\nPE ' + str(price_data.get_value(symbol, 'PE')) +
            '\tshort_ratio ' + str(price_data.get_value(symbol, 'short_ratio')) +
            '\n' + news_url
        )
@bot.command()
async def who(symbol:str, cache_override='nope'):
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
