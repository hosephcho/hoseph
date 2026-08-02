/* =========================================================
   재택의료저널 — 공용 스크립트
   - 다크/라이트 테마 토글 (localStorage 저장)
   - 스크롤 시 마스트헤드 축소
   - 스크롤 진입 애니메이션
   - 기사 읽기 진행률
   - 뉴스 목록 카테고리 필터
   - 오늘 날짜 표기
   ========================================================= */

(function () {
  'use strict';

  /* ---------- 테마 ---------- */

  var STORAGE_KEY = 'hcj-theme';

  function applyTheme(theme) {
    if (theme === 'light' || theme === 'dark') {
      document.documentElement.setAttribute('data-theme', theme);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }

  function currentTheme() {
    var stored = null;
    try { stored = localStorage.getItem(STORAGE_KEY); } catch (e) { /* ignore */ }
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  try { applyTheme(localStorage.getItem(STORAGE_KEY)); } catch (e) { /* ignore */ }

  function initTheme() {
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    if (!buttons.length) return;

    function label(theme) {
      return theme === 'dark' ? 'LIGHT' : 'DARK';
    }

    function sync() {
      var t = currentTheme();
      buttons.forEach(function (btn) {
        btn.textContent = label(t);
        btn.setAttribute('aria-label', t === 'dark' ? '밝은 화면으로 전환' : '어두운 화면으로 전환');
      });
    }

    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var next = currentTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* ignore */ }
        sync();
      });
    });

    sync();
  }

  /* ---------- 마스트헤드 ---------- */

  function initMasthead() {
    var masthead = document.querySelector('.masthead');
    if (!masthead) return;

    var threshold = 90;
    var ticking = false;

    function update() {
      masthead.classList.toggle('is-stuck', window.scrollY > threshold);
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });

    update();
  }

  /* ---------- 스크롤 진입 애니메이션 ---------- */

  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var delay = Number(el.getAttribute('data-reveal-delay') || 0);
        setTimeout(function () { el.classList.add('is-visible'); }, delay);
        observer.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    items.forEach(function (el) { observer.observe(el); });
  }

  /* ---------- 읽기 진행률 ---------- */

  function initProgress() {
    var bar = document.querySelector('.progress');
    var body = document.querySelector('.article-body');
    if (!bar || !body) return;

    var ticking = false;

    function update() {
      var rect = body.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var scrolled = -rect.top;
      var pct = total > 0 ? Math.min(Math.max(scrolled / total, 0), 1) : 0;
      bar.style.width = (pct * 100).toFixed(2) + '%';
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });

    window.addEventListener('resize', update);
    update();
  }

  /* ---------- 카테고리 필터 ---------- */

  function initFilters() {
    var chips = document.querySelectorAll('[data-filter]');
    var items = document.querySelectorAll('[data-category]');
    if (!chips.length || !items.length) return;

    var count = document.querySelector('[data-filter-count]');
    var known = {};
    chips.forEach(function (chip) { known[chip.getAttribute('data-filter')] = chip; });

    function apply(value) {
      var shown = 0;
      items.forEach(function (item) {
        var match = value === 'all' || item.getAttribute('data-category') === value;
        item.hidden = !match;
        if (match) shown += 1;
      });
      if (count) count.textContent = String(shown);
    }

    function select(value) {
      var chip = known[value] || known.all;
      chips.forEach(function (c) { c.setAttribute('aria-pressed', 'false'); });
      chip.setAttribute('aria-pressed', 'true');
      apply(chip.getAttribute('data-filter'));
    }

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        select(chip.getAttribute('data-filter'));
      });
    });

    // ?cat=policy 처럼 주소로 들어온 카테고리를 초기 선택값으로 사용
    var initial = 'all';
    try {
      var cat = new URLSearchParams(window.location.search).get('cat');
      if (cat && known[cat]) initial = cat;
    } catch (e) { /* ignore */ }

    select(initial);
  }

  /* ---------- 오늘 날짜 ---------- */

  function initDate() {
    var nodes = document.querySelectorAll('[data-today]');
    if (!nodes.length) return;

    function pad(n) { return n < 10 ? '0' + n : String(n); }

    var now = new Date();
    var days = ['일', '월', '화', '수', '목', '금', '토'];
    var md = pad(now.getMonth() + 1) + '.' + pad(now.getDate());
    var suffix = ' ' + days[now.getDay()] + '요일';

    nodes.forEach(function (node) {
      // 2026.08.02 일요일 — 월·일만 강조
      node.textContent = '';
      node.appendChild(document.createTextNode(now.getFullYear() + '.'));
      var strong = document.createElement('strong');
      strong.textContent = md;
      node.appendChild(strong);
      node.appendChild(document.createTextNode(suffix));
    });
  }

  /* ---------- 구독 폼 (데모) ---------- */

  function initSubscribe() {
    var forms = document.querySelectorAll('[data-subscribe]');
    forms.forEach(function (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        var note = form.querySelector('[data-subscribe-note]');
        if (note) {
          note.textContent = '초안 데모입니다. 실제 구독 연동 시 이 자리에서 처리 결과를 안내합니다.';
          note.style.color = 'var(--brass)';
        }
        form.reset();
      });
    });
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    initTheme();
    initMasthead();
    initReveal();
    initProgress();
    initFilters();
    initDate();
    initSubscribe();
  });
})();
