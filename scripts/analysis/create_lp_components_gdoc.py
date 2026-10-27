#!/usr/bin/env python3
# scripts/analysis/create_lp_components_gdoc.py
# ST LP Instagramコンポーネント（修正版）をGoogle Docに出力するスクリプト
# 必要: pip install google-auth google-auth-oauthlib

import sys, io, os, json, urllib.request, urllib.error, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]
TOKEN_FILE = '/Users/119322/Desktop/claude-code-template_af/secrets/token.json'
CREDS_FILE = '/Users/119322/Desktop/claude-code-template_af/secrets/credentials.json'

creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

token = creds.token

def api(url, body=None, method=None, retry=3):
    data = json.dumps(body).encode('utf-8') if body else None
    m = method or ('POST' if data else 'GET')
    for attempt in range(retry):
        req = urllib.request.Request(url, data=data,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            method=m)
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            err = e.read().decode('utf-8', errors='replace')
            if e.code == 429 and attempt < retry - 1:
                print(f'429 Too Many Requests - {attempt+1}秒待機...')
                time.sleep(attempt + 1)
                continue
            print(f'HTTP {e.code}: {err[:400]}')
            raise

# ============================================================
# HTML コンテンツ定義（修正済み）
# ============================================================

# 修正点サマリー:
# [root3] 特徴アイコン ? → 📋 / 🔍 / ⭐
# [root2] ボタンアイコン ? → 🎯、10秒で → 3分で
# [root2] 塾診断 → 塾ブランド診断

JUKU_PATTERN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220' "
    "viewBox='0 0 220 220'%3E%3Cg fill='none' stroke='%23FF7019' stroke-width='2.4' "
    "stroke-linecap='round' stroke-linejoin='round' opacity='0.16'%3E"
    "%3Cg transform='translate(14,20) rotate(-20)'%3E%3Crect x='0' y='0' width='46' height='11' rx='2.5'/%3E"
    "%3Cpolygon points='46,0 60,5.5 46,11'/%3E%3Cline x1='38' y1='0' x2='38' y2='11'/%3E%3C/g%3E"
    "%3Cg transform='translate(128,26)'%3E%3Cpath d='M0,2 Q16,-7 32,2 L32,26 Q16,17 0,26 Z'/%3E"
    "%3Cpath d='M32,2 Q48,-7 64,2 L64,26 Q48,17 32,26 Z'/%3E%3C/g%3E"
    "%3Cg transform='translate(26,108)'%3E%3Cpolygon points='22,0 44,10 22,20 0,10'/%3E"
    "%3Cline x1='22' y1='20' x2='22' y2='34'/%3E%3Cline x1='38' y1='13' x2='38' y2='28'/%3E"
    "%3Ccircle cx='38' cy='30' r='2.4' fill='%23FF7019' stroke='none'/%3E%3C/g%3E"
    "%3Cg transform='translate(140,118)'%3E%3Ccircle cx='16' cy='20' r='15'/%3E"
    "%3Cpath d='M16,5 Q20,-6 28,-1'/%3E%3Cpath d='M16,5 Q12,-3 6,-1'/%3E%3C/g%3E"
    "%3Cg transform='translate(66,168) rotate(10)'%3E%3Crect x='0' y='0' width='50' height='10' rx='2.5'/%3E"
    "%3Cline x1='10' y1='0' x2='10' y2='10'/%3E%3Cline x1='20' y1='0' x2='20' y2='10'/%3E"
    "%3Cline x1='30' y1='0' x2='30' y2='10'/%3E%3Cline x1='40' y1='0' x2='40' y2='10'/%3E%3C/g%3E"
    "%3Cg transform='translate(178,176)'%3E%3Ccircle cx='10' cy='10' r='9'/%3E"
    "%3Cpath d='M10,10 L10,2'/%3E%3Cpath d='M10,10 L15,12'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")"
)

