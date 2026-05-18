'''
TO DO

- Scrape the messages of the predefined timelines in three datasets
'''


import csv
import os
from datetime import datetime, timezone
import time

import requests
from bs4 import BeautifulSoup


# Configuration
CHANNEL_NAME = 'sut_tw'

# Output directory
OUTPUT_DIR = 'data'

# Timelines
TIMELINES = {
    'timeline_1_2025_Jun24_Dec28': {
        'start': datetime(2025, 6, 24, tzinfo = timezone.utc),
        'end': datetime(2025, 12, 28, 23, 59, 59, tzinfo = timezone.utc)
    },
    'timeline_2_2025_Dec29_2026_Feb28': {
        'start': datetime(2025, 12, 29, tzinfo = timezone.utc),
        'end': datetime(2026, 2, 28, 23, 59, 59, tzinfo = timezone.utc)
    },
    'timeline_3_2026_Mar01_May16': {
        'start': datetime(2026, 3, 1, tzinfo = timezone.utc),
        'end': datetime(2026, 5, 16, 23, 59, 59, tzinfo = timezone.utc)
    }    
}


PROXY = None

def parse_message_date(tag):
    '''Extract UTC datetime from a <time> element'''
    if tag and tag.has_attr('datetime'):
        return datetime.fromisoformat(tag['datetime']).replace(tzinfo = timezone.utc)
    return None

def scrape_channel(channel_name, start_dt, end_dt):
    '''
    Scrape the public Telegram channel preview (t.me/s/...).
    Returns list of dicts: {message_id, date, text}.
    '''
    messages = []
    base_url = f'https://t.me/s/{channel_name}'
    params = {}
    session = requests.Session()
    session.proxies = PROXY

    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)'}

    page_count = 0

    while True:
        time.sleep(1)
        try:
            resp = session.get(base_url, params = params, headers = headers, timeout = 30)
        except requests.RequestException as e:
            print(f'Network Error: {e}')
            break

        if resp.status_code != 200:
            print(f'Error {resp.status_code} fetching {resp.url}')
            break

        page_count += 1
        print(f'Page {page_count}: {resp.url}')

        soup = BeautifulSoup(resp.text, 'html.parser')
        msg_widgets = soup.find_all('div', class_ = 'tgme_widget_message_wrap')

        if not msg_widgets:
            print('No messages found on this page')
            break

        page_oldest_date = None
        for widget in msg_widgets:
            msg_div = widget.find('div', class_ = 'tgme_widget_message')
            if not msg_div:
                continue
            data_post = msg_div.get('data-post')
            if not data_post or '/' not in data_post:
                continue
            msg_id = int(data_post.split('/')[-1])

            # Message date
            time_tag = widget.find('time')
            msg_date = parse_message_date(time_tag)
            if not msg_date:
                print(f'Could not parse from <time>: {time_tag.get('datetime', 'no datetime attr')}')
                continue

            # Stop if older than start_dt
            if msg_date < start_dt:
                page_oldest_date = msg_date
                break

            if start_dt <= msg_date <= end_dt:
                text_div = widget.find('div', class_ = 'tgme_widget_message_text')
                text = text_div.get_text(separator = '\n').strip() if text_div else ''
                messages.append({
                    'message_id': msg_id,
                    'date': msg_date.isoformat(),
                    'text': text
                })

            page_oldest_date = msg_date

        if page_oldest_date and page_oldest_date < start_dt:
            break

        prev_link = soup.find('link', rel = 'prev')
        if not prev_link:
            print('End of history')
            break

        next_before = prev_link['href'].split('before=')[-1]
        params = {'before': next_before}

    return messages


def main():
    for name, dates in TIMELINES.items():
        print(f'Scraping {name}')
        messages = scrape_channel(CHANNEL_NAME, dates['start'], dates['end'])

        filepath = os.path.join(OUTPUT_DIR, f'{name}.csv')
        
        with open(filepath, 'w', newline = '', encoding = 'utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames = ['message_id', 'date', 'text'])
            writer.writeheader()
            writer.writerows(messages)

        print(f'Saved {len(messages)} messages to {filepath}')

if __name__ == '__main__':
    main()