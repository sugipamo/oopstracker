# OOPSTracker

AI Agent Code Loop Detection and Prevention Library - コード構造の類似性を検出するためのPythonツール

## 概要

OOPSTrackerは、AIエージェントがコード生成時に同じパターンや類似コードを繰り返し生成することを検出・防止するためのライブラリです。Pythonコードの構造的な類似性を検出し、重複コードの発見やリファクタリングの機会を提供します。AST解析とSimHashアルゴリズムを使用して、高精度な類似性検出を実現します。

## 主な機能

- **類似コード検出**: AST解析による構造的な類似性検出
- **SimHashアルゴリズム**: 高速かつ正確な類似性計算
- **統合検出サービス**: 複数の検出手法を統合した高精度な検出
- **SQLiteベースの永続化**: コード履歴の効率的な管理
- **非同期API**: FastAPIを使用した高性能なWeb API
- **AIエージェント対応**: LLMが生成するコードのループ検出に特化
- **関数・クラス単位での類似性評価**: 詳細な構造解析
- **大規模コードベースへの対応**: 効率的なインデックスとキャッシュ

## インストール

```bash
# UV環境での開発用インストール
cd evocraft
uv pip install -e packages/oopstracker

# または直接インストール
pip install oopstracker
```

## 基本的な使い方

### 統合検出サービスの使用（推奨）

```python
from oopstracker import UnifiedDetectionService, UnifiedRepository

# リポジトリとサービスの初期化
repository = UnifiedRepository()
detector = UnifiedDetectionService(repository)

# コードの類似性チェック
code = """
def calculate_sum(a, b):
    return a + b
"""

# 類似コードの検出
similar_codes = await detector.find_similar_codes(code, threshold=0.8)

# コードの記録
await detector.record_code(
    code=code,
    file_path="example.py",
    intent="数値の加算",
    context={"function": "calculate_sum"}
)
```

### 低レベルAPIの使用

```python
from oopstracker import ASTAnalyzer, SimHashCalculator, CodeAnalyzer

# アナライザーの初期化
ast_analyzer = ASTAnalyzer()
simhash_calculator = SimHashCalculator()
code_analyzer = CodeAnalyzer(ast_analyzer, simhash_calculator)

# コードの解析
source_code = '''
def calculate_sum(a, b):
    return a + b
'''

# 構造解析
result = code_analyzer.analyze(source_code)
print(f"関数: {result['features']['functions']}")
print(f"複雑度: {result['metrics']['complexity']}")
```

## 類似性検出の例

```python
# 2つのコードの類似性を計算
code1 = '''
def add_numbers(x, y):
    return x + y
'''

code2 = '''
def sum_values(a, b):
    return a + b
'''

features1 = code_analyzer.extract_features(code1)
features2 = code_analyzer.extract_features(code2)

hash1 = simhash_calculator.calculate(features1)
hash2 = simhash_calculator.calculate(features2)

similarity = simhash_calculator.similarity(hash1, hash2)
print(f"類似度: {similarity:.2%}")
```

## プロジェクト全体の分析

```python
from pathlib import Path

# プロジェクト内の類似コードを検出
project_path = Path("/path/to/project")
similar_functions = []

# 全Pythonファイルを解析
python_files = list(project_path.rglob("*.py"))
for i, file1 in enumerate(python_files):
    for file2 in python_files[i+1:]:
        # ファイル内容を読み込んで比較
        with open(file1) as f1, open(file2) as f2:
            similarity = analyze_similarity(f1.read(), f2.read())
            if similarity > 0.8:
                similar_functions.append((file1, file2, similarity))
```

## CLI使用例

```bash
# 類似コードの検出
oopstracker analyze your_code.py --threshold 0.8

# コード履歴の表示
oopstracker history --limit 10

# 統計情報の表示
oopstracker stats

# プロジェクト全体の分析
oopstracker scan /path/to/project --output report.json
```

## API使用例

```bash
# APIサーバーの起動
uvicorn oopstracker.api:app --reload

# 類似コードの検出
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a, b): return a + b"}'

# コード履歴の取得
curl http://localhost:8000/history?limit=10
```

## アーキテクチャ

### 主要コンポーネント

1. **ASTAnalyzer**: Pythonコードの構造を解析
2. **SimHashCalculator**: 類似性計算のためのハッシュ値生成
3. **CodeAnalyzer**: 統合的なコード分析機能を提供
4. **UnifiedDetectionService**: 複数の検出手法を統合
5. **UnifiedRepository**: SQLiteベースのデータ永続化

