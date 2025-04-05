import os
import json
from PyQt6.QtWidgets import QListWidget


class HistoryManager:
    def __init__(self, list_widget):
        self.list_widget = list_widget

    def load_history(self):
        """加载历史记录"""
        self.list_widget.clear()
        if os.path.exists("output"):
            # 获取所有结果文件并按时间戳排序
            files = [f for f in os.listdir("output") if f.endswith("_result.json")]
            # 提取时间戳并排序
            files.sort(key=lambda x: x.split("_result.json")[0], reverse=True)

            for file in files:
                try:
                    with open(os.path.join("output", file), "r", encoding="utf-8") as f:
                        result = json.load(f)
                        timestamp = file.split("_result.json")[0]
                        # 如果有标题就显示标题，否则显示时间戳
                        display_text = result.get("title", timestamp)
                        self.list_widget.addItem(display_text)
                except:
                    continue

    def get_selected_item_info(self, item):
        """获取选中项的信息"""
        if not item:
            return None

        # 获取文件名
        files = [f for f in os.listdir("output") if f.endswith("_result.json")]
        for file in files:
            try:
                with open(os.path.join("output", file), "r", encoding="utf-8") as f:
                    result = json.load(f)
                    timestamp = file.split("_result.json")[0]
                    # 如果标题匹配，或者没有标题且时间戳匹配
                    if result.get("title") == item.text() or (
                        not result.get("title") and timestamp == item.text()
                    ):
                        return timestamp
            except:
                continue
        return None
