# OOPSTracker

コード構造の類似性を検出するためのPythonツール

## 概要

OOPSTrackerは、Pythonコードの構造的な類似性を検出し、重複コードの発見やリファクタリングの機会を提供するツールです。

## 主な機能

- コード構造の分析と比較
- 類似コードパターンの検出
- 関数・クラス単位での類似性評価
- 大規模コードベースへの対応

## インストール

```bash
# UV環境での開発用インストール
cd evocraft
uv pip install -e packages/oopstracker

# または直接インストール
pip install oopstracker
```

## 基本的な使い方

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

## アーキテクチャ

### 主要コンポーネント

1. **ASTAnalyzer**: Pythonコードの構造を解析
2. **SimHashCalculator**: 類似性計算のためのハッシュ値生成
3. **CodeAnalyzer**: 統合的なコード分析機能を提供

### 解析対象

- 関数とメソッドの構造
- クラスの定義と階層
- 制御フローパターン
- インポートと依存関係

## 設定オプション

```python
# SimHashのカスタマイズ
calculator = SimHashCalculator(hash_size=64)  # ハッシュサイズの調整

# 分析の詳細度設定
analyzer = CodeAnalyzer(
    ast_analyzer=ast_analyzer,
    simhash_calculator=calculator
)
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

## 今後の拡張予定

- 追加のプログラミング言語サポート
- より詳細な類似性メトリクス
- IDE統合プラグイン
- Web UIの提供

## ライセンス

MIT License

## コントリビューション

プルリクエストを歓迎します。バグ報告や機能要望はIssueでお知らせください。

## 関連パッケージ

- `intent-unified`: コードの意図解析ツール
- `code-decomposer`: 大規模関数の分解ツール
- `pattern-intent`: パターンベースの分析ツール