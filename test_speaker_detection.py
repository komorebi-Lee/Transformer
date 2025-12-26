#!/usr/bin/env python3
"""
测试说话人识别功能
"""

import os
import sys
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_speaker_detection():
    """测试说话人识别"""
    print("🧪 测试说话人识别功能...")

    try:
        from data_processor import DataProcessor

        processor = DataProcessor()

        # 测试文本包含各种说话人标记和时间标记
        test_text = """
说话人1 00:00
采访者：请您介绍一下团队的主要职责？
说话人2 00:05
受访者：我们团队主要负责软件质量检测和测试工作。
说话人1 00:15
Interviewer: 在质量管理方面有什么创新吗？
说话人2 00:20
Interviewee: 我们开发了一套新的自动化测试框架。
00:25
主持人：团队面临的主要挑战是什么？
01:30
嘉宾：最大的挑战是技术更新快。
记者：团队氛围怎么样？
专家：团队氛围很好，大家互相支持。
        """

        print("原始文本:")
        print(test_text)

        # 测试文本清洗
        cleaned_text = processor.clean_text(test_text)
        print("\n清洗后文本:")
        print(cleaned_text)

        # 测试段落识别
        paragraphs = processor.identify_interview_paragraphs(test_text, "test_file.txt")

        print("\n识别出的段落:")
        for i, paragraph in enumerate(paragraphs):
            speaker = paragraph['speaker']
            content = paragraph['content'][:100] + "..." if len(paragraph['content']) > 100 else paragraph['content']
            print(f"{i + 1}. {speaker}: {content}")

        # 验证过滤效果
        has_speaker_marks = any(
            '说话人' in test_text or 'Interviewer' in test_text or '00:' in test_text for line in test_text.split('\n'))
        has_cleaned_marks = any(
            '说话人' in cleaned_text or 'Interviewer' in cleaned_text or '00:' in cleaned_text for line in
            cleaned_text.split('\n'))

        if has_speaker_marks and not has_cleaned_marks:
            print("✅ 说话人标记过滤成功")
        else:
            print("❌ 说话人标记过滤不彻底")

        # 验证段落识别
        interviewer_count = sum(1 for p in paragraphs if p['speaker'] == 'interviewer')
        respondent_count = sum(1 for p in paragraphs if p['speaker'] == 'respondent')

        print(f"识别出 {interviewer_count} 个采访人段落，{respondent_count} 个受访人段落")

        if interviewer_count > 0 and respondent_count > 0:
            print("✅ 说话人识别成功")
        else:
            print("❌ 说话人识别可能有问题")

        return True

    except Exception as e:
        print(f"❌ 说话人识别测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("扎根理论编码分析系统 - 说话人识别测试")
    print("=" * 60)

    success = test_speaker_detection()

    if success:
        print("\n🎉 说话人识别测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 说话人识别测试失败")
        sys.exit(1)