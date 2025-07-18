# LLM Setup Guide for OOPStracker

OOPStrackerの意味的解析機能を使用するには、LLMサービスが必要です。

## 推奨: Ollama を使用する方法

### 1. Ollamaのインストール

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# または手動でダウンロード
# https://ollama.com/download
```

### 2. Ollamaサービスの起動

```bash
# バックグラウンドで起動（自動起動済みの場合は不要）
ollama serve
```

### 3. モデルのダウンロード

```bash
# 軽量モデル（推奨）
ollama pull llama2

# より高精度なモデル
ollama pull codellama
ollama pull mistral
```

### 4. 動作確認

```bash
# Ollamaが動作しているか確認
curl http://localhost:11434

# OOPStrackerで確認
uv run oopstracker check --limit 1
```

## 環境変数による設定

カスタムLLMサービスを使用する場合：

```bash
# LLMエンドポイントの設定
export OOPSTRACKER_LLM_URL="http://your-llm-service:8000/v1/chat/completions"
export OOPSTRACKER_LLM_MODEL="your-model-name"

# 例: ローカルのOpenAI互換サービス
export OOPSTRACKER_LLM_URL="http://localhost:8000/v1/chat/completions"
export OOPSTRACKER_LLM_MODEL="gpt-3.5-turbo"
```

## サポートされるLLMサービス

### 1. Ollama（推奨）
- **エンドポイント**: `http://localhost:11434/api/chat`
- **モデル**: llama2, codellama, mistral など
- **特徴**: ローカル実行、無料、簡単セットアップ

### 2. OpenAI API互換サービス
- **エンドポイント**: `http://localhost:8000/v1/chat/completions`
- **モデル**: サービスによる
- **特徴**: 標準的なAPI形式

### 3. カスタムLLMサービス
- 環境変数で任意のエンドポイントを指定可能

## トラブルシューティング

### LLMが見つからない場合

```bash
# エラーメッセージ例
⚠️  Failed to initialize semantic analysis: No LLM service available
🔄 Falling back to structural analysis only
```

**解決方法**：

1. Ollamaがインストールされているか確認
   ```bash
   ollama --version
   ```

2. Ollamaサービスが起動しているか確認
   ```bash
   curl http://localhost:11434
   ```

3. モデルがダウンロードされているか確認
   ```bash
   ollama list
   ```

### 構造解析のみで使用する

LLMが利用できない場合でも、構造解析は利用可能です：

```bash
# LLMを無効化して実行
uv run oopstracker check --no-semantic
```

## パフォーマンスの最適化

### 1. 軽量モデルの使用
```bash
# 高速だが精度は低め
ollama pull tinyllama

export OOPSTRACKER_LLM_MODEL="tinyllama"
```

### 2. 並列度の調整
```bash
# 同時実行数を増やす（デフォルト: 3）
uv run oopstracker --max-semantic-concurrent 5 check
```

### 3. タイムアウトの調整
```bash
# タイムアウトを短くする（デフォルト: 30秒）
uv run oopstracker --semantic-timeout 10 check
```

## 自動検出の仕組み

OOPStrackerは以下の順序でLLMサービスを検出します：

1. 環境変数 `OOPSTRACKER_LLM_URL`
2. 環境変数 `LLM_API_URL`
3. Ollama デフォルト (`http://localhost:11434/api/chat`)
4. OpenAI互換 (`http://localhost:8000/v1/chat/completions`)
5. ハードコードされた開発環境

いずれも見つからない場合は、構造解析のみで動作します。