import requests
import warnings
import os
import re
from datetime import datetime, timezone, timedelta

warnings.filterwarnings('ignore')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0'}
TW_TZ = timezone(timedelta(hours=8))
LIVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data_live.js')


# ── TAIEX ────────────────────────────────────────────────────────────────────

def fetch_taiex_today():
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
        print(f'TAIEX fetch error: {e}')
    return None, None, None


# ── VT ───────────────────────────────────────────────────────────────────────

def fetch_vt():
    """用 yfinance 抓 VT 最新收盤與近期最高，並從歷史找 ATH."""
    try:
        import yfinance as yf
        ticker = yf.Ticker('VT')

        # 最近 5 天（含今日），取最後一筆有效資料
        hist = ticker.history(period='5d')
        if hist.empty:
            return None, None, None, None, None

        last = hist.iloc[-1]
        date  = hist.index[-1].strftime('%Y-%m-%d')
        close = round(float(last['Close']), 2)
        high  = round(float(last['High']),  2)

        # 歷史最高點
        full = ticker.history(period='max')
        ath_date = full['High'].idxmax().strftime('%Y-%m-%d')
        ath_val  = round(float(full['High'].max()), 2)

        return date, close, high, ath_val, ath_date
    except Exception as e:
        print(f'VT fetch error: {e}')
    return None, None, None, None, None


# ── 讀 / 寫 data_live.js ─────────────────────────────────────────────────────

def read_stored():
    with open(LIVE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    def section(name):
        m = re.search(rf'{name}:\s*\{{([^}}]+)\}}', content, re.DOTALL)
        return m.group(1) if m else ''

    def val_f(text, key):
        m = re.search(rf'{key}:\s*([-\d.]+)', text)
        return float(m.group(1)) if m else 0.0

    def val_i(text, key):
        m = re.search(rf'{key}:\s*(\d+)', text)
        return int(m.group(1)) if m else 0

    def val_s(text, key):
        m = re.search(rf"{key}:\s*'([^']*)'", text)
        return m.group(1) if m else ''

    tx = section('taiex')
    vx = section('vt')

    return {
        'taiex': {
            'current': val_f(tx, 'current'), 'currentDate': val_s(tx, 'currentDate'),
            'ath': val_f(tx, 'ath'), 'athDate': val_s(tx, 'athDate'),
            'athYtdCount': val_i(tx, 'athYtdCount'), 'athYtdYear': val_i(tx, 'athYtdYear'),
        },
        'vt': {
            'current': val_f(vx, 'current'), 'currentDate': val_s(vx, 'currentDate'),
            'ath': val_f(vx, 'ath'), 'athDate': val_s(vx, 'athDate'),
            'athYtdCount': val_i(vx, 'athYtdCount'), 'athYtdYear': val_i(vx, 'athYtdYear'),
        },
    }


def write_live(taiex, vt):
    updated_at = datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')
    content = f"""const DATA_LIVE = {{
  taiex: {{
    current: {taiex['current']},
    currentDate: '{taiex['currentDate']}',
    ath: {taiex['ath']},
    athDate: '{taiex['athDate']}',
    dropFromAth: {taiex['dropFromAth']},
    athYtdCount: {taiex['athYtdCount']},
    athYtdYear: {taiex['athYtdYear']},
  }},
  vt: {{
    current: {vt['current']},
    currentDate: '{vt['currentDate']}',
    ath: {vt['ath']},
    athDate: '{vt['athDate']}',
    dropFromAth: {vt['dropFromAth']},
    athYtdCount: {vt['athYtdCount']},
    athYtdYear: {vt['athYtdYear']},
  }},
  updatedAt: '{updated_at}',
}};
"""
    with open(LIVE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    stored = read_stored()

    this_year = datetime.now(TW_TZ).year

    def update_ytd_count(stored_data, new_ath_date, old_ath_date):
        count = stored_data['athYtdCount']
        year  = stored_data['athYtdYear']
        if year != this_year:
            count, year = 0, this_year
        if new_ath_date != old_ath_date:
            count += 1
        return count, year

    # ── TAIEX ──
    t_date, t_close, t_high = fetch_taiex_today()
    if t_close is None:
        print('無 TAIEX 今日資料，保留上次數值')
        t_close    = stored['taiex']['current']
        t_date     = stored['taiex']['currentDate']
        t_ath      = stored['taiex']['ath']
        t_ath_date = stored['taiex']['athDate']
        t_ytd_count, t_ytd_year = stored['taiex']['athYtdCount'], stored['taiex']['athYtdYear']
    else:
        print(f'TAIEX 今日 {t_date}  收盤 {t_close}  最高 {t_high}')
        t_ath      = stored['taiex']['ath']
        t_ath_date = stored['taiex']['athDate']
        if t_high > t_ath:
            t_ath, t_ath_date = t_high, t_date
            print(f'TAIEX 新 ATH！{t_ath} @ {t_ath_date}')
        t_ytd_count, t_ytd_year = update_ytd_count(stored['taiex'], t_ath_date, stored['taiex']['athDate'])

    # ── VT ──
    v_date, v_close, v_high, v_hist_ath, v_hist_ath_date = fetch_vt()
    if v_close is None:
        print('無 VT 資料，保留上次數值')
        v_close    = stored['vt']['current']
        v_date     = stored['vt']['currentDate']
        v_ath      = stored['vt']['ath']
        v_ath_date = stored['vt']['athDate']
        v_ytd_count, v_ytd_year = stored['vt']['athYtdCount'], stored['vt']['athYtdYear']
    else:
        print(f'VT 最新 {v_date}  收盤 {v_close}  最高 {v_high}  歷史ATH {v_hist_ath} @ {v_hist_ath_date}')
        v_ath      = v_hist_ath
        v_ath_date = v_hist_ath_date
        if v_high > v_ath:
            v_ath, v_ath_date = v_high, v_date
            print(f'VT 新 ATH！{v_ath} @ {v_ath_date}')
        v_ytd_count, v_ytd_year = update_ytd_count(stored['vt'], v_ath_date, stored['vt']['athDate'])

    t_drop = round((t_close - t_ath) / t_ath * 100, 2) if t_ath and t_close else 0
    v_drop = round((v_close - v_ath) / v_ath * 100, 2) if v_ath and v_close else 0

    write_live(
        taiex={'current': t_close, 'currentDate': t_date, 'ath': t_ath, 'athDate': t_ath_date, 'dropFromAth': t_drop, 'athYtdCount': t_ytd_count, 'athYtdYear': t_ytd_year},
        vt=   {'current': v_close, 'currentDate': v_date, 'ath': v_ath, 'athDate': v_ath_date, 'dropFromAth': v_drop, 'athYtdCount': v_ytd_count, 'athYtdYear': v_ytd_year},
    )
    print('data_live.js 已更新')


if __name__ == '__main__':
    main()
