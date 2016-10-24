# Prosper Bot
ProsperBot is meant as a easy utility for Discord for getting market data.

Though prosperbot is designed for Prosper stuff, there's nothing stopping others from putting their own bot token and running a version of prosperbot on thier own.

# Installing Prosper Bot
ProsperBot is written in python3.5 and uses [Discord.py](https://github.com/Rapptz/discord.py) for its bot functionality

TODO: setup.py?

**Additional requirements:**
* [tinyDB](http://tinydb.readthedocs.io/en/latest/) as a cache layer
* [pandas_datareader](https://pandas-datareader.readthedocs.io/en/latest/) for fetching stock quotes
* demjson for formatting Google "json"
* ujson as speed-up for tinyDB and json replacement
* [NLTK](http://www.nltk.org/) for sentiment analysis
* [requests](http://docs.python-requests.org/en/master/) for generic HTTP fetching
* [ProsperCommon](https://github.com/EVEprosper/ProsperCommon) for logging/config

**Running ProsperBot**

1. `virtualenv -p python3 venv_prosperbot`
2. activate virtualenv
3. `pip install -r bot_requirements.txt`
4. `python prosperbot.py`

**Environment Stuff**
* `prosperbot_config.cfg` is tracked by git.  To fill out secrets copy to `prosperbot_config_local.cfg` and complete configuration
* ProsperBot has been tested to work on Windows and Ubuntu16

# Prosper Bot Functions
ProsperBot comes with a wide array of functions using the `discord.ext` library

## !who [ticker] [please (OPTIONAL)]
`!who` is for translating stock ticker/symbol to its common/company name.

`!who` responses are cached in tinyDB for 30 days.  This makes responses extremely snappy when looking up company names (both as `!who` and other funcs that need the information).

To clear/refresh the cache, use the keyword `please` in your request and the company name will be fetched again on the yahoo endpoint.

## !price [ticker] [please (OPTIONAL)]
`!price` returns a summary of the current price of a stock.  This endpoint is furnished by yahoo through `pandas_datareader.data.get_quote_yahoo` function

`!price` also hits the following sub functions directly:
* `!who` for company name (`get_company_name`)
* `!news` for "most relevant article" (`get_news`)

The !news endpoint uses the `pct_change` statistic to try and find a "positive" or "negative" article to explain the price movement of the day.

TODO: add image of return?

## !news [ticker] [+/- (OPTIONAL)]
`!news` endpoint hits the Google Finance endpoint to get the relevant articles for a given ticker.

The Google Finance endpoint .json does not return valid JSON, and can only be parsed with `demjson` library

Google Finance endpoint returns 10-15 articles in a query.  To grade these responses, `NLTK` is run over the headlines to asses them as positive or negative.  Then using the `pct_change` of a quote, select the "best" or "worst" outlook to match the direction of the stock.

If the call is neutral, both the best/worst articles will be returned with their sentiment scores.

`!news` uses the [vader_lexicon](http://www.nltk.org/api/nltk.sentiment.html#module-nltk.sentiment.vader) to grade headlines of articles.  The best article is picked off the `polarity_scores['compound']` values.  First found result wins in a tie.

Links are returned with their sentiment score

## !quote [ticker] [range=30] [please (OPTIONAL)]
`!quote` is meant to give a bigger picture of a stock.  Where `!price` tells the one-day view, `!quote` returns a graph of the stock performance so far

