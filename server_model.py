import requests
import logging
import json
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ServerModelManager:
    """服务器模型管理器"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.is_connected = False
        self.test_connection()

    def test_connection(self) -> bool:
        """测试服务器连接"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                self.is_connected = True
                logger.info("服务器模型连接成功")
                return True
        except Exception as e:
            logger.warning(f"服务器模型连接失败: {e}")
            self.is_connected = False
        return False

    def get_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """从服务器获取文本嵌入"""
        if not self.is_connected:
            return None

        try:
            payload = {
                "texts": texts,
                "model_type": "bert",
                "max_length": 512
            }

            response = requests.post(
                f"{self.server_url}/embeddings",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                embeddings = np.array(result["embeddings"])
                return embeddings
            else:
                logger.error(f"服务器返回错误: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"获取服务器嵌入失败: {e}")
            self.is_connected = False
            return None

    def generate_codes_with_ai(self, text: str, model_type: str = "gpt") -> Dict[str, Any]:
        """使用AI模型生成编码"""
        if not self.is_connected:
            return {"error": "服务器连接失败"}

        try:
            payload = {
                "text": text,
                "model_type": model_type,
                "task": "grounded_theory_coding"
            }

            response = requests.post(
                f"{self.server_url}/generate_codes",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"服务器错误: {response.status_code}"}

        except Exception as e:
            logger.error(f"AI生成编码失败: {e}")
            return {"error": str(e)}

    def get_available_models(self) -> List[str]:
        """获取可用的服务器模型"""
        try:
            response = requests.get(f"{self.server_url}/models", timeout=10)
            if response.status_code == 200:
                return response.json().get("models", [])
            else:
                return []
        except:
            return []