# OOPSTracker サーバー化設計

## アーキテクチャ案

### 1. FastAPI + 永続メモリキャッシュ
```python
from fastapi import FastAPI
import uvicorn

class OOPSTrackerServer:
    def __init__(self):
        self.detector = ASTSimHashDetector()
        self.startup_time = None
    
    async def startup_event(self):
        start = time.time()
        await self.detector.load_all_data()  # 全データ読み込み
        self.startup_time = time.time() - start
        print(f"🚀 Server ready in {self.startup_time:.2f}s")

app = FastAPI()
tracker = OOPSTrackerServer()

@app.on_event("startup")
async def startup():
    await tracker.startup_event()

@app.post("/scan")
async def scan_code(code: str, file_path: str = None):
    return tracker.detector.register_code(code, file_path=file_path)

@app.post("/check")
async def check_duplicate(code: str):
    return tracker.detector.find_similar(code)

@app.get("/list")
async def list_records():
    return tracker.detector.get_all_records()
```

### 2. CLIクライアント
```python
# cli.py の変更
import httpx

class ServerClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client()
    
    def scan_file(self, file_path):
        with open(file_path) as f:
            code = f.read()
        response = self.client.post(f"{self.base_url}/scan", 
                                   json={"code": code, "file_path": file_path})
        return response.json()

# CLIコマンド実装
def main():
    try:
        client = ServerClient()
        # サーバーが動いていればクライアントモード
        client.health_check()
        return run_client_mode(client, args)
    except:
        # サーバーが動いていなければ直接モード
        return run_direct_mode(args)
```

## 性能予測

### 起動時間（データ量別）
- **1K関数**: 0.5-1秒
- **10K関数**: 5-15秒
- **100K関数**: 1-3分

### メモリ使用量
```python
# 概算（関数あたり）
memory_per_function = {
    "CodeRecord": "~1KB",
    "CodeUnit": "~2KB", 
    "BK-tree node": "~0.5KB",
    "Total": "~3.5KB per function"
}

# 総メモリ使用量
total_memory = {
    "1K関数": "3.5MB",
    "10K関数": "35MB", 
    "100K関数": "350MB"
}
```

### レスポンス時間
```python
# サーバーモード（メモリキャッシュ済み）
response_times = {
    "check": "10-50ms",
    "register": "20-100ms", 
    "scan_file": "100ms-1s",
    "list": "10-100ms"
}

# 直接モード（起動コスト含む）
direct_mode_times = {
    "check": "起動時間 + 10ms",
    "register": "起動時間 + 20ms",
    "scan_file": "起動時間 + 100ms",
    "list": "起動時間 + 10ms"
}
```

## 実装優先度

### Phase 1: ハイブリッド実装
```bash
# サーバーが起動していればクライアント、なければ直接実行
uv run oopstracker scan file.py  # 自動判定

# サーバー明示起動
uv run oopstracker serve --port 8000

# クライアント強制
uv run oopstracker --server-mode scan file.py
```

### Phase 2: 自動起動
```python
# 初回実行時にバックグラウンドサーバー自動起動
def auto_start_server():
    if not server_running():
        subprocess.Popen(["uv", "run", "oopstracker", "serve", "--daemon"])
        wait_for_server_ready()
```

### Phase 3: 最適化
```python
# 差分更新
def incremental_update(file_path):
    old_hash = get_file_hash(file_path)
    new_hash = calculate_file_hash(file_path)
    if old_hash != new_hash:
        update_file_records(file_path)

# 部分読み込み
def lazy_loading(query):
    # クエリに関連するデータのみ読み込み
    relevant_data = db.query_similar_structures(query)
```

## 推奨アプローチ

1. **短期**: 永続化のみ実装（起動時間受容）
2. **中期**: ハイブリッド方式（サーバー化オプション）
3. **長期**: 自動最適化（使用パターンに応じて切り替え）

**判断基準**:
- データ量 < 1K関数 → 直接モード
- データ量 > 1K関数 → サーバーモード推奨
- 頻繁な使用 → サーバーモード
- たまの使用 → 直接モード

どのアプローチを取りたいですか？