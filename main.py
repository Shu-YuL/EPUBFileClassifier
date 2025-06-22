import shutil # 用於移動檔案
from database import Database
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLineEdit, QLabel, QTableWidget, QHeaderView, QFileDialog, QTableWidgetItem)
from PySide6.QtCore import Qt

from pathlib import Path

class FileClassifierApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB 文件分類助手")
        self.resize(800, 600)

        # 初始化資料庫
        self.db = Database()

        self.init_ui()

    def init_ui(self):
        # 建立一個垂直主佈局
        main_layout = QVBoxLayout(self)

        # --- 輸入區 ---
        # 建立一個水平佈局來放置標籤、輸入框和按鈕
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("未分類文件:"))
        self.source_path_edit = QLineEdit()
        self.source_path_edit.setReadOnly(True)
        source_layout.addWidget(self.source_path_edit)
        browse_source_btn = QPushButton("瀏覽...")
        # 連接按鈕的點擊事件到一個方法
        browse_source_btn.clicked.connect(self.browse_source_folder)
        source_layout.addWidget(browse_source_btn)
        # 將這個水平佈局加入到主佈局中
        main_layout.addLayout(source_layout)

        db_layout = QHBoxLayout()
        db_layout.addWidget(QLabel("數據庫:"))
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        db_layout.addWidget(self.db_path_edit)
        browse_db_btn = QPushButton("瀏覽...")
        browse_db_btn.clicked.connect(self.browse_db_folder)
        db_layout.addWidget(browse_db_btn)
        main_layout.addLayout(db_layout)

        # --- 操作區 ---
        scan_btn = QPushButton("開始掃描比對")
        scan_btn.clicked.connect(self.start_scan)
        main_layout.addWidget(scan_btn)

        # --- 結果展示區 ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["待分類文件", "建議目標位置", "操作"])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.results_table)

    def browse_source_folder(self):
        # 彈出資料夾選擇對話框
        folder_path = QFileDialog.getExistingDirectory(self, "選擇未分類文件夾")
        if folder_path:
            # 如果用戶選擇了資料夾，就更新輸入框的文字
            self.source_path_edit.setText(folder_path)

    def browse_db_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "選擇數據庫")
        if folder_path:
            self.db_path_edit.setText(folder_path)

    def start_scan(self):
        source_dir = self.source_path_edit.text()
        db_dir = self.db_path_edit.text()

        # 檢查路徑是否已選擇
        if not source_dir or not db_dir:
            # 這裡可以彈出一個警告對話框，暫時用 print 代替
            print("錯誤：請先選擇兩個資料夾！")
            return

        source_path = Path(source_dir)
        db_path = Path(db_dir)

        # 清空表格舊數據
        self.results_table.setRowCount(0)

        # 尋找所有 .epub 檔案
        epub_files = list(source_path.glob('*.epub'))

        for file in epub_files:
            # 取得不含副檔名的檔名
            filename_stem = file.stem

            # --- 學習功能整合 ---
            # 1. 先從資料庫查詢學習紀錄
            learned_path = self.db.query_suggestion(filename_stem)

            if learned_path:
                suggestion_text = f"[學習] {learned_path}"
            else:
                # 2. 如果沒有學習紀錄，採用預設規則
                suggested_dir = db_path / filename_stem
                if suggested_dir.is_dir():
                    suggestion_text = str(suggested_dir)  # 將 Path 物件轉為字串
                else:
                    # 在 db_path 下尋找名稱部分與 filename_stem 有部分重疊的資料夾
                    def partial_match(a, b, min_len=3):
                        # 只要有長度 >= min_len 的子字串同時出現在 a 和 b 就算匹配
                        for i in range(len(a) - min_len + 1):
                            sub = a[i:i+min_len]
                            if sub in b:
                                return True
                        for i in range(len(b) - min_len + 1):
                            sub = b[i:i+min_len]
                            if sub in a:
                                return True
                        return False

                    candidates = [
                        d for d in db_path.iterdir()
                        if d.is_dir() and partial_match(filename_stem, d.name)
                    ]
                    if candidates:
                        # 選擇名稱最短且最早匹配的資料夾
                        best_match = min(candidates, key=lambda d: (len(d.name), d.name))
                        suggestion_text = str(best_match)
                    else:
                        suggestion_text = "未找到匹配項"

            # 將結果添加到表格
            self.add_row_to_table(file, suggestion_text)

    def add_row_to_table(self, file_path, suggested_path):
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)

        # 第 0 欄：待分類文件
        self.results_table.setItem(row_position, 0, QTableWidgetItem(str(file_path)))
        # 第 1 欄：建議位置
        self.results_table.setItem(row_position, 1, QTableWidgetItem(suggested_path))

        # 第 2 欄：操作按鈕
        accept_btn = QPushButton("接受")
        customize_btn = QPushButton("自訂")

        # 這裡使用 lambda 來確保點擊事件能獲取正確的行號
        accept_btn.clicked.connect(lambda: self.accept_action(row_position))
        customize_btn.clicked.connect(lambda: self.customize_action(row_position))

        # 建立一個小容器來放置兩個按鈕
        button_layout = QHBoxLayout()
        button_layout.addWidget(accept_btn)
        button_layout.addWidget(customize_btn)
        button_layout.setContentsMargins(5, 0, 5, 0) # 調整邊距

        button_widget = QWidget()
        button_widget.setLayout(button_layout)

        # 將這個包含按鈕的 widget 放入表格中
        self.results_table.setCellWidget(row_position, 2, button_widget)

    def accept_action(self, row):
        # 取得該行的檔案路徑和建議路徑
        source_file_item = self.results_table.item(row, 0)
        suggested_path_item = self.results_table.item(row, 1)

        if not source_file_item or not suggested_path_item: return

        source_file = Path(source_file_item.text())
        # 去掉 "[學習] " 標記
        dest_dir_str = suggested_path_item.text().replace("[學習] ", "")
        dest_dir = Path(dest_dir_str)

        if dest_dir_str == "未找到匹配項" or not dest_dir.exists():
            print(f"錯誤：目標位置 '{dest_dir_str}' 無效！")
            return

        try:
            shutil.move(source_file, dest_dir / source_file.name)
            self.deactivate_row(row)
        except Exception as e:
            print(f"移動檔案失敗: {e}")

    def customize_action(self, row):
        source_file_item = self.results_table.item(row, 0)
        if not source_file_item: return
        source_file = Path(source_file_item.text())

        # 彈出對話框讓用戶選擇新的目標位置
        new_dest_dir = QFileDialog.getExistingDirectory(self, f"為 {source_file.name} 選擇自訂位置")

        if new_dest_dir:
            try:
                # 移動檔案
                shutil.move(source_file, Path(new_dest_dir) / source_file.name)
                # --- 寫入學習紀錄 ---
                self.db.record_custom_choice(source_file.stem, new_dest_dir)
                # 更新表格第二欄為新目標位置
                self.results_table.setItem(row, 1, QTableWidgetItem(str(new_dest_dir)))
                # 將按鈕設為 disabled 並反灰 row
                self.deactivate_row(row)
            except Exception as e:
                print(f"移動檔案或記錄時出錯: {e}")

    def deactivate_row(self, row):
        # 反灰 row
        for col in range(self.results_table.columnCount()):
            item = self.results_table.item(row, col)
            if item:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setBackground(Qt.lightGray)
        # 禁用按鈕
        cell_widget = self.results_table.cellWidget(row, 2)
        if cell_widget:
            for i in range(cell_widget.layout().count()):
                btn = cell_widget.layout().itemAt(i).widget()
                if btn:
                    btn.setDisabled(True)

    # 新增 closeEvent 以確保程式關閉時資料庫也關閉
    def closeEvent(self, event):
        self.db.close()
        event.accept()

# ... (if __name__ == '__main__': 部分保持不變)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FileClassifierApp()
    window.show()
    sys.exit(app.exec())