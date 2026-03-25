import json
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CodingLibraryManager:
    """编码库管理器"""

    def __init__(self, library_path: str = "coding_library.json", semantic_matcher=None):
        """
        初始化编码库管理器

        Args:
            library_path: 编码库文件路径
            semantic_matcher: 语义匹配器实例
        """
        self.library_path = library_path
        self.library_data: Dict[str, Any] = {}
        self.second_level_codes: List[Dict[str, Any]] = []
        self.third_level_codes: List[Dict[str, Any]] = []
        self.code_mappings: Dict[str, Dict[str, Any]] = {}
        self.semantic_matcher = semantic_matcher

        self.load_library()

    def load_library(self) -> bool:
        """
        加载编码库

        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(self.library_path):
                logger.error(f"编码库文件不存在: {self.library_path}")
                return False

            with open(self.library_path, 'r', encoding='utf-8') as f:
                self.library_data = json.load(f)

            # 提取所有二阶编码
            self.second_level_codes = []
            for third_level in self.library_data.get('encoding_library', {}).get('third_level_codes', []):
                third_level_name = third_level.get('name')
                for second_level in third_level.get('second_level_codes', []):
                    second_level['third_level'] = third_level_name
                    self.second_level_codes.append(second_level)

            # 提取所有三阶编码
            self.third_level_codes = self.library_data.get('encoding_library', {}).get('third_level_codes', [])

            # 构建编码映射
            self.code_mappings = {}
            for second_level in self.second_level_codes:
                code_id = second_level.get('id')
                if code_id:
                    self.code_mappings[code_id] = second_level

            logger.info(f"编码库加载成功，包含 {len(self.third_level_codes)} 个三阶编码和 {len(self.second_level_codes)} 个二阶编码")
            return True

        except Exception as e:
            logger.error(f"加载编码库失败: {e}")
            return False

    def get_all_second_level_codes(self) -> List[Dict[str, Any]]:
        """
        获取所有二阶编码

        Returns:
            二阶编码列表
        """
        return self.second_level_codes

    def get_all_third_level_codes(self) -> List[Dict[str, Any]]:
        """
        获取所有三阶编码

        Returns:
            三阶编码列表
        """
        return self.third_level_codes

    def get_second_level_by_id(self, code_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取二阶编码

        Args:
            code_id: 二阶编码ID

        Returns:
            二阶编码信息
        """
        return self.code_mappings.get(code_id)

    def get_second_level_codes_by_third_level(self, third_level_name: str) -> List[Dict[str, Any]]:
        """
        根据三阶编码获取相关的二阶编码

        Args:
            third_level_name: 三阶编码名称

        Returns:
            二阶编码列表
        """
        return [code for code in self.second_level_codes if code.get('third_level') == third_level_name]

    def add_second_level_code(self, third_level_id: int, code_id: str, name: str, description: str) -> bool:
        """
        添加新的二阶编码

        Args:
            third_level_id: 所属三阶编码ID
            code_id: 二阶编码ID
            name: 二阶编码名称
            description: 二阶编码描述

        Returns:
            是否添加成功
        """
        try:
            # 找到对应的三阶编码
            third_level = None
            for code in self.third_level_codes:
                if code.get('id') == third_level_id:
                    third_level = code
                    break

            if not third_level:
                logger.error(f"找不到ID为 {third_level_id} 的三阶编码")
                return False

            # 检查是否已存在相同的二阶编码（通过ID或名称）
            for second_level in self.second_level_codes:
                if second_level.get('id') == code_id:
                    logger.error(f"二阶编码ID {code_id} 已存在")
                    return False
                if second_level.get('name') == name and second_level.get('third_level') == third_level.get('name'):
                    logger.error(f"在三阶编码 {third_level.get('name')} 下已存在名称为 {name} 的二阶编码")
                    return False

            # 检查在当前三阶编码下是否已存在相同名称的二阶编码
            for existing_code in third_level.get('second_level_codes', []):
                if existing_code.get('name') == name:
                    logger.error(f"在三阶编码 {third_level.get('name')} 下已存在名称为 {name} 的二阶编码")
                    return False

            # 创建新的二阶编码
            new_second_level = {
                'id': code_id,
                'name': name,
                'description': description,
                'third_level': third_level.get('name')
            }

            # 添加到三阶编码的二阶编码列表
            third_level.setdefault('second_level_codes', []).append(new_second_level)

            # 更新内部数据结构
            self.second_level_codes.append(new_second_level)
            self.code_mappings[code_id] = new_second_level

            # 保存到文件
            self.save_library()

            # 更新语义匹配器的编码嵌入
            if self.semantic_matcher:
                self.semantic_matcher.update_code_embeddings(self.second_level_codes)

            logger.info(f"添加二阶编码成功: {name}")
            return True

        except Exception as e:
            logger.error(f"添加二阶编码失败: {e}")
            return False

    def add_third_level_code(self, code_id: int, name: str, description: str) -> bool:
        """
        添加新的三阶编码

        Args:
            code_id: 三阶编码ID
            name: 三阶编码名称
            description: 三阶编码描述

        Returns:
            是否添加成功
        """
        try:
            # 检查ID是否已存在
            for code in self.third_level_codes:
                if code.get('id') == code_id:
                    logger.error(f"三阶编码ID {code_id} 已存在")
                    return False

            # 创建新的三阶编码
            new_third_level = {
                'id': code_id,
                'name': name,
                'description': description,
                'second_level_codes': []
            }

            # 添加到编码库
            self.third_level_codes.append(new_third_level)
            self.library_data.get('encoding_library', {}).get('third_level_codes', []).append(new_third_level)

            # 保存到文件
            self.save_library()

            logger.info(f"添加三阶编码成功: {name}")
            return True

        except Exception as e:
            logger.error(f"添加三阶编码失败: {e}")
            return False

    def save_library(self) -> bool:
        """
        保存编码库到文件

        Returns:
            是否保存成功
        """
        try:
            with open(self.library_path, 'w', encoding='utf-8') as f:
                json.dump(self.library_data, f, ensure_ascii=False, indent=2)

            logger.info(f"编码库已保存到: {self.library_path}")
            return True

        except Exception as e:
            logger.error(f"保存编码库失败: {e}")
            return False

    def delete_second_level_code(self, code_id: str) -> bool:
        """
        删除二阶编码

        Args:
            code_id: 二阶编码ID

        Returns:
            是否删除成功
        """
        try:
            # 检查编码是否存在
            if code_id not in self.code_mappings:
                logger.error(f"二阶编码ID {code_id} 不存在")
                return False

            # 获取编码信息
            second_level_code = self.code_mappings[code_id]
            third_level_name = second_level_code.get('third_level')
            code_name = second_level_code.get('name')

            # 从三阶编码的二阶编码列表中移除
            for third_level in self.third_level_codes:
                if third_level.get('name') == third_level_name:
                    second_level_codes = third_level.get('second_level_codes', [])
                    third_level['second_level_codes'] = [code for code in second_level_codes if code.get('id') != code_id]
                    break

            # 同时更新 library_data 中的数据
            if 'encoding_library' in self.library_data:
                third_level_codes = self.library_data['encoding_library'].get('third_level_codes', [])
                for third_level in third_level_codes:
                    if third_level.get('name') == third_level_name:
                        second_level_codes = third_level.get('second_level_codes', [])
                        third_level['second_level_codes'] = [code for code in second_level_codes if code.get('id') != code_id]
                        break

            # 从内部数据结构中移除
            self.second_level_codes = [code for code in self.second_level_codes if code.get('id') != code_id]
            del self.code_mappings[code_id]

            # 保存到文件
            self.save_library()

            # 更新语义匹配器的编码嵌入
            if self.semantic_matcher:
                self.semantic_matcher.update_code_embeddings(self.second_level_codes)

            logger.info(f"删除二阶编码成功: {code_name}")
            return True

        except Exception as e:
            logger.error(f"删除二阶编码失败: {e}")
            return False

    def delete_third_level_code(self, code_id: int) -> bool:
        """
        删除三阶编码

        Args:
            code_id: 三阶编码ID

        Returns:
            是否删除成功
        """
        try:
            # 检查编码是否存在
            third_level_code = None
            for code in self.third_level_codes:
                if code.get('id') == code_id:
                    third_level_code = code
                    break

            if not third_level_code:
                logger.error(f"三阶编码ID {code_id} 不存在")
                return False

            code_name = third_level_code.get('name')

            # 移除关联的二阶编码
            second_level_ids = [code.get('id') for code in third_level_code.get('second_level_codes', [])]
            for second_level_id in second_level_ids:
                if second_level_id in self.code_mappings:
                    del self.code_mappings[second_level_id]

            # 从二阶编码列表中移除关联的编码
            self.second_level_codes = [code for code in self.second_level_codes if code.get('third_level') != code_name]

            # 从三阶编码列表中移除
            self.third_level_codes = [code for code in self.third_level_codes if code.get('id') != code_id]

            # 从library_data中移除
            if 'encoding_library' not in self.library_data:
                self.library_data['encoding_library'] = {}
            if 'third_level_codes' not in self.library_data['encoding_library']:
                self.library_data['encoding_library']['third_level_codes'] = []
            
            self.library_data['encoding_library']['third_level_codes'] = [
                code for code in self.library_data['encoding_library']['third_level_codes'] 
                if code.get('id') != code_id
            ]

            # 保存到文件
            self.save_library()

            # 更新语义匹配器的编码嵌入
            if self.semantic_matcher:
                self.semantic_matcher.update_code_embeddings(self.second_level_codes)

            logger.info(f"删除三阶编码成功: {code_name}")
            return True

        except Exception as e:
            logger.error(f"删除三阶编码失败: {e}")
            return False

    def add_third_level_code(self, code_id: int, name: str, description: str) -> bool:
        """
        添加新的三阶编码

        Args:
            code_id: 三阶编码ID
            name: 三阶编码名称
            description: 三阶编码描述

        Returns:
            是否添加成功
        """
        try:
            # 检查ID是否已存在
            for code in self.third_level_codes:
                if code.get('id') == code_id:
                    logger.error(f"三阶编码ID {code_id} 已存在")
                    return False
                if code.get('name') == name:
                    logger.error(f"三阶编码名称 {name} 已存在")
                    return False

            # 创建新的三阶编码
            new_third_level = {
                'id': code_id,
                'name': name,
                'description': description,
                'second_level_codes': []
            }

            # 添加到编码库
            self.third_level_codes.append(new_third_level)
            self.library_data.get('encoding_library', {}).get('third_level_codes', []).append(new_third_level)

            # 保存到文件
            self.save_library()

            logger.info(f"添加三阶编码成功: {name}")
            return True

        except Exception as e:
            logger.error(f"添加三阶编码失败: {e}")
            return False

    def get_library_info(self) -> Dict[str, Any]:
        """
        获取编码库信息

        Returns:
            编码库信息
        """
        return {
            'version': self.library_data.get('version', '1.0'),
            'created_at': self.library_data.get('created_at', ''),
            'description': self.library_data.get('description', ''),
            'third_level_count': len(self.third_level_codes),
            'second_level_count': len(self.second_level_codes)
        }
