import os
import json
from datetime import datetime
from PyQt6.QtGui import QPixmap, QClipboard
from PyQt6.QtWidgets import QApplication


class FileManager:
    @staticmethod
    def ensure_output_dir():
        """确保输出目录存在"""
        if not os.path.exists("output"):
            os.makedirs("output")

    @staticmethod
    def get_timestamp():
        """获取当前时间戳"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def load_result(timestamp):
        """加载指定时间戳的结果"""
        result_file = f"{timestamp}_result.json"
        image_file = f"{timestamp}_image.png"

        result = None
        image = None

        try:
            with open(os.path.join("output", result_file), "r", encoding="utf-8") as f:
                result = json.load(f)

            if os.path.exists(os.path.join("output", image_file)):
                image = QPixmap(os.path.join("output", image_file))
        except Exception as e:
            print(f"加载结果出错: {str(e)}")

        return result, image


class ClipboardManager:
    @staticmethod
    def get_image_from_clipboard():
        """从剪贴板获取图片"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            return QPixmap(clipboard.pixmap())
        return None
