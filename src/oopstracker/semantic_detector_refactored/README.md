# Semantic Detector Refactoring

## 概要

`semantic_detector_original.py`のリファクタリング結果です。以下のパターンを適用しました：

1. **Extract（抽出）** - 複雑なロジックを責務別のサービスクラスに分離
2. **Isolate（分離）** - 外部依存を各サービス内に隔離
3. **Layer（層化）** - 明確な層構造で責務を整理

## アーキテクチャ

```
semantic_detector_refactored/
├── core/                       # ドメイン層：コアビジネスロジック
│   ├── structural_detector_service.py  # 構造的重複検出
│   └── semantic_detector_service.py    # 意味的重複検出
├── integrations/              # インフラ層：外部統合
│   └── intent_tree_service.py         # Intent Tree統合
├── orchestrator/              # アプリケーション層：ワークフロー管理
│   └── duplicate_detection_orchestrator.py
└── semantic_aware_detector.py # プレゼンテーション層：APIファサード
```

## 主な改善点

### 1. 責務の分離

- **StructuralDetectorService**: 構造的重複検出に特化
- **SemanticDetectorService**: 意味的重複検出に特化
- **IntentTreeService**: Intent Tree統合、対話的探索、学習統計を管理
- **DuplicateDetectionOrchestrator**: 全体のワークフローを調整

### 2. 依存関係の明確化

```
API層 (SemanticAwareDuplicateDetector)
  ↓
アプリケーション層 (DuplicateDetectionOrchestrator)
  ↓
ドメイン層 (StructuralDetectorService, SemanticDetectorService)
  ↓
インフラ層 (IntentTreeService)
```

### 3. テスタビリティの向上

- 各サービスが独立してテスト可能
- モックしやすい設計
- 明確なインターフェース

### 4. 保守性の向上

- 単一責任の原則に従った設計
- 機能追加・変更の影響範囲が限定的
- コードの可読性向上

## 使用方法

リファクタリング後も既存のAPIとの互換性を維持：

```python
from oopstracker.semantic_detector_refactored import SemanticAwareDuplicateDetector

# 初期化
detector = SemanticAwareDuplicateDetector(
    intent_unified_available=True,
    enable_intent_tree=True
)

# 初期化処理
await detector.initialize()

# 重複検出
results = await detector.detect_duplicates(
    code_records=records,
    enable_semantic=True,
    semantic_threshold=0.7
)

# クリーンアップ
await detector.cleanup()
```

## 今後の拡張

- 新しい検出アルゴリズムの追加が容易
- 異なる統合サービスの追加が可能
- パフォーマンス最適化の余地あり