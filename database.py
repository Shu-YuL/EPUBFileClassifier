# database.py
import sqlite3
from pathlib import Path

DB_FILE = "learning_history.db"

class Database:
    def __init__(self):
        # 連接資料庫，如果檔案不存在則會自動創建
        self.conn = sqlite3.connect(DB_FILE)
        self.setup_table()

    def setup_table(self):
        cursor = self.conn.cursor()
        # 創建表格，如果它不存在的話
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CustomDestinations (
                FileNameWithoutExtension TEXT PRIMARY KEY,
                ChosenPath TEXT NOT NULL,
                Weight INTEGER NOT NULL DEFAULT 1,
                LastModified TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def query_suggestion(self, filename_stem):
        cursor = self.conn.cursor()
        cursor.execute("SELECT ChosenPath FROM CustomDestinations WHERE FileNameWithoutExtension = ?", (filename_stem,))
        result = cursor.fetchone()
        # 如果查詢到結果，返回路徑；否則返回 None
        return result[0] if result else None

    def record_custom_choice(self, filename_stem, chosen_path):
        cursor = self.conn.cursor()
        # 使用 UPSERT: 如果 FileNameWithoutExtension 已存在，則更新 Weight；否則插入新紀錄
        cursor.execute("""
            INSERT INTO CustomDestinations (FileNameWithoutExtension, ChosenPath, LastModified)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(FileNameWithoutExtension) DO UPDATE SET
                ChosenPath = excluded.ChosenPath,
                Weight = Weight + 1,
                LastModified = excluded.LastModified;
        """, (filename_stem, str(chosen_path)))
        self.conn.commit()

    def close(self):
        self.conn.close()