#!/usr/bin/env python3
"""
UserPromptSubmit フック: コンテキスト使用量を監視し、2段階警告を注入する。
- Soft 警告: キリが良ければ区切りを推奨（佳境なら継続可）
- Hard 警告: 最小作業単位だけ終わらせて即座に引き継ぎメモ作成・終了
各段階は 1 セッションにつき 1 回だけ通知する。

環境変数:
  CC_SOFT_KB   ソフト閾値（KB）。デフォルト 150
  CC_HARD_KB   ハード閾値（KB）。デフォルト 300
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timedelta

# ── パス設定 ──────────────────────────────────────────────────
_HOOKS_DIR = Path(__file__).parent
STATE_FILE  = _HOOKS_DIR / ".warn_state.json"
HANDOFFS_DIR = _HOOKS_DIR.parent / "handoffs"

# ── 閾値（環境変数で上書き可） ────────────────────────────────
SOFT_KB = int(os.environ.get("CC_SOFT_KB", "150"))
HARD_KB = int(os.environ.get("CC_HARD_KB", "300"))


# ── 状態ファイル操作 ──────────────────────────────────────────
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        # 古いセッション（48h超）を定期クリーンアップ
        cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
        pruned = {sid: v for sid, v in state.items()
                  if v.get("updated_at", "9999") >= cutoff}
        STATE_FILE.write_text(json.dumps(pruned, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


# ── transcript サイズ計測 ─────────────────────────────────────
def get_transcript_kb(transcript_path: str) -> float:
    try:
        p = Path(transcript_path)
        if p.exists():
            return p.stat().st_size / 1024
    except Exception:
        pass
    return 0.0


# ── 引き継ぎメモ テンプレート ─────────────────────────────────
HANDOFF_TEMPLATE = """\
---
status: 引き継ぎ中
created: {timestamp}
---

## ゴール
（このセッションで達成しようとしていること）

## いまの状態
（どこまで進んだか・何が完了して何が未完か）

## 編集途中のファイル
- path/to/file.py: 変更内容メモ

## 失敗した試みと理由
- 試み: xxx → 失敗理由: yyy（次セッションで同じ失敗を繰り返さないために必須）

## 次にやること
1. 最初にやること
2. その次
"""

SOFT_WARNING = """\
⚠️  [コンテキスト警告 {size:.0f}KB / ソフト閾値 {soft}KB]
会話量が増えてきました。
- キリの良い区切りがあれば → 引き継ぎメモを作成してセッションを終了することを推奨します
- 佳境・作業の途中であれば → そのまま続行して構いません
（この通知は1セッションにつき1回のみ）"""

HARD_WARNING = """\
⛔ [コンテキスト終了通知 {size:.0f}KB / ハード閾値 {hard}KB]
コンテキストが限界に近づいています。
いま取り組んでいる作業単位だけ最小限で終わらせ、引き継ぎメモを作成してセッションを終了してください。

▼ 引き継ぎメモの作成手順
1. .claude/handoffs/YYYY-MM-DD_HH-MM-SS.md を新規作成
2. 必須項目: ゴール／いまの状態／編集途中のファイル／失敗した試みと理由／次にやること
3. ヘッダーに「status: 引き継ぎ中」を必ず記載する

テンプレート: .claude/handoffs/TEMPLATE.md を参照"""


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    session_id      = data.get("session_id", "unknown")
    transcript_path = data.get("transcript_path", "")
    size_kb         = get_transcript_kb(transcript_path)

    state           = load_state()
    sess            = state.get(session_id, {"soft_warned": False, "hard_warned": False})

    warning = None

    if size_kb >= HARD_KB and not sess.get("hard_warned"):
        warning = HARD_WARNING.format(size=size_kb, hard=HARD_KB)
        sess["hard_warned"] = True
        sess["soft_warned"] = True   # hard 通知時は soft も既済扱い

    elif size_kb >= SOFT_KB and not sess.get("soft_warned"):
        warning = SOFT_WARNING.format(size=size_kb, soft=SOFT_KB)
        sess["soft_warned"] = True

    sess["updated_at"] = datetime.now().isoformat()
    state[session_id]  = sess
    save_state(state)

    if warning:
        print(warning)
    # 閾値未達・通知済みの場合は何も出力しない（静かに終了）

    sys.exit(0)


if __name__ == "__main__":
    main()