### 解析対象

- 関数とメソッドの構造
- クラスの定義と階層
- 制御フローパターン
- インポートと依存関係

## 設定オプション

### 環境変数

```bash
# データベース設定
export OOPSTRACKER_DB_URL="sqlite:///oopstracker.db"

# 検出設定
export OOPSTRACKER_THRESHOLD=0.8
export OOPSTRACKER_MAX_HISTORY=1000

# API設定
export OOPSTRACKER_API_HOST="0.0.0.0"
export OOPSTRACKER_API_PORT=8000
```

### プログラムでの設定

```python
# SimHashのカスタマイズ
calculator = SimHashCalculator(hash_size=64)  # ハッシュサイズの調整

# 分析の詳細度設定
analyzer = CodeAnalyzer(
    ast_analyzer=ast_analyzer,
    simhash_calculator=calculator
)

# 統合サービスの設定
from oopstracker.config import Settings

settings = Settings(
    db_url="sqlite:///custom.db",
    similarity_threshold=0.85,
    max_history_size=5000
)

repository = UnifiedRepository(settings=settings)
detector = UnifiedDetectionService(repository, settings=settings)
```

## 実用例

### 重複コードの検出

```python
def find_duplicate_functions(project_path):
    """プロジェクト内の重複関数を検出"""
    duplicates = []
    
    # 全関数を抽出して比較
    for file_path in Path(project_path).rglob("*.py"):
        with open(file_path) as f:
            units = ast_analyzer.parse_code(f.read(), str(file_path))
            
        for unit in units:
            if unit.type == "function":
                # 他の関数と比較
                for other_file, other_unit in all_functions:
                    if is_similar(unit, other_unit):
                        duplicates.append((file_path, other_file))
    
    return duplicates
```

### コード品質メトリクス

```python
# コードの複雑度分析
def analyze_complexity(source_code):
    result = code_analyzer.analyze(source_code)
    
    metrics = {
        "lines_of_code": result["metrics"]["loc"],
        "cyclomatic_complexity": result["metrics"]["complexity"],
        "nesting_depth": result["metrics"]["nesting_depth"],
        "function_count": len(result["features"]["functions"]),
        "class_count": len(result["features"]["classes"])
    }
    
    return metrics
```

## パフォーマンス考慮事項

- 大規模ファイルは段階的に処理
- キャッシュを活用して再計算を削減
- 並列処理による高速化が可能

## トラブルシューティング

### メモリ使用量が多い場合

```python
# バッチ処理で大規模プロジェクトを分析
def analyze_in_batches(files, batch_size=100):
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        process_batch(batch)
```

### 解析エラーへの対処

```python
# エラーハンドリングの例
try:
    result = code_analyzer.analyze(source_code)
except SyntaxError:
    print("構文エラー: コードを確認してください")
except Exception as e:
    print(f"解析エラー: {e}")
```

## 開発

### セットアップ

```bash
# 開発環境のセットアップ
cd evocraft
uv sync --dev

# パッケージのインストール
uv pip install -e packages/oopstracker
```

### テスト

```bash
# 単体テスト
uv run pytest packages/oopstracker/tests/unit

# 統合テスト
uv run pytest packages/oopstracker/tests/integration

# カバレッジレポート
uv run pytest packages/oopstracker --cov=oopstracker --cov-report=html
```

### コード品質チェック

```bash
# Ruffによるリンティング
uv run ruff check packages/oopstracker

# Mypyによる型チェック
uv run mypy packages/oopstracker

# Blackによるフォーマット
uv run black packages/oopstracker
```

## 今後の拡張予定

- 追加のプログラミング言語サポート（JavaScript/TypeScript、Go、Rust）
- より詳細な類似性メトリクス（セマンティック分析）
- IDE統合プラグイン（VS Code、PyCharm）
- Web UIの提供
- クラウドベースの分析サービス
- GitHubアクションとの統合

## ライセンス

MIT License

## コントリビューション

プルリクエストを歓迎します。大きな変更を行う場合は、まずissueを作成して変更内容について議論してください。

1. Forkする
2. Feature branchを作成する (`git checkout -b feature/amazing-feature`)
3. 変更をコミットする (`git commit -m 'Add some amazing feature'`)
4. Branchにpushする (`git push origin feature/amazing-feature`)
5. Pull Requestを作成する

## 関連パッケージ

- `intent-unified`: コードの意図解析ツール
- `code-decomposer`: 大規模関数の分解ツール
- `pattern-intent`: パターンベースの分析ツール