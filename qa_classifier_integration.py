"""
集成 QA 分类器到 speaker_role_extractor

使用示例和标注数据准备脚本
"""

import sys
import re
sys.path.insert(0, r'D:\zthree2')

from speaker_role_extractor import SpeakerRoleExtractor
from qa_classifier import QAClassifier
import pandas as pd


# ============================================================
# 方案1: 使用 QA 分类器替代复杂的规则逻辑
# ============================================================

class SpeakerRoleExtractorV2:
    """
    使用 QA 分类器的说话人角色识别器
    
    优势：
    - 避免复杂的规则逻辑和死循环
    - 可以通过标注数据持续改进
    - 轻量级，推理速度快
    """
    
    def __init__(self, qa_model_path: str = None):
        """
        初始化
        
        Args:
            qa_model_path: QA 分类器模型路径（None=规则模式）
        """
        self.qa_classifier = QAClassifier()
        self.qa_classifier.load_model(qa_model_path)
    
    def extract_interviewee_sentences(
        self,
        text: str,
        return_metadata: bool = False,
        confidence_threshold: float = 0.6
    ):
        """
        提取受访者语句
        
        Args:
            text: 原始文本
            return_metadata: 是否返回元数据
            confidence_threshold: 置信度阈值
            
        Returns:
            受访者语句列表
        """
        # 预处理
        text = self._preprocess(text)
        
        # 分句
        sentences = self._split_sentences(text)
        
        # 使用 QA 分类器分类
        results = self.qa_classifier.classify_batch(sentences)
        
        # 过滤出受访者回答
        interviewee_sentences = []
        for result in results:
            if result['label'] == 'answer' and result['confidence'] >= confidence_threshold:
                if return_metadata:
                    interviewee_sentences.append({
                        'text': result['text'],
                        'confidence': result['confidence'],
                        'speaker_label': None,
                        'method': 'qa_classifier',
                        'scores': result['scores']
                    })
                else:
                    interviewee_sentences.append(result['text'])
        
        return interviewee_sentences
    
    def _preprocess(self, text: str) -> str:
        """预处理文本"""
        # 清理时间戳
        text = re.sub(r'\d{2}:\d{2}', '', text)
        # 清理标注残留
        text = re.sub(r'^(问题|回答|标签对好)\s*', '', text, flags=re.MULTILINE)
        # 统一换行
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text.strip()
    
    def _split_sentences(self, text: str) -> list:
        """分句"""
        import re
        # 按标点分句
        sentences = re.split(r'[。！？\n]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 5]


# ============================================================
# 标注数据准备脚本
# ============================================================

def create_annotation_template(input_file: str, output_file: str):
    """
    创建标注模板
    
    Args:
        input_file: 输入的访谈文本文件（docx）
        output_file: 输出的标注模板（CSV）
    """
    from docx import Document
    import pandas as pd
    
    # 读取文档
    doc = Document(input_file)
    
    # 提取所有段落
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text and len(text) >= 5:
            paragraphs.append(text)
    
    # 创建标注模板
    df = pd.DataFrame({
        'text': paragraphs,
        'label': ''  # 待标注：question / answer / other
    })
    
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"标注模板已创建: {output_file}")
    print(f"共 {len(df)} 条待标注")
    print("\n请在 Excel 中打开并标注 label 列：")
    print("  - question: 访谈员问句")
    print("  - answer: 受访者回答")
    print("  - other: 其他/不确定")


def validate_annotations(annotated_file: str):
    """验证标注数据"""
    import pandas as pd
    
    df = pd.read_csv(annotated_file)
    
    print(f"总样本数: {len(df)}")
    print(f"\n标签分布:")
    print(df['label'].value_counts())
    
    # 检查空标签
    empty = df['label'].isna().sum() + (df['label'] == '').sum()
    if empty > 0:
        print(f"\n警告: {empty} 条样本未标注")
    
    # 检查非法标签
    valid_labels = {'question', 'answer', 'other'}
    invalid = df[~df['label'].isin(valid_labels)]
    if len(invalid) > 0:
        print(f"\n警告: {len(invalid)} 条样本标签非法")
        print(invalid[['text', 'label']].head())
    
    return df


# ============================================================
# 使用示例
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("示例1: 使用 QA 分类器（规则模式）")
    print("=" * 60)
    
    extractor_v2 = SpeakerRoleExtractorV2()
    
    test_text = """
    那您觉得景漂这个称呼对您意味着是什么呢？
    那倒没有可能也就只是一个标签吧。
    那您刚来的时候遇到的最大困难是什么呢？
    没钱哦。当时真的很困难。
    那如何解决这个困难呢？
    就是慢慢积累，一点一点做起来的。
    """
    
    results = extractor_v2.extract_interviewee_sentences(test_text, return_metadata=True)
    
    print(f"\n提取到 {len(results)} 条受访者语句:")
    for i, item in enumerate(results):
        print(f"\n[{i+1}] 置信度: {item['confidence']:.2f}")
        print(f"    {item['text']}")
        print(f"    分数: Q={item['scores']['question']:.2f}, "
              f"A={item['scores']['answer']:.2f}, "
              f"O={item['scores']['other']:.2f}")
    
    print("\n" + "=" * 60)
    print("示例2: 创建标注模板")
    print("=" * 60)
    print("\n使用方法:")
    print("1. 准备访谈文本文件（docx格式）")
    print("2. 运行: create_annotation_template('input.docx', 'to_annotate.csv')")
    print("3. 在 Excel 中打开 to_annotate.csv，标注 label 列")
    print("4. 保存为 annotated.csv")
    print("5. 运行: validate_annotations('annotated.csv')")
    print("6. 训练模型: train_qa_classifier(texts, labels, output_dir='./qa_model')")
    print("7. 使用微调模型: extractor = SpeakerRoleExtractorV2(qa_model_path='./qa_model')")
    
    print("\n" + "=" * 60)
    print("标注数据量建议:")
    print("=" * 60)
    print("- 最小: 100条（50 question + 50 answer）")
    print("- 推荐: 300条（100 question + 150 answer + 50 other）")
    print("- 理想: 1000条（平衡分布）")
    print("\n标注来源:")
    print("- 从现有访谈文件中随机抽取")
    print("- 覆盖不同领域、不同风格的访谈")
    print("- 包含明确标注、说话人编号、问答杂糅等各种情况")
