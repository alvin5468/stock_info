import requests
import warnings
import os
import re
from datetime import datetime, timezone, timedelta

warnings.filterwarnings('ignore')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0'}
TW_TZ = timezone(timedelta(hours=8))
LIVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data_live.js')


def fetch_today():
    now = datetime.now(TW_TZ)
    date_str = now.strftime('%Y%m%d')
    url = f'https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={date_str}&response=json'
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        d = r.json()
        if d.get('stat') == 'OK' and d.get('data'):
            last = d['data'][-1]
            parts = last[0].split('/')
            year = int(parts[0]) + 1911
            date = f'{year}-{parts[1]}-{parts[2]}'
            close = float(last[4].replace(',', ''))
            high  = float(last[2].replace(',', ''))
            return date, close, high
    except Exception as e:
        print(f'fetch error: {e}')
    return None, None, None


def read_stored():
    with open(LIVE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    ath      = float(re.search(r'ath:\s*([\d.]+)',         content).group(1))
    ath_date =        re.search(r"athDate:\s*'([^']+)'",   content).group(1)
    return ath, ath_date


def write_live(current, current_date, ath, ath_date):
    drop       = round((current - ath) / ath * 100, 2)
    updated_at = datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')
    content = f"""const DATA_LIVE = {{
  current: {current},
  currentDate: '{current_date}',
  ath: {ath},
  athDate: '{ath_date}',
  dropFromAth: {drop},
  updatedAt: '{updated_at}',
}};
"""
    with open(LIVE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    date, close, high = fetch_today()
    if close is None:
        print('無今日資料，略過')
        return

    print(f'今日 {date}  收盤 {close}  最高 {high}')

    stored_ath, stored_ath_date = read_stored()
    print(f'儲存 ATH {stored_ath} @ {stored_ath_date}')

    new_ath      = stored_ath
    new_ath_date = stored_ath_date

    if high > stored_ath:
        new_ath      = high
        new_ath_date = date
        print(f'新 ATH！{new_ath} @ {new_ath_date}')

    write_live(close, date, new_ath, new_ath_date)
    print('data_live.js 已更新')


if __name__ == '__main__':
    main()
