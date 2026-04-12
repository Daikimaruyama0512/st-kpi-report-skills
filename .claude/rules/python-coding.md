## Pythonスクリプト コーディング規則

このプロジェクトはWindows環境（cp932端末）でPythonを実行する。
以下の規則を必ず守ること。

---

### 1. 文字エンコーディング（最重要）

#### ファイル出力は必ず utf-8-sig
```python
# CSV出力
df.to_csv("output.csv", index=False, encoding="utf-8-sig")

# テキストファイル出力
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(text)
```

#### コンソール出力でUnicodeEncodeErrorが出る場合
絵文字・特殊記号を使わない。または標準出力をUTF-8でラップ：
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

**NG**: `print("✅ 完了")` → Windowscp932端末でクラッシュする
**OK**: `print("完了")` またはファイルに書き出す

---

### 2. BigQuery クエリパターン

#### ビュー（VIEW）に対してWHERE＋集計する場合はCTEを必ず使う

BigQueryのビューに直接 `GROUP BY` + `HAVING SUM(...)` を使うと
「Aggregations of aggregations are not allowed」エラーが発生する。

**NG**:
```sql
SELECT ad_name, SUM(spend) AS spend
FROM `project.dataset.view_name`
GROUP BY ad_name
HAVING SUM(spend) > 1000
```

**OK（CTEパターン）**:
```sql
WITH agg AS (
  SELECT
    ad_name,
    SUM(spend) AS spend
  FROM `project.dataset.view_name`
  GROUP BY ad_name
)
SELECT * FROM agg
WHERE spend > 1000
```

#### SAFE_DIVIDE を使う（ゼロ除算防止）
```sql
SAFE_DIVIDE(SUM(purchase), NULLIF(SUM(link_clicks), 0)) AS cvr
```

---

### 3. BigQuery 必須パッケージ

BigQueryのクエリ結果を `to_dataframe()` で取得するには以下が必要：
```
pip install db-dtypes pyarrow
```

スクリプト冒頭のコメントに記載しておくこと：
```python
# 必要: pip install google-cloud-bigquery db-dtypes pyarrow
```

---

### 4. pandas 表示

#### 日本語テキストを含む列は画面に出力しない
→ 文字化けする。ファイルに書き出すか、短縮表示のみ：
```python
# 全文はCSVに保存
df.to_csv("output.csv", index=False, encoding="utf-8-sig")

# 画面表示は数値列のみ
print(df[['ad_name', 'spend', 'cvr']].to_string(index=False))
```

---

### 5. Google Data Transfer Service（スケジュールクエリ）

スケジュールクエリを作成する場合、同名クエリの重複作成を避けること：
```python
# 既存確認 → 存在すればスキップ
for config in transfer_client.list_transfer_configs(parent=parent):
    if config.display_name == display_name:
        print(f"既存: {config.name} → スキップ")
        return config.name
```
