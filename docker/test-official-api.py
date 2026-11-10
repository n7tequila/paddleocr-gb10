#!/usr/bin/env python3
"""Checks the official PaddleX /layout-parsing response. Stdlib only."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8080/layout-parsing')
    p.add_argument('--image', required=True)
    p.add_argument('--output', default='api-smoke-result.json')
    args = p.parse_args()
    if not args.url.endswith('/layout-parsing'):
        sys.exit('Expected official /layout-parsing endpoint')
    data = {
        'file': base64.b64encode(Path(args.image).read_bytes()).decode('ascii'),
        'fileType': 1,
        'visualize': False,
        'useDocOrientationClassify': False,
        'useDocUnwarping': False,
    }
    req = Request(args.url, json.dumps(data).encode(),
                  headers={'Content-Type': 'application/json'}, method='POST')
    start = time.monotonic()
    try:
        with urlopen(req, timeout=300) as response:
            raw = response.read()
            status = response.status
    except HTTPError as e:
        sys.exit(f'HTTP error {e.code}: {e.read(2048).decode(errors="replace")}')
    except URLError as e:
        sys.exit(f'HTTP request failed: {e}')
    Path(args.output).write_bytes(raw)
    result = json.loads(raw)
    pages = result.get('result', {}).get('layoutParsingResults', [])
    assert status == 200, f'HTTP {status}'
    assert result.get('errorCode') == 0, f"errorCode={result.get('errorCode')} {result.get('errorMsg')}"
    assert isinstance(pages,list) and len(pages)>=1, f'Unexpected result: {list(result)}'
    assert 'markdown' in pages[0] and 'prunedResult' in pages[0]
    print(f'SUCCESS: official API, {len(pages)} page(s), {time.monotonic()-start:.2f}s')
    print('Response:',args.output)
    print('Response keys:', list(result))
    print('First page keys:', list(pages[0]))
    md = pages[0]['markdown']
    if isinstance(md,dict): print('Markdown preview:',repr(str(md.get('text',''))[:180]))
if __name__ == '__main__':
    main()
