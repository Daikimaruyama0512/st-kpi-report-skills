#!/usr/bin/env python3
"""
SessionStart フック: 未消化の引き継ぎメモを自動読み込みする。
- 対象: 直近 CC_HANDOFF_HOURS 時間以内に作成され、status が「引き継ぎ中」のもの
- 1件 → 本文を自動注入してステータスを「再開済み」に更新
- 複数 → 一覧を表示してユーザーに選ばせる

環境変数:
  CC_HANDOFF_MAX_CHARS  自動注入する本文の最大文字数。デフォルト 3000
  CC_HANDOFF_HOURS      対象期間（時間）。デフォルト 24
"""
import json, sys, os, re
from pathlib import Path
from datetime import datetime, timedelta

# ── パス設定 ──────────────────────────────────────────────────
_HOOKS_DIR   = Path(__file__).parent
HANDOFFS_DIR = _HOOKS_DIR.parent / "handoffs"

# ── 設定（環境変数で上書き可） ────────────────────────────────
MAX_CHARS = int(os.environ.get("CC_HANDOFF_MAX_CHARS", "3000"))
HOURS     = int(os.environ.get("CC_HANDOFF_HOURS",    "24"))


# ── メモ操作ユーティリティ ────────────────────────────────────
def get_status(text: str) -> str | None:
    m = re.search(r'status:\s*(\S+)', text)
    return m.group(1) if m else None


def set_status(filepath: Path, new_status: str) -> None:
    text    = filepath.read_text(encoding="utf-8")
    updated = re.sub(r'(status:\s*)\S+', f'\\g<1>{new_status}', text, count=1)
    filepath.write_text(updated, encoding="utf-8")


def get_body(text: str) -> str:
    """YAML フロントマター（---..---）を除いた本文を返す"""
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else text.strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…（文字数上限により省略）"


# ── メイン ────────────────────────────────────────────────────
def main() -> None:
    try:
        json.load(sys.stdin)   # stdin を消費する（必須）
    except Exception:
        pass

    if not HANDOFFS_DIR.exists():
        sys.exit(0)

    cutoff = datetime.now() - timedelta(hours=HOURS)

    # 候補ファイル抽出（新しい順）
    candidates: list[tuple[Path, datetime, str]] = []
    for f in sorted(HANDOFFS_DIR.glob("*.md"), reverse=True):
        if f.name == "TEMPLATE.md":
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue
            text   = f.read_text(encoding="utf-8")
            status = get_status(text)
            if status == "引き継ぎ中":
                candidates.append((f, mtime, text))
        except Exception:
            continue

    # ── 0件: 静かに終了 ─────────────────────────────────────
    if not candidates:
        sys.exit(0)

    # ── 1件: 自動読み込み ────────────────────────────────────
    if len(candidates) == 1:
        filepath, mtime, text = candidates[0]

        # ステータスを即座に更新（同じメモが二度読み込まれないように）
        try:
            set_status(filepath, "再開済み")
        except Exception:
            pass

        body    = get_body(text)
        preview = truncate(body, MAX_CHARS)

        output = (
            f"【引き継ぎメモを自動読み込みしました: {filepath.name}】\n"
            f"作成: {mtime.strftime('%Y-%m-%d %H:%M')}\n"
            "─────────────────────────────────────────\n"
            f"{preview}\n"
            "─────────────────────────────────────────\n"
            "上記の引き継ぎメモを読み込みました。\n"
            "ユーザーが「続き」と言ったら【次にやること】の最初の項目から作業を再開してください。"
        )
        print(output)

    # ── 複数件: 一覧を表示して選ばせる ──────────────────────
    else:
        lines = [
            f"【未消化の引き継ぎメモが {len(candidates)} 件あります。どれから再開しますか？】\n"
        ]
        for i, (f, mtime, text) in enumerate(candidates, 1):
            body    = get_body(text)
            preview = body.replace("\n", " ")[:80]
            lines.append(
                f"{i}. {f.name} （{mtime.strftime('%Y-%m-%d %H:%M')}）\n"
                f"   {preview}…"
            )

        lines += [
            "",
            "番号を教えていただければ、そのメモを読み込んで再開します。",
            "再開後はそのメモの status を「再開済み」に書き換えてから作業を開始してください。",
        ]

        # 候補ファイルパスをコンテキストに追加（Claude が更新できるように）
        lines += [
            "",
            "[システム補足] 選択されたメモのファイルを Read し、",
            "status: 引き継ぎ中 を status: 再開済み に Edit で書き換えてから作業を開始すること。",
            f"候補ファイル: {', '.join(str(f) for f, _, _ in candidates)}",
        ]

        print("\n".join(lines))

    sys.exit(0)


if __name__ == "__main__":
    main()
