from paddlex import create_model
from utils import FileManager
import os


class FormulaRecognizer:
    def __init__(self):
        self.model = create_model(model_name="PP-FormulaNet-S")

    def recognize(self, image_path, timestamp):
        """识别图片中的公式"""
        try:
            output = self.model.predict(input=image_path, batch_size=1)
            for res in output:
                # 保存到带时间戳的文件
                result_file = f"{timestamp}_result.json"
                res.save_to_json(save_path=os.path.join("output", result_file))
                return res
            return None
        except Exception as e:
            print(f"识别出错: {str(e)}")
            return None
