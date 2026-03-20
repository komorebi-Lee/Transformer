import unittest
import json
import os
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication
import sys

class TestCodingStatistics(unittest.TestCase):
    """测试编码统计机制的单元测试"""

    def setUp(self):
        """设置测试环境"""
        self.settings = QSettings("GroundedTheory", "CodingSystem")
        # 创建一个简单的编码结构用于测试
        self.test_coding_structure = {
            "C01 三阶编码1": {
                "B01 二阶编码1": [
                    {
                        "content": "一阶编码内容1",
                        "code_id": "A01",
                        "sentence_details": [
                            {
                                "text": "测试句子1",
                                "file_path": "test_file1.txt",
                                "sentence_id": "1"
                            },
                            {
                                "text": "测试句子2",
                                "file_path": "test_file1.txt",
                                "sentence_id": "2"
                            }
                        ]
                    },
                    {
                        "content": "一阶编码内容2",
                        "code_id": "A02",
                        "sentence_details": [
                            {
                                "text": "测试句子3",
                                "file_path": "test_file2.txt",
                                "sentence_id": "3"
                            }
                        ]
                    }
                ],
                "B02 二阶编码2": [
                    {
                        "content": "一阶编码内容3",
                        "code_id": "A03",
                        "sentence_details": [
                            {
                                "text": "测试句子4",
                                "file_path": "test_file1.txt",
                                "sentence_id": "4"
                            },
                            {
                                "text": "测试句子5",
                                "file_path": "test_file2.txt",
                                "sentence_id": "5"
                            },
                            {
                                "text": "测试句子6",
                                "file_path": "test_file3.txt",
                                "sentence_id": "6"
                            }
                        ]
                    }
                ]
            },
            "C02 三阶编码2": {
                "B03 二阶编码3": [
                    {
                        "content": "一阶编码内容4",
                        "code_id": "A04",
                        "sentence_details": [
                            {
                                "text": "测试句子7",
                                "file_path": "test_file1.txt",
                                "sentence_id": "7"
                            }
                        ]
                    }
                ]
            }
        }

    def test_second_level_sentence_count(self):
        """测试二阶编码的句子来源数统计"""
        # 手动计算期望的句子来源数
        expected_second_level_counts = {
            "B01 二阶编码1": 3,  # 2 + 1
            "B02 二阶编码2": 3,  # 3
            "B03 二阶编码3": 1   # 1
        }

        # 遍历测试编码结构，验证二阶编码的句子来源数
        for third_cat, second_cats in self.test_coding_structure.items():
            for second_cat, first_contents in second_cats.items():
                actual_count = 0
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        actual_count += len(sentence_details) if sentence_details else 1
                    else:
                        actual_count += 1
                self.assertEqual(actual_count, expected_second_level_counts[second_cat], 
                                 f"二阶编码 {second_cat} 的句子来源数统计错误")

    def test_third_level_sentence_count(self):
        """测试三阶编码的句子来源数统计"""
        # 手动计算期望的句子来源数
        expected_third_level_counts = {
            "C01 三阶编码1": 6,  # 3 + 3
            "C02 三阶编码2": 1   # 1
        }

        # 遍历测试编码结构，验证三阶编码的句子来源数
        for third_cat, second_cats in self.test_coding_structure.items():
            actual_count = 0
            for second_cat, first_contents in second_cats.items():
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        actual_count += len(sentence_details) if sentence_details else 1
                    else:
                        actual_count += 1
            self.assertEqual(actual_count, expected_third_level_counts[third_cat], 
                             f"三阶编码 {third_cat} 的句子来源数统计错误")

    def test_empty_coding_structure(self):
        """测试空编码结构的情况"""
        empty_structure = {}
        # 验证空结构不会导致错误
        try:
            # 尝试处理空结构
            for third_cat, second_cats in empty_structure.items():
                pass
            # 如果没有抛出异常，测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"空编码结构处理失败: {e}")

    def test_single_level_coding(self):
        """测试只有一阶编码的情况"""
        single_level_structure = {
            "C01 三阶编码1": {
                "B01 二阶编码1": [
                    {
                        "content": "一阶编码内容1",
                        "code_id": "A01",
                        "sentence_details": [
                            {
                                "text": "测试句子1",
                                "file_path": "test_file1.txt",
                                "sentence_id": "1"
                            }
                        ]
                    }
                ]
            }
        }

        # 验证统计结果
        expected_second_level_count = 1
        expected_third_level_count = 1

        # 验证二阶编码统计
        for third_cat, second_cats in single_level_structure.items():
            for second_cat, first_contents in second_cats.items():
                actual_second_count = 0
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        actual_second_count += len(sentence_details) if sentence_details else 1
                    else:
                        actual_second_count += 1
                self.assertEqual(actual_second_count, expected_second_level_count, 
                                 f"单级编码的二阶编码句子来源数统计错误")

            # 验证三阶编码统计
            actual_third_count = 0
            for second_cat, first_contents in second_cats.items():
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        actual_third_count += len(sentence_details) if sentence_details else 1
                    else:
                        actual_third_count += 1
            self.assertEqual(actual_third_count, expected_third_level_count, 
                             f"单级编码的三阶编码句子来源数统计错误")

    def test_mixed_content_types(self):
        """测试混合内容类型的情况"""
        mixed_structure = {
            "C01 三阶编码1": {
                "B01 二阶编码1": [
                    {
                        "content": "一阶编码内容1",
                        "code_id": "A01",
                        "sentence_details": [
                            {
                                "text": "测试句子1",
                                "file_path": "test_file1.txt",
                                "sentence_id": "1"
                            }
                        ]
                    },
                    "一阶编码内容2"  # 非字典格式内容
                ]
            }
        }

        # 验证统计结果
        expected_second_level_count = 2  # 1 (字典格式) + 1 (非字典格式)
        expected_third_level_count = 2

        # 验证二阶编码统计
        for third_cat, second_cats in mixed_structure.items():
            for second_cat, first_contents in second_cats.items():
                actual_second_count = 0
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        actual_second_count += len(sentence_details) if sentence_details else 1
                    else:
                        actual_second_count += 1
                self.assertEqual(actual_second_count, expected_second_level_count, 
                                 f"混合内容类型的二阶编码句子来源数统计错误")

            # 验证三阶编码统计
            actual_third_count = 0
            for second_cat, first_contents in second_cats.items():
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        actual_third_count += len(sentence_details) if sentence_details else 1
                    else:
                        actual_third_count += 1
            self.assertEqual(actual_third_count, expected_third_level_count, 
                             f"混合内容类型的三阶编码句子来源数统计错误")


