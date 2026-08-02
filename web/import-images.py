#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""원본 사이트의 사진을 내려받아 자리표시자(.plate)를 실제 <img>로 바꾼다.

사용법
------
1. images.tsv 를 만든다. 한 줄에 하나씩, 탭으로 구분:

       slot<TAB>이미지 URL<TAB>대체 텍스트

   slot 은 각 페이지의 사진 자리를 가리키는 이름이다. 자리 이름은
       python3 import-images.py --list
   로 확인할 수 있다.

2. 내려받고 교체:

       python3 import-images.py images.tsv

   assets/img/ 에 저장하고, 해당 slot 의 <div class="plate …"> 를
   <img class="photo …"> 로 바꾼다. 비율 클래스(ratio-16x9 등)와
   캡션은 그대로 유지한다.

이미 <img> 로 바뀐 자리는 건드리지 않으므로 여러 번 실행해도 안전하다.
"""

import io
import os
import re
import sys
import urllib.request

PAGES = ['index.html', 'news.html', 'article.html', 'local.html', 'qna.html', 'about.html']
IMG_DIR = 'assets/img'

PLATE_RE = re.compile(
    r'<div class="(plate[^"]*?)\s+(ratio-[0-9x]+)"\s*>(.*?)</div>'
    r'|<div class="(plate[^"]*?)\s+(ratio-[0-9x]+)"\s*></div>',
    re.S)

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


def slots(page, html):
    """페이지 안의 사진 자리를 순서대로 (이름, 매치) 로 돌려준다."""
    base = os.path.splitext(page)[0]
    out = []
    for i, m in enumerate(PLATE_RE.finditer(html), 1):
        out.append(('%s-%02d' % (base, i), m))
    return out


def list_slots():
    for page in PAGES:
        html = io.open(page, encoding='utf-8').read()
        found = slots(page, html)
        print('\n# %s — %d곳' % (page, len(found)))
        for name, m in found:
            cls = m.group(1) or m.group(4)
            ratio = m.group(2) or m.group(5)
            caption = (m.group(3) or '').strip()
            cap = re.sub(r'<[^>]+>', '', caption).strip()
            print('  %-14s %-16s %-12s %s' % (name, cls, ratio, cap[:40]))


def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://imweb.me/'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    io.open(dest, 'wb').write(data)
    return len(data)


def apply_map(tsv_path):
    mapping = {}
    for line in io.open(tsv_path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            print('건너뜀 (열 부족):', line)
            continue
        slot, url = parts[0].strip(), parts[1].strip()
        alt = parts[2].strip() if len(parts) > 2 else ''
        mapping[slot] = (url, alt)

    os.makedirs(IMG_DIR, exist_ok=True)

    for page in PAGES:
        html = io.open(page, encoding='utf-8').read()
        found = slots(page, html)
        changed = 0

        # 뒤에서부터 바꿔야 앞쪽 인덱스가 밀리지 않는다
        for name, m in reversed(found):
            if name not in mapping:
                continue
            url, alt = mapping[name]
            ext = os.path.splitext(url.split('?')[0])[1].lower() or '.jpg'
            if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'):
                ext = '.jpg'
            fname = '%s%s' % (name, ext)
            dest = os.path.join(IMG_DIR, fname)

            try:
                size = download(url, dest)
            except Exception as exc:                      # noqa: BLE001
                print('실패 %-14s %s' % (name, exc))
                continue

            ratio = m.group(2) or m.group(5)
            caption = (m.group(3) or '').strip()
            alt_txt = alt or re.sub(r'<[^>]+>', '', caption).strip()

            img = '<img class="photo %s" src="%s/%s" alt="%s" loading="lazy">' % (
                ratio, IMG_DIR, fname, alt_txt.replace('"', '&quot;'))
            if caption:
                img = '<span class="media %s">%s%s</span>' % (ratio, img, caption)

            html = html[:m.start()] + img + html[m.end():]
            changed += 1
            print('  %-14s %6.1f KB  %s' % (name, size / 1024, fname))

        if changed:
            io.open(page, 'w', encoding='utf-8').write(html)
            print('%s — %d곳 교체' % (page, changed))


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) < 2 or sys.argv[1] in ('--list', '-l'):
        list_slots()
        return
    apply_map(sys.argv[1])
    print('\n끝났습니다. python3 build-preview.py 로 미리보기를 갱신하세요.')


if __name__ == '__main__':
    main()
