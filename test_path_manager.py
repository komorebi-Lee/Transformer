import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from path_manager import PathManager


class TestPathManager(unittest.TestCase):
    """测试 PathManager 的路径管理功能"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_dir = tempfile.mkdtemp()
        cls.original_cwd = os.getcwd()
        os.chdir(cls.test_dir)
        
        # 重置 PathManager 的基础路径
        PathManager._BASE_DIR = None
        PathManager._IS_FROZEN = False

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        os.chdir(cls.original_cwd)
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        """每个测试方法前的初始化"""
        # 重置 PathManager
        PathManager._BASE_DIR = None
        PathManager._IS_FROZEN = False

    def test_get_base_dir(self):
        """测试获取基础目录"""
        base_dir = PathManager.get_base_dir()
        self.assertTrue(os.path.isabs(base_dir))
        self.assertTrue(os.path.exists(base_dir))
        self.assertEqual(base_dir, os.path.normpath(base_dir))

    def test_join_paths(self):
        """测试路径拼接"""
        base_dir = PathManager.get_base_dir()
        
        # 测试单一路径
        result = PathManager.join("test")
        expected = os.path.normpath(os.path.join(base_dir, "test"))
        self.assertEqual(result, expected)
        
        # 测试多级路径
        result = PathManager.join("test", "subdir", "file.txt")
        expected = os.path.normpath(os.path.join(base_dir, "test", "subdir", "file.txt"))
        self.assertEqual(result, expected)

    def test_get_absolute_path(self):
        """测试获取绝对路径"""
        base_dir = PathManager.get_base_dir()
        
        # 相对路径
        result = PathManager.get_absolute_path("test.txt")
        expected = os.path.normpath(os.path.join(base_dir, "test.txt"))
        self.assertEqual(result, expected)
        
        # 绝对路径
        abs_path = os.path.abspath("/absolute/path/test.txt")
        result = PathManager.get_absolute_path(abs_path)
        self.assertEqual(result, os.path.normpath(abs_path))

    def test_ensure_dir(self):
        """测试确保目录存在"""
        test_dir = "test_ensure_dir"
        result = PathManager.ensure_dir(test_dir)
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(os.path.isdir(result))
        
        # 再次调用应该不会出错
        PathManager.ensure_dir(test_dir)
        
        # 清理
        shutil.rmtree(result, ignore_errors=True)

    def test_exists(self):
        """测试路径存在性检查"""
        # 创建测试文件
        test_file = "test_exists.txt"
        with open(test_file, 'w') as f:
            f.write("test")
        
        self.assertTrue(PathManager.exists(test_file))
        self.assertFalse(PathManager.exists("non_existent_file.txt"))
        
        # 清理
        os.remove(test_file)

    def test_is_file(self):
        """测试文件类型检查"""
        # 创建测试文件
        test_file = "test_is_file.txt"
        with open(test_file, 'w') as f:
            f.write("test")
        
        self.assertTrue(PathManager.is_file(test_file))
        self.assertFalse(PathManager.is_dir(test_file))
        
        # 清理
        os.remove(test_file)

    def test_is_dir(self):
        """测试目录类型检查"""
        test_dir = "test_is_dir"
        os.makedirs(test_dir)
        
        self.assertTrue(PathManager.is_dir(test_dir))
        self.assertFalse(PathManager.is_file(test_dir))
        
        # 清理
        shutil.rmtree(test_dir)

    def test_get_file_path(self):
        """测试获取文件路径"""
        result = PathManager.get_file_path("test.txt")
        self.assertTrue(result.endswith("test.txt"))
        
        result = PathManager.get_file_path("test.txt", "subdir")
        self.assertTrue("subdir" in result)
        self.assertTrue(result.endswith("test.txt"))

    def test_get_dir_path(self):
        """测试获取目录路径"""
        result = PathManager.get_dir_path("test_dir")
        self.assertTrue(result.endswith("test_dir"))

    def test_get_projects_dir(self):
        """测试获取项目目录"""
        result = PathManager.get_projects_dir()
        self.assertTrue(result.endswith("projects"))
        self.assertTrue(os.path.isabs(result))

    def test_get_data_dir(self):
        """测试获取数据目录"""
        result = PathManager.get_data_dir()
        self.assertTrue(result.endswith("data"))
        self.assertTrue(os.path.isabs(result))

    def test_get_local_models_dir(self):
        """测试获取本地模型目录"""
        result = PathManager.get_local_models_dir()
        self.assertTrue(result.endswith("local_models"))
        self.assertTrue(os.path.isabs(result))

    def test_get_trained_models_dir(self):
        """测试获取训练模型目录"""
        result = PathManager.get_trained_models_dir()
        self.assertTrue(result.endswith("trained_models"))
        self.assertTrue(os.path.isabs(result))

    def test_get_standard_answers_dir(self):
        """测试获取标准答案目录"""
        result = PathManager.get_standard_answers_dir()
        self.assertTrue(result.endswith("standard_answers"))
        self.assertTrue(os.path.isabs(result))

    def test_get_output_dir(self):
        """测试获取输出目录"""
        result = PathManager.get_output_dir()
        self.assertTrue(result.endswith("output"))
        self.assertTrue(os.path.isabs(result))

    def test_get_cache_dir(self):
        """测试获取缓存目录"""
        result = PathManager.get_cache_dir()
        self.assertTrue(result.endswith("cache"))
        self.assertTrue(os.path.isabs(result))

    def test_get_logs_dir(self):
        """测试获取日志目录"""
        result = PathManager.get_logs_dir()
        self.assertTrue(result.endswith("logs"))
        self.assertTrue(os.path.isabs(result))

    def test_get_backup_dir(self):
        """测试获取备份目录"""
        result = PathManager.get_backup_dir()
        self.assertTrue(result.endswith("backups"))
        self.assertTrue(os.path.isabs(result))
        
        # 测试自定义基础目录
        custom_base = "/custom/base"
        result = PathManager.get_backup_dir(custom_base)
        self.assertTrue(result.endswith("backups"))
        self.assertTrue(custom_base in result)

    def test_get_modifications_dir(self):
        """测试获取修改记录目录"""
        result = PathManager.get_modifications_dir()
        self.assertTrue(result.endswith("modifications"))
        self.assertTrue(os.path.isabs(result))
        
        # 测试自定义基础目录
        custom_base = "/custom/base"
        result = PathManager.get_modifications_dir(custom_base)
        self.assertTrue(result.endswith("modifications"))
        self.assertTrue(custom_base in result)

    def test_get_manual_coding_save_dir(self):
        """测试获取手动编码保存目录"""
        result = PathManager.get_manual_coding_save_dir()
        self.assertTrue("手动编码保存编码" in result)
        self.assertTrue(os.path.isabs(result))

    def test_get_manual_coding_tree_save_dir(self):
        """测试获取手动编码树保存目录"""
        result = PathManager.get_manual_coding_tree_save_dir()
        self.assertTrue("手动编码编码树保存" in result)
        self.assertTrue(os.path.isabs(result))

    def test_get_last_position_file(self):
        """测试获取最后编码位置文件"""
        result = PathManager.get_last_position_file()
        self.assertTrue(result.endswith("last_coding_position.json"))
        self.assertTrue(os.path.isabs(result))

    def test_get_version_history_file(self):
        """测试获取版本历史文件"""
        result = PathManager.get_version_history_file()
        self.assertTrue(result.endswith("version_history.json"))
        self.assertTrue(os.path.isabs(result))

    def test_normalize_path(self):
        """测试路径规范化"""
        # 测试相对路径
        result = PathManager.normalize_path("test/../test/file.txt")
        self.assertTrue(".." not in result)
        
        # 测试绝对路径
        abs_path = os.path.abspath("/test/../test/file.txt")
        result = PathManager.normalize_path(abs_path)
        self.assertTrue(".." not in result)

    def test_get_relative_path(self):
        """测试获取相对路径"""
        base_dir = PathManager.get_base_dir()
        
        # 测试基础目录下的路径
        test_path = os.path.join(base_dir, "test", "file.txt")
        result = PathManager.get_relative_path(test_path)
        self.assertFalse(os.path.isabs(result))
        self.assertTrue(result.startswith("test"))
        
        # 测试基础目录外的路径
        outside_path = os.path.join(base_dir, "..", "outside", "file.txt")
        outside_path = os.path.normpath(outside_path)
        result = PathManager.get_relative_path(outside_path)
        # 应该返回绝对路径，因为不在基础目录下
        self.assertTrue(os.path.isabs(result))

    def test_safe_open(self):
        """测试安全打开文件"""
        test_file = "test_safe_open.txt"
        test_content = "测试内容"
        
        # 写入文件
        with PathManager.safe_open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 读取文件
        with PathManager.safe_open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertEqual(content, test_content)
        
        # 清理
        os.remove(test_file)

    def test_init_all_directories(self):
        """测试初始化所有目录"""
        PathManager.init_all_directories()
        
        # 检查所有目录是否已创建
        directories = [
            PathManager.get_projects_dir(),
            PathManager.get_data_dir(),
            PathManager.get_local_models_dir(),
            PathManager.get_trained_models_dir(),
            PathManager.get_standard_answers_dir(),
            PathManager.get_output_dir(),
            PathManager.get_cache_dir(),
            PathManager.get_logs_dir(),
            PathManager.get_backup_dir(),
            PathManager.get_modifications_dir(),
            PathManager.get_manual_coding_save_dir(),
            PathManager.get_manual_coding_tree_save_dir(),
        ]
        
        for directory in directories:
            self.assertTrue(os.path.exists(directory), f"目录不存在: {directory}")
            self.assertTrue(os.path.isdir(directory), f"不是目录: {directory}")

    def test_cross_platform_paths(self):
        """测试跨平台路径处理"""
        # 测试路径拼接
        result = PathManager.join("test", "subdir", "file.txt")
        
        # 验证路径分隔符是正确的
        self.assertTrue(os.path.isabs(result))
        
        # 验证路径规范化
        self.assertNotIn("//", result)
        self.assertNotIn("\\\\", result)

    def test_is_frozen(self):
        """测试是否在打包环境中"""
        # 在开发环境中，应该返回 False
        is_frozen = PathManager.is_frozen()
        self.assertFalse(is_frozen)


class TestPathManagerConvenienceFunctions(unittest.TestCase):
    """测试 PathManager 的便捷函数"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_dir = tempfile.mkdtemp()
        cls.original_cwd = os.getcwd()
        os.chdir(cls.test_dir)
        
        # 重置 PathManager 的基础路径
        PathManager._BASE_DIR = None
        PathManager._IS_FROZEN = False

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        os.chdir(cls.original_cwd)
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_get_base_dir(self):
        """测试便捷函数 get_base_dir"""
        from path_manager import get_base_dir
        result = get_base_dir()
        self.assertTrue(os.path.isabs(result))
        self.assertTrue(os.path.exists(result))

    def test_join_path(self):
        """测试便捷函数 join_path"""
        from path_manager import join_path
        result = join_path("test", "file.txt")
        self.assertTrue(result.endswith("file.txt"))
        self.assertTrue(os.path.isabs(result))

    def test_get_abs_path(self):
        """测试便捷函数 get_abs_path"""
        from path_manager import get_abs_path
        result = get_abs_path("test.txt")
        self.assertTrue(result.endswith("test.txt"))
        self.assertTrue(os.path.isabs(result))

    def test_ensure_dir(self):
        """测试便捷函数 ensure_dir"""
        from path_manager import ensure_dir
        test_dir = "test_ensure_dir_convenience"
        result = ensure_dir(test_dir)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(os.path.isdir(result))
        shutil.rmtree(result, ignore_errors=True)

    def test_file_exists(self):
        """测试便捷函数 file_exists"""
        from path_manager import file_exists
        test_file = "test_file_exists.txt"
        with open(test_file, 'w') as f:
            f.write("test")
        
        self.assertTrue(file_exists(test_file))
        self.assertFalse(file_exists("non_existent.txt"))
        
        os.remove(test_file)


class TestPathManagerFrozenMode(unittest.TestCase):
    """测试 PathManager 在打包环境中的行为"""

    def setUp(self):
        """每个测试方法前的初始化"""
        # 重置 PathManager
        PathManager._BASE_DIR = None
        PathManager._IS_FROZEN = False

    def test_frozen_mode_detection(self):
        """测试打包模式检测"""
        # 模拟打包环境
        import sys as sys_module
        original_frozen = getattr(sys_module, 'frozen', False)
        
        try:
            # 设置为打包模式
            sys_module.frozen = True
            PathManager._BASE_DIR = None
            PathManager._IS_FROZEN = False
            
            base_dir = PathManager.get_base_dir()
            self.assertTrue(PathManager.is_frozen())
            self.assertTrue(os.path.isabs(base_dir))
            
        finally:
            # 恢复原始状态
            sys_module.frozen = original_frozen
            PathManager._BASE_DIR = None
            PathManager._IS_FROZEN = False


if __name__ == '__main__':
    unittest.main(verbosity=2)
