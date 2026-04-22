#!/usr/bin/env python3
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from urllib.request import Request, urlopen

class TableExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_th = False
        self.in_td = False
        self.current_row = []
        self.headers = []
        self.rows = []
        self.current_cell = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.headers = []
            self.rows = []
        elif self.in_table and tag == 'th':
            self.in_th = True
            self.current_cell = ''
        elif self.in_table and tag == 'td':
            self.in_td = True
            self.current_cell = ''

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif self.in_table and tag == 'th':
            self.in_th = False
            self.headers.append(self.current_cell.strip())
        elif self.in_table and tag == 'td':
            self.in_td = False
            self.current_row.append(self.current_cell.strip())
        elif self.in_table and tag == 'tr':
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data):
        if self.in_th or self.in_td:
            self.current_cell += data


def normalize_header(text):
    return re.sub(r"[^A-Za-z0-9]", '', text.strip().lower())


def parse_table(headers, rows):
    normalized = [normalize_header(h) for h in headers]
    keys = {}
    for idx, h in enumerate(normalized):
        if 'year' in h or h == 'y':
            keys['y'] = idx
        elif 'open' in h or h == 'o':
            keys['o'] = idx
        elif 'close' in h or h == 'c':
            keys['c'] = idx
        elif 'high' in h or h == 'h':
            keys['h'] = idx
        elif 'low' in h or h == 'l':
            keys['l'] = idx
    if set(keys.keys()) != {'y', 'o', 'c', 'h', 'l'}:
        raise ValueError('Table headers do not contain all required columns: year, open, close, high, low')

    data = []
    for row in rows:
        if len(row) < len(headers):
            continue
        try:
            data.append({
                'y': int(row[keys['y']]),
                'o': float(row[keys['o']].replace(',', '').replace('$', '')),
                'c': float(row[keys['c']].replace(',', '').replace('$', '')),
                'h': float(row[keys['h']].replace(',', '').replace('$', '')),
                'l': float(row[keys['l']].replace(',', '').replace('$', '')),
            })
        except ValueError:
            continue
    return data


def fetch_url(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req) as resp:
        charset = resp.headers.get_content_charset() or 'utf-8'
        return resp.read().decode(charset, errors='ignore')


def write_js(data, output_file='data_vt.js'):
    payload = {
        'label': 'Vanguard 全球 VT ETF',
        'unit': 'USD',
        'isCurrency': True,
        'data': data,
    }
    lines = [
        'const DATA_VT = {',
        "  label: 'Vanguard 全球 VT ETF',",
        "  unit: 'USD',",
        '  isCurrency: true,',
        '  data: [',
    ]
    for item in payload['data']:
        lines.append(
            f"    {{ y: {item['y']}, o: {item['o']:.2f}, c: {item['c']:.2f}, h: {item['h']:.2f}, l: {item['l']:.2f} }},"
        )
    lines.extend(['  ]', '};', ''])

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Fetch VT data from a webpage and save to data_vt.js')
    parser.add_argument('url', help='URL of the web page containing VT data')
    parser.add_argument('--output', default='data_vt.js', help='Output JS file name')
    args = parser.parse_args()

    html = fetch_url(args.url)

    try:
        extracted = json.loads(html)
        if isinstance(extracted, dict) and 'data' in extracted:
            data = extracted['data']
        elif isinstance(extracted, list):
            data = extracted
        else:
            raise ValueError('JSON does not contain expected data structure')
    except Exception:
        parser_html = TableExtractor()
        parser_html.feed(html)
        if not parser_html.headers or not parser_html.rows:
            raise RuntimeError('Unable to extract table data from page')
        data = parse_table(parser_html.headers, parser_html.rows)

    if not data:
        raise RuntimeError('No valid data rows parsed')

    write_js(data, args.output)
    print(f'Written {len(data)} records to {args.output}')


if __name__ == '__main__':
    main()
