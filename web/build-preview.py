#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""6개 정적 페이지를 단일 파일 미리보기(preview.html)로 묶는다.

배포본은 web/*.html 각각을 그대로 쓰고, preview.html은 링크 하나로
전체를 둘러볼 수 있게 만든 부산물이다. 페이지나 CSS/JS를 고친 뒤
    python3 build-preview.py
를 다시 실행하면 preview.html이 갱신된다.
"""

import base64
import io
import json
import mimetypes
import os
import re

PAGES = ['index', 'news', 'article', 'local', 'qna', 'about']

IMG_SRC_RE = re.compile(r'src="(assets/img/[^"]+)"')

TITLES = {
    'index':   '재택의료NEWS — 집으로 가는, 집에서 하는',
    'news':    '전체 기사 — 재택의료NEWS',
    'article': '65세 이상 고령층…전체 인구의 20.7% — 재택의료NEWS',
    'local':   '우리동네재택의료 — 재택의료NEWS',
    'qna':     '재택의료 Q&A — 재택의료NEWS',
    'about':   '회사소개 — 재택의료NEWS',
}

ROUTER = r"""
/* ---------- 단일 파일 미리보기 라우터 ----------
   6개 페이지를 한 파일에 담아 해시(#/news?cat=hot)로 전환한다.
   실제 배포에서는 각 .html 파일을 그대로 쓰므로 이 코드는 쓰이지 않는다. */
(function () {
  'use strict';

  var VIEWS  = __VIEWS__;
  var TITLES = __TITLES__;
  var app = document.getElementById('app');

  function parse(hash) {
    var raw = (hash || '').replace(/^#\/?/, '');
    if (!raw) return { view: 'index', cat: '', anchor: '' };

    var anchor = '';
    var hi = raw.indexOf('#');
    if (hi > -1) { anchor = raw.slice(hi + 1); raw = raw.slice(0, hi); }

    var cat = '';
    var qi = raw.indexOf('?');
    if (qi > -1) {
      var m = /(?:^|&)cat=([^&]*)/.exec(raw.slice(qi + 1));
      raw = raw.slice(0, qi);
      if (m) cat = decodeURIComponent(m[1]);
    }

    if (!VIEWS[raw]) raw = 'index';
    return { view: raw, cat: cat, anchor: anchor };
  }

  function markCurrent(view, cat) {
    var want = view === 'index' ? 'news.html'
             : view === 'news'  ? (cat ? 'news.html?cat=' + cat : 'news.html')
             : view + '.html';
    Array.prototype.forEach.call(app.querySelectorAll('.mainnav__link'), function (a) {
      if (a.getAttribute('data-href') === want) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
  }

  // 내부 .html 링크를 해시 경로로 바꾼다
  function rewrite(root) {
    Array.prototype.forEach.call(root.querySelectorAll('a[href]'), function (a) {
      var href = a.getAttribute('href');
      if (!href || !/\.html(\?|#|$)/.test(href)) return;
      a.setAttribute('data-href', href);
      a.setAttribute('href', '#/' + href.replace(/\.html/, ''));
    });
  }

  function render(state) {
    window.__hcjCat = state.cat;
    app.innerHTML = VIEWS[state.view];
    rewrite(app);
    markCurrent(state.view, state.cat);
    document.title = TITLES[state.view] || TITLES.index;
    if (window.HCJ && window.HCJ.init) window.HCJ.init();

    if (state.anchor) {
      var target = document.getElementById(state.anchor);
      if (target) { target.scrollIntoView(); return; }
    }
    window.scrollTo(0, 0);
  }

  window.addEventListener('hashchange', function () { render(parse(window.location.hash)); });
  render(parse(window.location.hash));
})();
"""


def inline_images(html):
    """assets/img 상대경로를 base64 data URI로 바꿔, preview.html 하나만
    떼어 내도 사진이 그대로 보이게 한다."""
    cache = {}

    def sub(m):
        path = m.group(1)
        if path not in cache:
            data = io.open(path, 'rb').read()
            mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            cache[path] = 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode('ascii'))
        return 'src="%s"' % cache[path]

    return IMG_SRC_RE.sub(sub, html)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    css = io.open('assets/css/main.css', encoding='utf-8').read()
    js = io.open('assets/js/main.js', encoding='utf-8').read()

    views = {}
    for name in PAGES:
        src = io.open('%s.html' % name, encoding='utf-8').read()
        start = src.index('<body>') + len('<body>')
        end = src.index('<script src="assets/js/main.js">')
        views[name] = inline_images(src[start:end].strip())

    router = (ROUTER
              .replace('__VIEWS__', json.dumps(views, ensure_ascii=False))
              .replace('__TITLES__', json.dumps(TITLES, ensure_ascii=False)))

    out = (
        '<title>%s</title>\n'
        '<style>\n%s\n</style>\n\n'
        '<div id="app"></div>\n\n'
        '<script>\n%s\n%s\n</script>\n'
    ) % (TITLES['index'], css, js, router)

    io.open('preview.html', 'w', encoding='utf-8').write(out)
    print('preview.html — %d bytes, %d views' % (len(out), len(views)))


if __name__ == '__main__':
    main()