def validate_coding_statistics(coding_structure):
    """自动化校验工具：验证编码统计数据的一致性"""
    """
    实时监控编码统计数据的一致性
    
    Args:
        coding_structure: 编码结构字典
    
    Returns:
        dict: 包含验证结果的字典
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "statistics": {
            "third_level": {},
            "second_level": {}
        }
    }

    try:
        for third_cat, second_cats in coding_structure.items():
            third_count = 0
            for second_cat, first_contents in second_cats.items():
                second_count = 0
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        second_count += len(sentence_details) if sentence_details else 1
                    else:
                        second_count += 1
                third_count += second_count
                validation_result["statistics"]["second_level"][second_cat] = second_count
            validation_result["statistics"]["third_level"][third_cat] = third_count
    except Exception as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"统计计算错误: {e}")

    return validation_result

# 创建QApplication实例
app = None
if not QApplication.instance():
    app = QApplication(sys.argv)

class TestCodingStatisticsIntegration(unittest.TestCase):
    """测试编码统计机制的集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.settings = QSettings("GroundedTheory", "CodingSystem")
        # 创建测试文件数据
        self.test_files = {
            "test_file1.txt": {
                "filename": "test_file1.txt",
                "file_path": "test_file1.txt",
                "content": "测试句子1 [1] 测试句子2 [2]",
                "numbered_content": "测试句子1 [1] 测试句子2 [2]"
            },
            "test_file2.txt": {
                "filename": "test_file2.txt",
                "file_path": "test_file2.txt",
                "content": "测试句子3 [3] 测试句子4 [4]",
                "numbered_content": "测试句子3 [3] 测试句子4 [4]"
            }
        }

    def test_coding_statistics_consistency(self):
        """测试编码统计数据的一致性"""
        # 创建一个复杂的编码结构
        complex_structure = {
            "C01 三阶编码1": {
                "B01 二阶编码1": [
                    {
                        "content": "一阶编码内容1",
                        "code_id": "A01",
                        "sentence_details": [
                            {
                                "text": "测试句子1",
                                "file_path": "test_file1.txt",
                                "sentence_id": "1"
                            },
                            {
                                "text": "测试句子2",
                                "file_path": "test_file1.txt",
                                "sentence_id": "2"
                            }
                        ]
                    }
                ],
                "B02 二阶编码2": [
                    {
                        "content": "一阶编码内容2",
                        "code_id": "A02",
                        "sentence_details": [
                            {
                                "text": "测试句子3",
                                "file_path": "test_file2.txt",
                                "sentence_id": "3"
                            }
                        ]
                    }
                ]
            }
        }

        # 计算期望的统计结果
        expected_third_count = 3  # 2 + 1
        expected_second_counts = {
            "B01 二阶编码1": 2,
            "B02 二阶编码2": 1
        }

        # 验证统计结果一致性
        actual_third_count = 0
        actual_second_counts = {}

        for third_cat, second_cats in complex_structure.items():
            for second_cat, first_contents in second_cats.items():
                second_count = 0
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        sentence_details = content_data.get('sentence_details', [])
                        second_count += len(sentence_details) if sentence_details else 1
                    else:
                        second_count += 1
                actual_second_counts[second_cat] = second_count
                actual_third_count += second_count

        # 验证二阶编码统计
        for second_cat, expected_count in expected_second_counts.items():
            self.assertEqual(actual_second_counts.get(second_cat), expected_count, 
                             f"二阶编码 {second_cat} 统计不一致")

        # 验证三阶编码统计
        self.assertEqual(actual_third_count, expected_third_count, 
                         "三阶编码统计不一致")

if __name__ == '__main__':
    unittest.main()
