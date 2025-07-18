# OOPStracker `check` コマンド クイックガイド

## 最もよく使うコマンド

```bash
# カレントディレクトリをチェック（デフォルトで意味的解析も実行）
uv run oopstracker check

# 特定のディレクトリをチェック
uv run oopstracker check src/

# 結果の表示数を制限
uv run oopstracker check --limit 10
```

## デフォルト動作（v2.0以降）

`check`コマンドは以下をデフォルトで実行します：

1. **構造的解析**: AST（抽象構文木）による高速な重複検出
2. **意味的解析**: LLMを使用した意味的な類似性の判定（自動有効）
3. **自明な重複の除外**: getter/setter、passクラスなどを自動除外

## 主要オプション

### 表示制御
```bash
# 重複の表示数を制限（デフォルト: 50）
uv run oopstracker check --limit 20

# 自明な重複も含めて表示
uv run oopstracker check --include-trivial

# 重複解析のみ（ファイルスキャンをスキップ）
uv run oopstracker check --duplicates-only
```

### 閾値調整
```bash
# 構造的類似度の閾値を調整（0.0-1.0、デフォルト: 0.7）
uv run oopstracker check --threshold 0.8

# 意味的類似度の閾値を調整（0.0-1.0、デフォルト: 0.7）
uv run oopstracker check --semantic-threshold 0.8
```

### パフォーマンス調整
```bash
# 意味的解析を無効化（高速化）
uv run oopstracker check --no-semantic

# 網羅的な検索（精度優先、低速）
uv run oopstracker check --exhaustive

# キャッシュを無視して全ファイルを再スキャン
uv run oopstracker check --force
```

### ファイル選択
```bash
# 特定のパターンのファイルのみチェック
uv run oopstracker check --pattern "test_*.py"

# .gitignoreを無視
uv run oopstracker check --no-gitignore
```

## 出力の見方

```
🧠 Semantic analysis enabled (LLM-based)
🔍 Checking . for updates and duplicates...
📁 Found 40 Python files
📝 15 files have changed since last scan

⚠️  Found 20 potential duplicate pairs (threshold: 0.7):

 1. Similarity: 0.850                    ← 構造的類似度
    function: process_data in src/data.py:45
    function: handle_data in src/handler.py:12

🔍 Semantic analysis found 5 meaningful duplicates:

 1. Semantic similarity: 0.800 (confidence: 0.850)  ← 意味的類似度と信頼度
    Method: llm_semantic
    process_data in src/data.py
    handle_data in src/handler.py
    Reasoning: 類似度 80%...           ← LLMによる判定理由
```

## よくある使用例

### 1. プロジェクト全体の重複チェック（推奨）
```bash
uv run oopstracker check
```

### 2. テストコードを除外して本番コードのみチェック
```bash
uv run oopstracker check src/ --pattern "*.py" --limit 20
```

### 3. CI/CDでの使用（高速モード）
```bash
uv run oopstracker check --no-semantic --threshold 0.8 --limit 10
```

### 4. 詳細な解析（時間をかけて精査）
```bash
uv run oopstracker check --exhaustive --semantic-threshold 0.6
```

### 5. 変更されたファイルのみチェック（デフォルト動作）
```bash
# キャッシュにより、変更されたファイルのみが自動的にスキャンされます
uv run oopstracker check
```

## トラブルシューティング

### LLM接続エラー
```bash
# 意味的解析を無効化して実行
uv run oopstracker check --no-semantic
```

### メモリ不足
```bash
# ファイル数を制限
uv run oopstracker check src/module/ --limit 10
```

### 実行が遅い
```bash
# 高速モードで実行（精度は下がる可能性）
uv run oopstracker check --no-semantic --fast
```

## Tips

1. **初回実行は時間がかかります** - 全ファイルのAST解析とキャッシュ作成のため
2. **2回目以降は高速** - 変更されたファイルのみをスキャン
3. **意味的解析は並列実行** - デフォルトで3つまで同時実行
4. **閾値の目安**:
   - 0.9以上: ほぼ同一のコード
   - 0.7-0.9: 類似した実装
   - 0.5-0.7: 部分的に類似