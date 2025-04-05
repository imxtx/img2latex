import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QTextEdit,
    QListWidget,
    QSplitter,
    QSizePolicy,
    QMenu,
    QMessageBox,
    QInputDialog,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QUrl, QRegularExpression
from PyQt6.QtGui import (
    QPixmap,
    QClipboard,
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
import os
import json
import re
import platform

from utils import FileManager, ClipboardManager
from model import FormulaRecognizer
from history import HistoryManager


class LatexHighlighter(QSyntaxHighlighter):
    """LaTeX 语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # 命令格式
        command_format = QTextCharFormat()
        command_format.setForeground(QColor("#0000FF"))  # 深蓝色
        command_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append(
            (QRegularExpression(r"\\[a-zA-Z]+"), command_format)
        )

        # 数学符号格式
        math_symbol_format = QTextCharFormat()
        math_symbol_format.setForeground(QColor("#000000"))  # 黑色
        self.highlighting_rules.append(
            (QRegularExpression(r"[{}]"), math_symbol_format)
        )

        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))  # 深绿色
        self.highlighting_rules.append((QRegularExpression(r"%.*"), comment_format))

        # 数字格式
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#000000"))  # 黑色
        self.highlighting_rules.append((QRegularExpression(r"\b\d+\b"), number_format))

    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)


class MathFormulaConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Math Formula to LaTeX")
        self.setGeometry(100, 100, 1400, 900)

        # 初始化工具类
        FileManager.ensure_output_dir()
        self.recognizer = FormulaRecognizer()

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()

        # 创建左侧历史记录列表
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # 添加历史记录标题和按钮
        history_header = QHBoxLayout()
        history_header.addWidget(QLabel("History:"))
        clear_history_btn = QPushButton("Clear All")
        clear_history_btn.clicked.connect(self.clear_history)
        history_header.addWidget(clear_history_btn)
        history_header.addStretch()
        left_layout.addLayout(history_header)

        self.history_list = QListWidget()
        self.history_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )  # 允许多选
        self.history_list.itemClicked.connect(self.show_history_item)
        self.history_list.itemDoubleClicked.connect(
            self.rename_history_item
        )  # 添加双击事件
        self.history_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )  # 启用右键菜单
        self.history_list.customContextMenuRequested.connect(
            self.show_history_context_menu
        )
        left_layout.addWidget(self.history_list)
        left_widget.setLayout(left_layout)

        # 创建右侧主显示区域
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # 创建图片显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 400)  # 设置最小尺寸
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )  # 允许扩展
        self.image_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f0f0;
                border: none;
                border-radius: 4px;
                padding: 0;
                margin: 0;
            }
        """
        )

        # 创建图片容器，用于居中显示
        self.image_container = QWidget()
        image_container_layout = QVBoxLayout()  # 改为垂直布局
        image_container_layout.addStretch()

        # 添加选择图片按钮
        select_image_btn = QPushButton("Select Image")
        select_image_btn.clicked.connect(self.select_image)
        select_image_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        )
        image_container_layout.addWidget(
            select_image_btn, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # 添加图片标签
        image_label_layout = QHBoxLayout()
        image_label_layout.addStretch()
        image_label_layout.addWidget(self.image_label)
        image_label_layout.addStretch()
        image_container_layout.addLayout(image_label_layout)

        image_container_layout.addStretch()
        self.image_container.setLayout(image_container_layout)
        self.image_container.setMinimumHeight(400)  # 设置容器最小高度

        right_layout.addWidget(self.image_container)

        # 创建LaTeX编辑和渲染区域
        latex_layout = QHBoxLayout()

        # LaTeX编辑区域
        latex_edit_widget = QWidget()
        latex_edit_layout = QVBoxLayout()
        self.latex_text = QTextEdit()
        self.latex_text.setReadOnly(False)  # 允许编辑
        self.latex_text.textChanged.connect(self.on_latex_changed)

        # 设置等宽字体
        font = QFont("Courier New", 12)
        self.latex_text.setFont(font)

        # 添加语法高亮
        self.highlighter = LatexHighlighter(self.latex_text.document())

        # 添加快捷键提示
        system = platform.system().lower()
        if system == "darwin":
            shortcut_text = "Use Command+V to paste image or text"
        else:
            shortcut_text = "Use Ctrl+V to paste image or text"
        shortcut_label = QLabel(shortcut_text)
        shortcut_label.setStyleSheet("color: gray; font-style: italic;")

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(shortcut_label)

        latex_edit_layout.addWidget(QLabel("LaTeX Code:"))
        latex_edit_layout.addWidget(self.latex_text)
        latex_edit_layout.addLayout(button_layout)
        latex_edit_widget.setLayout(latex_edit_layout)

        # LaTeX渲染区域
        latex_render_widget = QWidget()
        latex_render_layout = QVBoxLayout()
        self.web_view = QWebEngineView()
        latex_render_layout.addWidget(QLabel("Formula Preview:"))
        latex_render_layout.addWidget(self.web_view)
        latex_render_widget.setLayout(latex_render_layout)

        latex_layout.addWidget(latex_edit_widget)
        latex_layout.addWidget(latex_render_widget)
        right_layout.addLayout(latex_layout)

        right_widget.setLayout(right_layout)

        # 使用QSplitter分割左右区域
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        main_layout.addWidget(self.splitter)

        main_widget.setLayout(main_layout)

        # 初始化历史记录管理器
        self.history_manager = HistoryManager(self.history_list)
        self.history_manager.load_history()

        # 记录当前正在编辑的文件时间戳
        self.current_timestamp = None

        # 初始化 KaTeX 渲染
        self.init_mathjax()

        # 重写文本框的粘贴事件
        self.latex_text.keyPressEvent = self.text_edit_key_press_event

        # 保存当前显示的图片
        self.current_pixmap = None

    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        if self.current_pixmap and not self.current_pixmap.isNull():
            # 重新缩放当前图片
            scaled_pixmap = self.scale_image(self.current_pixmap)
            if scaled_pixmap and not scaled_pixmap.isNull():
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def text_edit_key_press_event(self, event):
        """处理文本框的按键事件"""
        # 获取当前操作系统
        system = platform.system().lower()

        # 检查是否是粘贴快捷键
        if (
            system == "darwin"
            and event.key() == Qt.Key.Key_V
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.handle_paste()
            return
        elif (
            system != "darwin"
            and event.key() == Qt.Key.Key_V
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.handle_paste()
            return

        # 如果不是粘贴快捷键，调用原始的按键事件处理
        QTextEdit.keyPressEvent(self.latex_text, event)

    def init_mathjax(self):
        """初始化 KaTeX 渲染环境"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css" integrity="sha384-zh0CIslj+VczCZtlzBcjt5ppRcsAmDnRem7ESsYwWwg3m/OaJ2l4x7YBZl9Kxxib" crossorigin="anonymous">
            <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.js" integrity="sha384-Rma6DA2IPUwhNxmrB/7S3Tno0YY7sFu9WSYMCuulLhIqYSGZ2gKCJWIqhBWqMQfh" crossorigin="anonymous"></script>
            <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/contrib/auto-render.min.js" integrity="sha384-hCXGrW6PitJEwbkoStFjeJxv+fSOOQKOPbJxSfM6G5sWZjAyWhXiTIIAmQqnlLlh" crossorigin="anonymous"></script>
            <style>
                body { margin: 0; padding: 20px; }
                #formula { font-size: 24px; text-align: center; }
            </style>
            <script>
                document.addEventListener("DOMContentLoaded", function() {
                    renderMathInElement(document.body, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\(', right: '\\)', display: false},
                            {left: '\\[', right: '\\]', display: true}
                        ],
                        throwOnError: false
                    });
                });
            </script>
        </head>
        <body>
            <div id="formula"></div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)

    def on_latex_changed(self):
        """处理 LaTeX 代码变化"""
        # 更新公式预览
        self.update_formula_preview()

        # 如果当前有正在编辑的文件，则保存修改
        if self.current_timestamp:
            self.save_current_edit()

    def save_current_edit(self):
        """保存当前的编辑内容"""
        try:
            # 读取原始结果文件
            result_file = os.path.join(
                "output", f"{self.current_timestamp}_result.json"
            )
            if os.path.exists(result_file):
                with open(result_file, "r", encoding="utf-8") as f:
                    result = json.load(f)

                # 更新 LaTeX 代码
                result["rec_formula"] = self.latex_text.toPlainText()

                # 保存更新后的结果
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存编辑内容时出错: {str(e)}")

    def update_formula_preview(self):
        """更新公式预览"""
        latex_code = self.latex_text.toPlainText()
        try:
            if latex_code:
                # 转义反斜杠
                latex_code = latex_code.replace("\\", "\\\\")
                # 使用 KaTeX 渲染公式
                js_code = f"""
                document.getElementById('formula').innerHTML = '$${latex_code}$$';
                renderMathInElement(document.getElementById('formula'), {{
                    delimiters: [
                        {{left: '$$', right: '$$', display: true}},
                        {{left: '$', right: '$', display: false}},
                        {{left: '\\\\(', right: '\\\\)', display: false}},
                        {{left: '\\\\[', right: '\\\\]', display: true}}
                    ],
                    throwOnError: false
                }});
                """
            else:
                # 如果没有输入，显示提示信息
                js_code = """
                document.getElementById('formula').innerHTML = '<span style="color: gray;">请输入 LaTeX 公式</span>';
                """
            self.web_view.page().runJavaScript(js_code)
        except Exception as e:
            # 在渲染区域显示错误信息
            error_msg = f"渲染错误:\n{str(e)}"
            js_code = f"""
            document.getElementById('formula').innerHTML = '<span style="color: red;">{error_msg}</span>';
            """
            self.web_view.page().runJavaScript(js_code)

    def on_clipboard_changed(self):
        """处理剪贴板变化"""
        # 获取剪贴板
        mime_data = self.clipboard.mimeData()

        # 检查剪贴板中的图片
        if mime_data.hasImage():
            pixmap = self.clipboard.pixmap()
            if not pixmap.isNull():
                # 显示图片
                scaled_pixmap = self.scale_image(pixmap)
                self.image_label.setPixmap(scaled_pixmap)

                # 生成时间戳
                timestamp = FileManager.get_timestamp()
                self.current_timestamp = timestamp

                # 保存原始图片
                image_file = f"{timestamp}_image.png"
                pixmap.save(os.path.join("output", image_file))

                # 保存临时图片文件用于识别
                temp_image_path = os.path.join("output", f"{timestamp}_temp.png")
                pixmap.save(temp_image_path)

                try:
                    # 进行公式识别
                    result = self.recognizer.recognize(temp_image_path, timestamp)
                    if result:
                        # 显示LaTeX代码
                        self.latex_text.setText(result["rec_formula"])
                        # 更新公式预览
                        self.update_formula_preview()
                        # 更新历史记录
                        self.history_manager.load_history()

                    # 删除临时文件
                    os.remove(temp_image_path)
                except Exception as e:
                    self.latex_text.setText(f"Recognition Error: {str(e)}")
                    self.update_formula_preview()

    def scale_image(self, pixmap):
        """缩放图片到合适的大小"""
        # 获取原始尺寸
        width = pixmap.width()
        height = pixmap.height()

        # 获取容器的可用尺寸
        container_width = self.image_container.width() - 20  # 减去内边距
        container_height = self.image_container.height() - 20

        # 如果图片尺寸小于容器尺寸，不进行缩放
        if width <= container_width and height <= container_height:
            return pixmap

        # 计算宽度和高度的缩放比例
        width_ratio = container_width / width
        height_ratio = container_height / height

        # 使用较小的比例确保图片完整显示
        scale_ratio = min(width_ratio, height_ratio)

        # 计算新尺寸
        new_width = int(width * scale_ratio)
        new_height = int(height * scale_ratio)

        # 进行缩放，保持宽高比
        return pixmap.scaled(
            new_width,
            new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def show_history_item(self, item):
        """显示选中的历史记录"""
        timestamp = self.history_manager.get_selected_item_info(item)
        result, image = FileManager.load_result(timestamp)

        if result:
            self.current_timestamp = timestamp  # 记录当前正在编辑的文件时间戳
            self.latex_text.setText(result["rec_formula"])
            if image and not image.isNull():
                # 保存当前图片
                self.current_pixmap = image.copy()  # 创建图片的副本
                # 缩放图片
                scaled_image = self.scale_image(self.current_pixmap)
                if scaled_image and not scaled_image.isNull():
                    self.image_label.setPixmap(scaled_image)
                    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 更新公式预览
            self.update_formula_preview()

    def process_image(self, pixmap):
        """处理图片并显示结果"""
        if pixmap and not pixmap.isNull():
            # 保存当前图片
            self.current_pixmap = pixmap.copy()  # 创建图片的副本
            # 缩放图片
            scaled_pixmap = self.scale_image(self.current_pixmap)
            if scaled_pixmap and not scaled_pixmap.isNull():
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 生成时间戳
            timestamp = FileManager.get_timestamp()
            self.current_timestamp = timestamp  # 记录当前正在编辑的文件时间戳

            # 保存原始图片
            image_file = f"{timestamp}_image.png"
            pixmap.save(os.path.join("output", image_file))

            # 保存临时图片文件用于识别
            temp_image_path = os.path.join("output", f"{timestamp}_temp.png")
            pixmap.save(temp_image_path)

            try:
                # 进行公式识别
                result = self.recognizer.recognize(temp_image_path, timestamp)
                if result:
                    # 添加标题
                    result["title"] = f"Formula {timestamp}"

                    # 显示LaTeX代码
                    self.latex_text.setText(result["rec_formula"])
                    # 更新公式预览
                    self.update_formula_preview()
                    # 更新历史记录
                    self.history_manager.load_history()

                # 删除临时文件
                os.remove(temp_image_path)
            except Exception as e:
                self.latex_text.setText(f"Recognition Error: {str(e)}")
                # 更新公式预览以显示错误信息
                self.update_formula_preview()

    def select_image(self):
        """选择图片文件"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                self.process_image(pixmap)
            else:
                QMessageBox.warning(self, "Error", "Failed to load image")

    def show_history_context_menu(self, position):
        """显示历史记录右键菜单"""
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        rename_action.triggered.connect(
            lambda: self.rename_history_item(self.history_list.itemAt(position))
        )
        delete_action.triggered.connect(self.delete_selected_history)
        menu.exec(self.history_list.mapToGlobal(position))

    def rename_history_item(self, item):
        """重命名历史记录项"""
        if not item:
            return

        # 获取当前名称
        current_name = item.text()

        # 创建输入对话框
        new_name, ok = QInputDialog.getText(
            self,
            "Rename History Item",
            "Enter new name:",
            QLineEdit.EchoMode.Normal,
            current_name,
        )

        if ok and new_name and new_name != current_name:
            # 获取时间戳
            timestamp = self.history_manager.get_selected_item_info(item)
            if timestamp:
                # 更新JSON文件
                result_file = os.path.join("output", f"{timestamp}_result.json")
                if os.path.exists(result_file):
                    try:
                        with open(result_file, "r", encoding="utf-8") as f:
                            result = json.load(f)

                        # 更新标题
                        result["title"] = new_name

                        with open(result_file, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=4)

                        # 更新列表显示
                        item.setText(new_name)
                    except Exception as e:
                        QMessageBox.warning(
                            self, "Error", f"Failed to rename: {str(e)}"
                        )

    def delete_selected_history(self):
        """删除选中的历史记录"""
        selected_items = self.history_list.selectedItems()
        if not selected_items:
            return

        # 获取选中的时间戳
        timestamps = []
        for item in selected_items:
            timestamp = self.history_manager.get_selected_item_info(item)
            if timestamp:
                timestamps.append(timestamp)

        # 删除文件
        for timestamp in timestamps:
            # 删除图片文件
            image_file = os.path.join("output", f"{timestamp}_image.png")
            if os.path.exists(image_file):
                os.remove(image_file)

            # 删除结果文件
            result_file = os.path.join("output", f"{timestamp}_result.json")
            if os.path.exists(result_file):
                os.remove(result_file)

        # 重新加载历史记录
        self.history_manager.load_history()

        # 如果删除的是当前正在编辑的记录，清空当前编辑
        if self.current_timestamp in timestamps:
            self.current_timestamp = None
            self.latex_text.clear()
            self.image_label.clear()
            self.update_formula_preview()

    def clear_history(self):
        """清空所有历史记录"""
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Are you sure you want to clear all history? This action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 获取所有历史记录
            items = [
                self.history_list.item(i) for i in range(self.history_list.count())
            ]
            timestamps = []
            for item in items:
                timestamp = self.history_manager.get_selected_item_info(item)
                if timestamp:
                    timestamps.append(timestamp)

            # 删除所有文件
            for timestamp in timestamps:
                # 删除图片文件
                image_file = os.path.join("output", f"{timestamp}_image.png")
                if os.path.exists(image_file):
                    os.remove(image_file)

                # 删除结果文件
                result_file = os.path.join("output", f"{timestamp}_result.json")
                if os.path.exists(result_file):
                    os.remove(result_file)

            # 清空当前编辑
            self.current_timestamp = None
            self.latex_text.clear()
            self.image_label.clear()
            self.update_formula_preview()

            # 重新加载历史记录
            self.history_manager.load_history()

    def setup_shortcuts(self):
        """设置快捷键"""
        # 获取当前操作系统
        system = platform.system().lower()

        # 设置粘贴快捷键
        if system == "darwin":  # macOS
            self.paste_shortcut = QShortcut(QKeySequence("Meta+V"), self)
        else:  # Windows 和 Linux
            self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)

        # 设置快捷键上下文为全局
        self.paste_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.paste_shortcut.activated.connect(self.handle_paste)

    def handle_paste(self):
        """处理粘贴操作"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                self.process_image(pixmap)
        elif mime_data.hasText():
            text = clipboard.text()
            if text:
                self.latex_text.insertPlainText(text)
                self.update_formula_preview()
        else:
            self.show_paste_prompt()

    def show_paste_prompt(self):
        """显示粘贴提示"""
        system = platform.system().lower()
        if system == "darwin":
            self.latex_text.setText(
                "No content in clipboard. Use Command+V to paste image or text"
            )
        else:
            self.latex_text.setText(
                "No content in clipboard. Use Ctrl+V to paste image or text"
            )
        self.update_formula_preview()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MathFormulaConverter()
    window.show()
    sys.exit(app.exec())
