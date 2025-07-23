#!/usr/bin/env python3
"""
OOPStracker cleanup script - Remove unnecessary files and empty directories
Based on clean.sh but with enhanced empty directory removal
"""

import os
import shutil
from pathlib import Path
from typing import List

class CleanupManager:
    """プロジェクト清掃管理クラス"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(".")
        
    def run_cleanup(self):
        """メイン清掃処理"""
        print("🧹 OOPStracker Cleanup Script")
        print("=============================")
        
        # 各種清掃処理
        self.cleanup_pattern_dirs("__pycache__", "Python cache directories")
        self.cleanup_pattern_dirs("htmlcov", "test coverage HTML directories")
        self.cleanup_pattern_dirs(".pytest_cache", "pytest cache directories")
        self.cleanup_pattern_dirs("build", "build directories")
        self.cleanup_pattern_dirs("dist", "distribution directories")
        self.cleanup_pattern_dirs("*.egg-info", "egg info directories")
        self.cleanup_pattern_dirs(".mypy_cache", "mypy cache directories")
        self.cleanup_pattern_dirs(".ruff_cache", "ruff cache directories")
        
        # ファイル清掃
        self.cleanup_files("*.db", "database files")
        self.cleanup_files("coverage.xml", "coverage XML files")
        self.cleanup_files(".coverage", "coverage data files")
        self.cleanup_files("*.pyc", "Python compiled files")
        self.cleanup_files("*.pyo", "Python optimized files")
        
        # 空ディレクトリ清掃（main feature）
        self.cleanup_empty_directories()
        
        # サマリー
        print("")
        print("✨ Cleanup complete!")
        print("")
        print("Note: This script removes temporary and cache files,")
        print("      and empty directories. Source code is preserved.")
    
    def cleanup_pattern_dirs(self, pattern: str, description: str):
        """パターンマッチするディレクトリを削除"""
        print(f"🔍 Searching for {description}... ", end="")
        
        matching_dirs = list(self.project_root.rglob(pattern))
        matching_dirs = [d for d in matching_dirs if d.is_dir()]
        
        if matching_dirs:
            print(f"found {len(matching_dirs)}")
            print("   Removing...")
            
            for dir_path in matching_dirs:
                try:
                    shutil.rmtree(dir_path)
                except OSError as e:
                    print(f"   ⚠️  Failed to remove {dir_path}: {e}")
            
            print("   ✅ Cleaned!")
        else:
            print("none found ✅")
    
    def cleanup_files(self, pattern: str, description: str):
        """パターンマッチするファイルを削除"""
        print(f"🔍 Searching for {description}... ", end="")
        
        matching_files = list(self.project_root.rglob(pattern))
        matching_files = [f for f in matching_files if f.is_file()]
        
        if matching_files:
            print(f"found {len(matching_files)}")
            print("   Removing...")
            
            for file_path in matching_files:
                try:
                    file_path.unlink()
                except OSError as e:
                    print(f"   ⚠️  Failed to remove {file_path}: {e}")
            
            print("   ✅ Cleaned!")
        else:
            print("none found ✅")
    
    def cleanup_empty_directories(self):
        """空ディレクトリを再帰的に削除"""
        print("🔍 Searching for empty directories... ", end="")
        
        removed_count = 0
        max_iterations = 10  # 無限ループ防止
        
        for _ in range(max_iterations):
            empty_dirs = self._find_empty_directories()
            
            if not empty_dirs:
                break
            
            for dir_path in empty_dirs:
                try:
                    # .gitkeepファイルがある場合はスキップ
                    if (dir_path / ".gitkeep").exists():
                        continue
                    
                    # 隠しファイルのみの場合もチェック
                    if self._is_effectively_empty(dir_path):
                        dir_path.rmdir()
                        removed_count += 1
                except OSError:
                    # 削除できない場合はスキップ
                    continue
        
        if removed_count > 0:
            print(f"found and removed {removed_count}")
            print("   ✅ Empty directories cleaned!")
        else:
            print("none found ✅")
    
    def _find_empty_directories(self) -> List[Path]:
        """空ディレクトリを検索"""
        empty_dirs = []
        
        for root, _, _ in os.walk(self.project_root, topdown=False):
            root_path = Path(root)
            
            # .git, .venv, __pycache__ などはスキップ
            if any(skip in root_path.parts for skip in ['.git', '.venv', '__pycache__']):
                continue
            
            # プロジェクトルート自体はスキップ
            if root_path == self.project_root:
                continue
            
            if self._is_effectively_empty(root_path):
                empty_dirs.append(root_path)
        
        return empty_dirs
    
    def _is_effectively_empty(self, dir_path: Path) -> bool:
        """ディレクトリが実質的に空かどうかチェック"""
        try:
            contents = list(dir_path.iterdir())
            
            # 完全に空
            if not contents:
                return True
            
            # 隠しファイル（.DS_Store等）のみの場合
            visible_contents = [item for item in contents if not item.name.startswith('.')]
            if not visible_contents:
                # .gitkeep がある場合は保持
                if (dir_path / ".gitkeep").exists():
                    return False
                return True
            
            return False
        except PermissionError:
            return False
    
    def show_directory_stats(self):
        """ディレクトリ統計を表示"""
        print("\n📊 Directory Statistics:")
        
        total_dirs = 0
        empty_dirs = 0
        
        for root, dirs, _ in os.walk(self.project_root):
            total_dirs += len(dirs)
            
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                if self._is_effectively_empty(dir_path):
                    empty_dirs += 1
        
        print(f"   Total directories: {total_dirs}")
        print(f"   Empty directories: {empty_dirs}")
        if total_dirs > 0:
            print(f"   Empty ratio: {empty_dirs/total_dirs*100:.1f}%")

def main():
    """メイン関数"""
    # プロジェクトルートを自動検出
    current = Path(".")
    project_root = current
    
    # pyproject.tomlまたは.gitがある場所をプロジェクトルートとする
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            project_root = parent
            break
    
    print(f"🎯 Project root: {project_root.absolute()}")
    
    # 清掃実行
    cleaner = CleanupManager(project_root)
    cleaner.run_cleanup()
    
    # 統計表示
    cleaner.show_directory_stats()

if __name__ == "__main__":
    main()