import logging
from coding_library_manager import CodingLibraryManager
from semantic_matcher import SemanticMatcher

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

def test_semantic_matching():
    """测试语义匹配功能"""
    try:
        # 初始化编码库管理器
        coding_library = CodingLibraryManager()
        
        # 初始化语义匹配器
        semantic_matcher = SemanticMatcher()
        
        # 测试编码库加载
        library_info = coding_library.get_library_info()
        logger.info(f"编码库信息: {library_info}")
        
        # 获取所有二阶编码
        second_level_codes = coding_library.get_all_second_level_codes()
        logger.info(f"加载了 {len(second_level_codes)} 个二阶编码")
        
        # 获取所有三阶编码
        third_level_codes = coding_library.get_all_third_level_codes()
        logger.info(f"加载了 {len(third_level_codes)} 个三阶编码")
        
        # 测试一阶编码到二阶编码的匹配
        test_first_level_texts = [
            "利用工作间隙测试新的实验方法",
            "为了满足客户需求，在制度允许范围外提供额外服务",
            "担心创新失败会影响职业发展",
            "通过快速迭代试错来解决问题",
            "领导对创新行为持支持态度"
        ]
        
        logger.info("\n测试一阶编码到二阶编码的匹配:")
        for text in test_first_level_texts:
            matches = semantic_matcher.match_first_level_to_second_level(
                text,
                second_level_codes,
                top_k=3,
                threshold=0.5
            )
            
            logger.info(f"\n一阶编码: {text}")
            if matches:
                for i, (match, similarity) in enumerate(matches):
                    logger.info(f"  匹配 {i+1}: {match.get('name')} (相似度: {similarity:.4f}) - {match.get('third_level')}")
            else:
                logger.info("  未找到匹配的二阶编码")
        
        # 测试二阶编码到三阶编码的匹配
        if second_level_codes:
            test_second_level = second_level_codes[0]
            logger.info(f"\n测试二阶编码到三阶编码的匹配:")
            logger.info(f"二阶编码: {test_second_level.get('name')}")
            
            match_result = semantic_matcher.match_second_level_to_third_level(
                test_second_level,
                third_level_codes,
                threshold=0.5
            )
            
            if match_result:
                third_level, similarity = match_result
                logger.info(f"匹配的三阶编码: {third_level.get('name')} (相似度: {similarity:.4f})")
            else:
                logger.info("未找到匹配的三阶编码")
        
        logger.info("\n测试完成!")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_semantic_matching()
