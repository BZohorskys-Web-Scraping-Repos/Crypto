import webbrowser
import aiohttp
import asyncio
import curses
import logging
import itertools

from lxml import html

COIN_MARKET_CAP_URL = 'https://coinmarketcap.com/currencies/'
COIN_WARS_URL = 'https://www.coinwarz.com/mining/<coin>/difficulty-chart'

logging.basicConfig(
    level=logging.WARN,
    format='%(asctime)-15s [%(levelname)s] %(funcName)s: %(message)s',
)

# Sample logging call
# logging.WARN(locals())

async def get_cmc_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = {
                'url': url,
                'error': False
            }
            code = response.status
            if code != 200:
                data['error'] = True
                return data
            webpage = html.fromstring(await response.text())
            data['current_value'] = [
                webpage.xpath('//div[contains(@class,"priceTitle")]/div/span/text()')[0],
                webpage.xpath('//div[contains(@class,"priceTitle")]/span/span/@class')[0],
                webpage.xpath('//div[contains(@class,"priceTitle")]/span/text()')[0],
            ]
            volume_html = webpage.xpath('//div[@class="statsBlock"]/div/div[@class="statsItemRight"]')[2]
            data['current_volume'] = [
                volume_html.xpath('./div/text()')[0],
                volume_html.xpath('./span/span/@class')[0],
                volume_html.xpath('./span/text()')[:2]
            ]
            data['current_rank'] = webpage.xpath('//div[@class="namePill namePillPrimary"]/text()')[0]
            data['alternate_price_1'] = [
                webpage.xpath('//div[contains(@class,"alternatePrices")]/p/text()')[0].split()[1],
                webpage.xpath('//div[contains(@class,"alternatePrices")]/p/span/span/@class')[0],
                webpage.xpath('//div[contains(@class,"alternatePrices")]/p/span/descendant-or-self::*/text()')[:2]
                ]
            price_history_html = webpage.xpath('//caption[contains(text(),"Price History")]/following-sibling::tbody/tr')
            data['price_history'] = [
                webpage.xpath('//div[contains(@class,"sliderSection")]/descendant-or-self::*/text()'),
                price_history_html[0].xpath('./descendant-or-self::*/text()'),
                price_history_html[1].xpath('./descendant-or-self::*/text()'),
                price_history_html[2].xpath('./descendant-or-self::*/text()'),
                price_history_html[3].xpath('./descendant-or-self::*/text()'),
            ]
            return data

async def get_cw_data(url):
    async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = {
                    'url': url,
                    'error': False
                }
                code = response.status
                if code != 200:
                    data['error'] = True
                    return data
                webpage = html.fromstring(await response.text())
                data['current_difficulty'] = webpage.xpath('//strong[contains(text(),"Current")]/following-sibling::div/span/strong/text()'),
                difficulty_values = webpage.xpath('//div[@class="diff-summary-section"]/div/span/text()')
                data['difficulties'] = [value.strip() for value in difficulty_values]
                return data

def format_data(data):
    formated_data = {}
    for key in data:
        if key == 'current_value':
            value = data[key][0]
            direction = get_direction(data[key][1])
            percent_change = data[key][2]
            value_change = float(percent_change.replace(',', ''))/100 * float(value[1:].replace(',',''))
            formated_data[key] = ''.join(['Current Value: ', value, ' ', direction, '(', percent_change, '%|$', "{:,}".format(value_change), ')'])
        elif key == 'current_volume':
            volume = data[key][0]
            direction = get_direction(data[key][1])
            percent_change = data[key][2][0]
            volume_change = float(percent_change.replace(',', ''))/100 * float(volume[1:].replace(',',''))
            formated_data[key] = ''.join(['Current Volume: ', volume, ' ', direction, '(', percent_change, '%|$', "{:,}".format(volume_change), ')'])
        elif key == 'current_rank':
            formated_data[key] = 'Current Rank: ' + data[key].split()[1]
        elif key == 'alternate_price_1':
            coin = data[key][0]
            direction = get_direction(data[key][1])
            percent_change = ''.join(data[key][2])
            formated_data[key] = ''.join(['Coin Comparision: ', coin, ' ', direction, percent_change])
        elif key == 'price_history':
            h24 = data[key][0]
            formated_data['24h'] = ''.join(['24h Low / 24h High : ', h24[2], " / ", h24[5]])
            d7 = data[key][1]
            formated_data['7d'] = ''.join([d7[0], ': ', d7[1], ' / ', d7[3]])
            d30 = data[key][2]
            formated_data['30d'] = ''.join([d30[0], ': ', d30[1], ' / ', d30[3]])
            d90 = data[key][3]
            formated_data['90d'] = ''.join([d90[0], ': ', d90[1], ' / ', d90[3]])
            w52 = data[key][4]
            formated_data['w52'] = ''.join([w52[0], ': ', w52[1], ' / ', w52[3]])
        elif key == 'current_difficulty':
            formated_data[key] = 'Current Difficulty: ' + data[key][0][0]
        elif key == 'difficulties':
            if 'current_difficulty' in formated_data:
                current_difficulty = float(data['current_difficulty'][0][0].replace(',',''))
                formated_data['1dd'] = ''.join(['1 Day Difficulty: ', data[key][0], ' | ', "{:,}".format(float(data[key][0][:-1].replace(',',''))/100 * current_difficulty)])
                formated_data['7dd'] = ''.join(['7 Days Difficulty: ', data[key][1], ' | ', "{:,}".format(float(data[key][1][:-1].replace(',',''))/100 * current_difficulty)])
                formated_data['30dd'] = ''.join(['30 Days Difficulty: ', data[key][2], ' | ', "{:,}".format(float(data[key][2][:-1].replace(',',''))/100 * current_difficulty)])
                formated_data['90dd'] = ''.join(['90 Days Difficulty: ', data[key][3], ' | ', "{:,}".format(float(data[key][3][:-1].replace(',',''))/100 * current_difficulty)])
    return formated_data

def get_direction(icon_class):
    if icon_class == 'icon-Caret-up':
        return "+"
    else:
        return "-"

async def idleAnimation(task):
    for frame in itertools.cycle(r'-\|/-\|/'):
        if task.done():
            print('\r', '', sep='', end='', flush=True)
            break
        print('\r', frame, sep='', end='', flush=True)
        await asyncio.sleep(0.2)

def interactive_console(screen, data, url):
    screen.clear()
    for key in data:
        screen.addstr(data[key] + '\n')
    screen.addstr("Quit or Open CoinMarketCap.com? (q,o)")
    user_response = screen.getkey()
    valid_response = False
    while not valid_response:
        if user_response == 'q':
            valid_response = True
        elif user_response == 'o':
            webbrowser.open(url)
            user_response = screen.getkey()
        else:
            user_response = screen.getkey()


async def search(query_string):
    cmc_url = COIN_MARKET_CAP_URL + query_string
    cw_url = COIN_WARS_URL.replace('<coin>', query_string)
    cmc_task = asyncio.create_task(get_cmc_data(cmc_url))
    cw_task = asyncio.create_task(get_cw_data(cw_url))
    await idleAnimation(asyncio.gather(cmc_task, cw_task))
    tasks = [cmc_task, cw_task]
    data = {}
    show_user_data = True
    for task in tasks:
        if task.result()['error']:
            print(f"There was an issue scraping {task.result()['url']}")
            show_user_data = False
        else:
            for key in task.result():
                if key == 'error' or key == 'url':
                    continue
                data[key] = task.result()[key]
    if show_user_data:
        curses.wrapper(interactive_console, (format_data(data)), cmc_url)