# ---------- 1. FVセクション (jkw-root4) ----------
HTML_ROOT4 = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap" rel="stylesheet">
<style>
.jkw-root4 {
  --juku-pattern: """ + JUKU_PATTERN + """;
  width: 100%;
  max-width: 100vw;
  box-sizing: border-box;
  font-family: 'Noto Sans JP', sans-serif;
  background: #FFF3EA;
  padding: 40px 20px 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
  background-image: var(--juku-pattern);
  background-size: 200px 200px;
  overflow-x: hidden;
}
.jkw-root4, .jkw-root4 * { box-sizing: border-box; }
.hero-badge {
  background: #E8721A;
  color: white;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 18px;
  border-radius: 20px;
  letter-spacing: 0.05em;
  box-shadow: 0 3px 10px rgba(232,114,26,0.25);
}
.hero-bubble {
  background: white;
  border: 2.5px solid #E8721A;
  border-radius: 20px;
  padding: 26px 28px;
  text-align: center;
  position: relative;
  width: 100%;
  max-width: 560px;
  box-shadow: 0 8px 24px rgba(232,114,26,0.1);
}
.hero-bubble::before {
  content: '';
  position: absolute;
  top: -16px;
  left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-bottom-color: #E8721A;
}
.hero-bubble::after {
  content: '';
  position: absolute;
  top: -11px;
  left: 50%;
  transform: translateX(-50%);
  border: 7px solid transparent;
  border-bottom-color: white;
  z-index: 1;
}
.hero-lead { font-size: 15px; color: #E8721A; font-weight: 900; letter-spacing: 0.02em; }
.hero-text { font-size: 14px; color: #555; margin-top: 10px; line-height: 1.7; }
.hero-checks {
  display: flex;
  justify-content: center;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #F0C9A8;
}
.hero-check { font-size: 12px; color: #A07060; font-weight: 700; display: flex; align-items: center; gap: 4px; }
.hero-check span { color: #3BB04A; font-size: 14px; }
.btn-wrap { width: 100%; display: flex; justify-content: center; }
.hero-btn {
  background: #3BB04A;
  color: white;
  border: none;
  border-radius: 40px;
  padding: 18px 52px;
  font-size: clamp(15px,3vw,19px);
  font-weight: 900;
  cursor: pointer;
  letter-spacing: 0.04em;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  transition: opacity 0.2s;
  font-family: 'Noto Sans JP', sans-serif;
  box-shadow: 0 8px 20px rgba(59,176,74,0.3);
  max-width: 100%;
}
.hero-btn:hover { opacity: 0.9; }
.hero-btn-main { display: flex; align-items: center; gap: 8px; }
.hero-btn-sub { font-size: 11px; font-weight: 400; opacity: 0.9; }
</style>
</head>
<body style="margin:0;padding:0;">
<div class="jkw-root4">
  <div class="hero-badge">今、選ばれています</div>
  <div class="hero-bubble">
    <p class="hero-lead">✦ 3分で診断完了！</p>
    <p class="hero-text">全国2,000社以上の塾から あなたにぴったり<br>の塾が <strong style="color:#E8721A;">すぐに見つかる！</strong></p>
    <div class="hero-checks">
      <span class="hero-check"><span>✓</span>会員登録不要</span>
      <span class="hero-check"><span>✓</span>完全無料</span>
      <span class="hero-check"><span>✓</span>結果はすぐ表示</span>
    </div>
  </div>
  <div class="btn-wrap">
    <button class="hero-btn">
      <span class="hero-btn-main"> 診断を始める</span>
      <span class="hero-btn-sub">無料・かんたん3分</span>
    </button>
  </div>
</div>
</body>
</html>"""

# ---------- 2. 実績セクション (stats) ----------
HTML_STATS = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap" rel="stylesheet">
<style>
:root { --juku-pattern: """ + JUKU_PATTERN + """; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Noto Sans JP',sans-serif; background: #f5f5f5; padding: 40px 20px; display: flex; justify-content: center; background-image: var(--juku-pattern); background-size: 200px 200px; }
.stats { width: 100%; max-width: 800px; background: white; border-radius: 20px; padding: 32px 24px; }
.stats-title { text-align: center; font-size: 18px; font-weight: 900; color: #E8721A; margin-bottom: 24px; letter-spacing: 0.04em; }
.stats-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 1px; background: #F0E8E0; border-radius: 12px; overflow: hidden; }
.stat-item { background: white; padding: 20px 12px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.stat-label { font-size: 12px; color: #A07060; font-weight: 700; text-align: center; letter-spacing: 0.04em; }
.stat-num { font-size: clamp(24px,5vw,36px); font-weight: 900; color: #E8721A; line-height: 1; letter-spacing: -0.02em; }
.stat-unit { font-size: 12px; color: #E8721A; font-weight: 700; }
.stat-note { font-size: 10px; color: #C0A090; }
.stats-sub { text-align: center; font-size: 11px; color: #C0A090; margin-top: 16px; line-height: 1.7; }
</style>
</head>
<body>
<div class="stats">
  <p class="stats-title">塾講師ステーションが選ばれる理由</p>
  <div class="stats-grid">
    <div class="stat-item">
      <span class="stat-label">掲載求人件数</span>
      <div style="display:flex;align-items:baseline;gap:3px;"><span class="stat-num">1.5</span><span class="stat-unit">万件以上</span></div>
      <span class="stat-note">※1</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">年間利用者数</span>
      <div style="display:flex;align-items:baseline;gap:3px;"><span class="stat-num">2.7</span><span class="stat-unit">万人</span></div>
      <span class="stat-note">※2</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">累計利用者数</span>
      <div style="display:flex;align-items:baseline;gap:3px;"><span class="stat-num">76</span><span class="stat-unit">万人</span></div>
      <span class="stat-note">※2</span>
    </div>
  </div>
  <p class="stats-sub">※1 塾講師専門サービスを対象とした自社調査（2026年2月時点）<br>※2 Webサイト含むサービス全体の累計数値（2026年2月時点）</p>
</div>
</body>
</html>"""

# ---------- 3. 口コミセクション (reviews carousel) ----------
HTML_REVIEWS = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap" rel="stylesheet">
<style>
:root { --juku-pattern: """ + JUKU_PATTERN + """; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Noto Sans JP',sans-serif; background: #f5f5f5; padding: 40px 20px; display: flex; flex-direction: column; align-items: center; gap: 0; background-image: var(--juku-pattern); background-size: 200px 200px; }
.reviews { width: 100%; max-width: 800px; }
.reviews-title { text-align: center; font-size: 18px; font-weight: 900; color: #E8721A; margin-bottom: 6px; }
.reviews-sub { text-align: center; font-size: 13px; color: #A07060; margin-bottom: 20px; }
.carousel { overflow: hidden; border-radius: 16px; }
.carousel-track { display: flex; transition: transform 0.4s ease; }
.review-card { min-width: 100%; background: white; border-radius: 16px; padding: 24px 20px; display: flex; flex-direction: column; gap: 14px; }
.review-bubble { background: #FFF3EA; border-radius: 12px; padding: 14px 16px; }
.review-badge { display: inline-block; background: #E8721A; color: white; font-size: 11px; font-weight: 700; padding: 4px 14px; border-radius: 20px; margin-bottom: 10px; letter-spacing: 0.04em; }
.review-text { font-size: 14px; color: #3A2A20; line-height: 1.75; }
.review-person { display: flex; align-items: center; gap: 12px; }
.review-avatar { width: 44px; height: 44px; border-radius: 50%; background: #FFF3EA; border: 2px solid #FDDBB4; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.review-name { font-size: 13px; font-weight: 900; color: #3A2A20; }
.review-meta { font-size: 12px; color: #A07060; margin-top: 2px; }
.carousel-dots { display: flex; justify-content: center; gap: 8px; margin-top: 14px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #FDDBB4; cursor: pointer; transition: background 0.2s; border: none; }
.dot.active { background: #E8721A; }
.carousel-btns { display: flex; justify-content: center; gap: 12px; margin-top: 12px; }
.cbtn { width: 36px; height: 36px; border-radius: 50%; border: 2px solid #E8721A; background: white; color: #E8721A; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.cbtn:hover { background: #FFF3EA; }
</style>
</head>
<body>
<div class="reviews">
  <p class="reviews-title">先輩講師の声</p>
  <p class="reviews-sub">実際に働く大学生のリアルな体験談</p>
  <div class="carousel">
    <div class="carousel-track" id="track">
      <div class="review-card">
        <div class="review-bubble">
          <span class="review-badge">私のやりがい</span>
          <p class="review-text">苦手だった科目を克服して、定期試験で点数が伸びているのを見た時に、本当にやっていて良かったと感じました。</p>
        </div>
        <div class="review-person">
          <div class="review-avatar"><svg width="28" height="28" viewBox="0 0 40 40" fill="none"><circle cx="20" cy="15" r="9" fill="#FDDBB4"/><ellipse cx="20" cy="34" rx="14" ry="9" fill="#FDDBB4"/><path d="M11,22 Q14,17 20,17 Q26,17 29,22" fill="#3B5298"/><ellipse cx="20" cy="12" rx="9" ry="6" fill="#2C1810"/></svg></div>
          <div><p class="review-name">Aさん</p><p class="review-meta">関西大学・2年 / 個別指導塾</p></div>
        </div>
      </div>
      <div class="review-card">
        <div class="review-bubble">
          <span class="review-badge">選んだ理由</span>
          <p class="review-text">大学の近くで週2〜3回から働ける塾をすぐ見つけられました。授業との両立もしやすくて、勉強も塾バイトも充実しています。</p>
        </div>
        <div class="review-person">
          <div class="review-avatar"><svg width="28" height="28" viewBox="0 0 40 40" fill="none"><circle cx="20" cy="15" r="9" fill="#FDDBB4"/><ellipse cx="20" cy="34" rx="14" ry="9" fill="#FDDBB4"/><rect x="12" y="22" width="16" height="12" rx="4" fill="#3BB04A"/><ellipse cx="20" cy="11" rx="9" ry="7" fill="#2C2416"/></svg></div>
          <div><p class="review-name">Bさん</p><p class="review-meta">早稲田大学・3年 / 集団指導塾</p></div>
        </div>
      </div>
      <div class="review-card">
        <div class="review-bubble">
          <span class="review-badge">使ってみて</span>
          <p class="review-text">口コミで塾の雰囲気を事前に確認できたのが良かったです。働いてみたらイメージ通りで、職場環境にも満足しています。</p>
        </div>
        <div class="review-person">
          <div class="review-avatar"><svg width="28" height="28" viewBox="0 0 40 40" fill="none"><circle cx="20" cy="15" r="9" fill="#FDDBB4"/><ellipse cx="20" cy="34" rx="14" ry="9" fill="#FDDBB4"/><rect x="12" y="22" width="16" height="12" rx="4" fill="#E8721A"/><ellipse cx="20" cy="11" rx="9" ry="7" fill="#412402"/></svg></div>
          <div><p class="review-name">Cさん</p><p class="review-meta">東京大学・2年 / 個別指導塾</p></div>
        </div>
      </div>
    </div>
  </div>
  <div class="carousel-dots">
    <button class="dot active" onclick="goTo(0)"></button>
    <button class="dot" onclick="goTo(1)"></button>
    <button class="dot" onclick="goTo(2)"></button>
  </div>
  <div class="carousel-btns">
    <button class="cbtn" onclick="prev()">&#8249;</button>
    <button class="cbtn" onclick="next()">&#8250;</button>
  </div>
</div>
<script>
let cur=0;const total=3;const track=document.getElementById('track');const dots=document.querySelectorAll('.dot');
function goTo(n){cur=n;track.style.transform='translateX(-'+(cur*100)+'%)';dots.forEach(function(d,i){d.classList.toggle('active',i===cur);})}
function next(){goTo((cur+1)%total);}function prev(){goTo((cur-1+total)%total);}
setInterval(next,5000);
</script>
</body>
</html>"""

# ---------- 4. 特徴セクション (jkw-root3) ★修正: ?→絵文字 ----------
HTML_ROOT3 = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
.jkw-root3 {
  --juku-pattern: """ + JUKU_PATTERN + """;
  width: 100%;
  max-width: 100vw;
  box-sizing: border-box;
  background: #f5f5f5;
  padding: 40px 12px;
  display: flex;
  justify-content: center;
  background-image: var(--juku-pattern);
  background-size: 200px 200px;
  overflow-x: hidden;
}
.jkw-root3, .jkw-root3 * { box-sizing: border-box; }
.features { width: 100%; max-width: 800px; min-width: 0; background: white; border-radius: 24px; padding: 52px 36px 48px; font-family: 'Zen Maru Gothic','Hiragino Maru Gothic ProN',sans-serif; }
.features-title { text-align: center; font-size: clamp(20px,5vw,30px); font-weight: 900; color: #E8721A; margin-bottom: 10px; letter-spacing: 0.03em; line-height: 1.3; }
.features-subtitle { text-align: center; font-size: 15px; font-weight: 700; color: #C49070; margin-bottom: 48px; }
.feature-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; }
.feature-card { min-width: 0; width: 100%; background: #FFF3EA; border-radius: 20px; padding: 28px 14px; display: flex; flex-direction: column; align-items: center; gap: 12px; position: relative; margin-top: 20px; }
.feature-badge { position: absolute; top: -20px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; max-width: 90%; }
.badge-top { background: #E8721A; color: white; font-size: 13px; font-weight: 900; padding: 6px 20px; border-radius: 8px 8px 0 0; white-space: nowrap; letter-spacing: 0.06em; }
.badge-tail { width: 0; height: 0; border-left: 26px solid transparent; border-right: 26px solid transparent; border-top: 14px solid #E8721A; }
.feature-icon { font-size: 44px; margin-top: 8px; }
.feature-name { font-size: 16px; font-weight: 900; color: #5C2D0A; text-align: center; line-height: 1.55; letter-spacing: 0.04em; overflow-wrap: break-word; word-break: keep-all; }
.feature-divider { width: 36px; height: 3px; background: #E8721A; border-radius: 2px; opacity: 0.5; }
.feature-desc { font-size: 13px; font-weight: 500; color: #A07060; text-align: center; line-height: 1.7; overflow-wrap: break-word; }
@media (max-width: 700px) { .feature-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } .feature-card:nth-child(3) { grid-column: 1 / -1; } }
@media (max-width: 480px) { .features { padding: 44px 20px 36px; } .feature-cards { grid-template-columns: 1fr; gap: 20px; } .feature-card:nth-child(3) { grid-column: auto; } }
</style>
</head>
<body style="margin:0;padding:0;">
<div class="jkw-root3">
  <div class="features">
    <h2 class="features-title">塾講師ステーション 3つの特徴</h2>
    <p class="features-subtitle">選ばれる理由がここにあります ✦</p>
    <div class="feature-cards">
      <div class="feature-card">
        <div class="feature-badge"><div class="badge-top">特徴 ①</div><div class="badge-tail"></div></div>
        <div class="feature-icon">📋</div>
        <p class="feature-name">業界最大級の求人数</p>
        <div class="feature-divider"></div>
        <p class="feature-desc">見逃しゼロで理想の塾が見つかる</p>
      </div>
      <div class="feature-card">
        <div class="feature-badge"><div class="badge-top">特徴 ②</div><div class="badge-tail"></div></div>
        <div class="feature-icon">🔍</div>
        <p class="feature-name">こだわり条件で<br>かんたん検索</p>
        <div class="feature-divider"></div>
        <p class="feature-desc">エリア・給与・科目など<br>絞り込みが自由自在</p>
      </div>
      <div class="feature-card">
        <div class="feature-badge"><div class="badge-top">特徴 ③</div><div class="badge-tail"></div></div>
        <div class="feature-icon">⭐</div>
        <p class="feature-name">口コミ・評判が充実</p>
        <div class="feature-divider"></div>
        <p class="feature-desc">実際に働いた人の<br>リアルな声がわかる</p>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""

# ---------- 5. CTAセクション (jkw-root2) ★修正: 🎯/3分/塾ブランド診断 ----------
HTML_ROOT2 = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap" rel="stylesheet">
<style>
.jkw-root2 {
  --juku-pattern: """ + JUKU_PATTERN + """;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  font-family: 'Noto Sans JP', sans-serif;
  background: #f5f5f5;
  padding: 24px 16px;
  display: flex;
  justify-content: center;
  background-image: var(--juku-pattern);
  background-size: 200px 200px;
  overflow-x: hidden;
}
.jkw-root2, .jkw-root2 * { box-sizing: border-box; }
.juku-wrap { width: 100%; max-width: 375px; background: #FFF3EA; border-radius: 20px; padding: 20px 16px; display: flex; flex-direction: column; gap: 14px; }
.juku-card { background: white; border-radius: 16px; padding: 22px 18px; display: flex; flex-direction: column; align-items: center; gap: 12px; box-shadow: 0 6px 18px rgba(196,144,112,0.14); }
.juku-badge { background: #FFE4CC; color: #C4671A; font-size: 11px; font-weight: 700; padding: 5px 14px; border-radius: 20px; letter-spacing: 0.03em; }
.juku-eyebrow { font-size: 12px; font-weight: 700; color: #C49070; letter-spacing: 0.08em; text-align: center; }
.juku-btn { width: 100%; background: #3BB04A; color: white; border: none; border-radius: 12px; padding: 18px 16px; font-family: 'Noto Sans JP', sans-serif; font-size: clamp(14px, 3vw, 17px); font-weight: 900; letter-spacing: 0.03em; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; text-align: center; box-shadow: 0 6px 14px rgba(59,176,74,0.3); }
.juku-stats { display: flex; justify-content: center; gap: 16px; width: 100%; padding-top: 10px; border-top: 1px dashed #F0D9C0; }
.juku-stat { text-align: center; }
.juku-stat-num { font-size: 15px; font-weight: 900; color: #E8721A; display: block; }
.juku-stat-label { font-size: 10px; color: #B09080; font-weight: 700; }
.juku-note { font-size: 11px; color: #B09080; line-height: 1.7; text-align: center; }
.juku-line-card { background: white; border-radius: 16px; padding: 20px 18px; display: flex; flex-direction: column; gap: 12px; box-shadow: 0 6px 18px rgba(196,144,112,0.14); }
.juku-line-header { display: flex; align-items: center; gap: 12px; }
.juku-line-icon { width: 40px; height: 40px; background: #06C755; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.juku-line-title { font-size: 14px; font-weight: 900; color: #2C2C2A; line-height: 1.4; }
.juku-line-body { font-size: 12px; color: #7A6050; line-height: 1.75; }
.juku-line-body strong { color: #2C2C2A; font-weight: 700; }
.juku-line-btn { width: 100%; background: #06C755; color: white; border: none; border-radius: 10px; padding: 13px; font-family: 'Noto Sans JP', sans-serif; font-size: 14px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 6px 14px rgba(6,199,85,0.28); }
</style>
</head>
<body style="margin:0;padding:0;">
<div class="jkw-root2">
  <div class="juku-wrap">
    <div class="juku-card">
      <p class="juku-badge">今すぐ結果がわかる</p>
      <p class="juku-eyebrow">3分・無料・結果はLINEで届く</p>
      <button class="juku-btn"><span>🎯</span>3分で自分に合う塾を診断する</button>
      <div class="juku-stats">
        <div class="juku-stat">
          <span class="juku-stat-num">トップクラスの</span>
          <span class="juku-stat-label">掲載求人数</span>
        </div>
        <div class="juku-stat">
          <span class="juku-stat-num">高い</span>
          <span class="juku-stat-label">平均時給</span>
        </div>
      </div>
      <p class="juku-note">※希望条件に合う求人のみ配信します<br>※配信停止はいつでも可能です</p>
    </div>
    <div class="juku-line-card">
      <div class="juku-line-header">
        <div class="juku-line-icon">
          <svg width="24" height="24" viewBox="0 0 22 22" fill="none">
            <path d="M11 2C6.03 2 2 5.8 2 10.5c0 2.6 1.3 4.9 3.3 6.5L4.5 20l3.3-1.7C8.8 18.7 9.9 19 11 19c4.97 0 9-3.8 9-8.5S15.97 2 11 2z" fill="white"/>
          </svg>
        </div>
        <p class="juku-line-title">公式LINEで塾バイトの解像度を上げよう</p>
      </div>
      <p class="juku-line-body">自分に合った<strong>塾ブランド診断・月収診断</strong>など、塾バイトのリアルがわかるコンテンツを配信中。<strong>友だち追加</strong>で今すぐ受け取ろう。</p>
      <button class="juku-line-btn">
        <svg width="18" height="18" viewBox="0 0 22 22" fill="none" style="flex-shrink:0">
          <path d="M11 2C6.03 2 2 5.8 2 10.5c0 2.6 1.3 4.9 3.3 6.5L4.5 20l3.3-1.7C8.8 18.7 9.9 19 11 19c4.97 0 9-3.8 9-8.5S15.97 2 11 2z" fill="white"/>
        </svg>
        友だち追加する
      </button>
    </div>
  </div>
</div>
</body>
</html>"""

# ============================================================
# Google Doc 作成
# ============================================================

DOC_TITLE = 'ST LP Instagramコンポーネント 修正版（2026-08-18）'

print(f'ドキュメント作成中: {DOC_TITLE}')
doc = api('https://docs.googleapis.com/v1/documents', {'title': DOC_TITLE})
doc_id = doc['documentId']
print(f'作成完了: {doc_id}')

# セクション定義（番号・ラベル・HTML・修正メモ）
SECTIONS = [
    ('1. FVセクション（jkw-root4）', HTML_ROOT4, '変更なし'),
    ('2. 実績セクション（stats）', HTML_STATS, '変更なし'),
    ('3. 口コミセクション（reviews）', HTML_REVIEWS, '変更なし'),
    ('4. 特徴セクション（jkw-root3）', HTML_ROOT3, '★修正: アイコン ? → 📋 / 🔍 / ⭐'),
    ('5. CTAセクション（jkw-root2）', HTML_ROOT2, '★修正: ボタン🎯 / 3分で / 塾ブランド診断'),
]

# ヘッダー挿入
header_text = (
    f'{DOC_TITLE}\n'
    '修正サマリー:\n'
    '  特徴セクション(root3): アイコン ? → 📋(求人数) / 🔍(検索) / ⭐(口コミ)\n'
    '  CTAセクション(root2): ボタンアイコン ? → 🎯 / 10秒で → 3分で / 塾診断 → 塾ブランド診断\n\n'
)

api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate', {
    'requests': [{
        'insertText': {
            'text': header_text,
            'endOfSegmentLocation': {'segmentId': ''}
        }
    }]
})
print('ヘッダー挿入完了')

# セクションごとに挿入
for i, (section_title, html_content, note) in enumerate(SECTIONS, 1):
    content = f'{"="*60}\n{section_title}\n{note}\n{"="*60}\n\n{html_content}\n\n'
    api(f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate', {
        'requests': [{
            'insertText': {
                'text': content,
                'endOfSegmentLocation': {'segmentId': ''}
            }
        }]
    })
    print(f'セクション {i}/5 挿入完了: {section_title}')
    time.sleep(0.3)  # 429対策

url = f'https://docs.google.com/document/d/{doc_id}/edit'
print(f'\n完了!')
print(f'URL: {url}')
