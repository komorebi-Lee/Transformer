"""
一阶编码质量测试脚本

对 D:\c盘\文本样本 中的所有 docx 文件进行一阶编码测试，
输出编码结果供人工评估。

用法: D:\anaconda3\envs\zthree5\python.exe test_first_level_coding.py
"""
import json
import logging
import os
import re
import sys
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.WARNING,  # 减少日志噪音
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

TEST_DIR = r"D:\c盘\文本样本"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coding_test_results.json")
OUTPUT_TEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coding_test_results.txt")


def extract_sentences_from_docx(filepath):
    """从 docx 文件中提取受访者句子"""
    from docx import Document
    doc = Document(filepath)

    sentences = []
    current_speaker = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text or len(text) < 8:
            continue

        # 检测说话人标记 (A:, B:, C: 或 A： B： C：)
        speaker_match = re.match(r'^([A-C]|[问答题])\s*[：:]\s*', text)
        if speaker_match:
            speaker_label = speaker_match.group(1)
            text = re.sub(r'^([A-C]|[问答题])\s*[：:]\s*', '', text).strip()
            if speaker_label in ('A', '问', '题'):
                current_speaker = 'interviewer'
            elif speaker_label in ('B', 'C', '答'):
                current_speaker = 'respondent'

        if not text or len(text) < 8:
            continue

        # 跳过元数据行
        if re.match(r'^(访谈录音转录|样本\d+|基本信息|行业[：:]|部门[：:]|职位[：:]|工作年限[：:]|姓名[：:]|正式访谈)', text):
            continue

        # 跳过纯数字
        if re.match(r'^\d+$', text):
            continue

        # 跳过纯问句（访员提问）
        if re.search(r'[吗呢呀嘛啊][？?]?$', text) and current_speaker in ('interviewer', 'unknown', None):
            continue
        if re.search(r'^(什么|怎么|为什么|如何|哪些|是不是|能不能|要不要|有没有|可不可以|会不会)', text):
            if current_speaker in ('interviewer', 'unknown', None):
                continue

        # 按句号、问号、感叹号分句
        raw_sentences = re.split(r'[。！？!?；;]', text)
        for sent in raw_sentences:
            sent = sent.strip()
            # 跳过问句片段
            if re.search(r'[吗呢呀嘛啊][？?]?$', sent):
                continue
            if len(sent) >= 10:  # 至少10字
                sentences.append({
                    'content': sent,
                    'speaker': current_speaker or 'unknown',
                    'file': os.path.basename(filepath),
                })

    return sentences


def grade_code_quality(code: str, original: str) -> str:
    """根据一阶编码质量标准自动评分 (A/B/C/D)"""
    if not code:
        return 'D'

    # D级检查：硬性淘汰条件
    # 语义残缺
    if re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', code):
        if not re.search(r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险|'
                        r'种植|养殖|加工|收购|销售|市场|价格|成本|利润|工艺|技术|生产|标准|检验|认证)', code):
            return 'D'
    if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时|而且|而|但)', code):
        if not re.search(r'(导致|影响|推动|形成|引入|转变|降低|提高|获得|支持|需求|资源|客户)', code):
            return 'D'
    if re.search(r'(什么|怎么|哪些|怎么样|如何|哪方面|什么时候)', code):
        return 'D'
    # 口语残留
    if re.search(r'[吧呢啊嘛呀哦哈哎诶噢呃]', code):
        return 'D'
    if re.search(r'(怎么说呢|就是说|我觉得|相当于|这个东西|这个事情|这个问题|什么的|之类的|那种感觉)', code):
        return 'D'
    if re.search(r'^(我|我们|你|你们|他|他们|大家|那个|这个|这些|那些|这种|那种)', code):
        return 'D'
    if re.search(r'(对不对|是不是|行不行|能不能|有没有|要不要)', code):
        return 'D'
    # 长度检查
    if len(code) < 4:
        return 'D'
    if len(code) > 30:
        return 'D'

    # 信息量检查
    info_terms = r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险|'
    info_terms += r'种植|养殖|加工|收购|销售|市场|价格|成本|利润|工艺|技术|生产|标准|检验|认证|'
    info_terms += r'引入|建立|调整|获得|降低|提高|推动|解决|分析|反馈|合作|转变|优化|对接|支持|'
    info_terms += r'审批|协调|整合|压力|约束|冲突|规范|培训|投资|收入|资金|设备|工具|原料|'
    info_terms += r'影响|导致|受限|不足|短板|风险|延迟|缺乏|缺少|推动|推进|降低|增加)'
    has_info = bool(re.search(info_terms, code))

    # 纯名词短语检查（缺谓语，概念不完整）
    verb_indicators = r'(缺乏|缺少|不足|受限|导致|影响|推动|降低|提高|优化|开展|进行|建立|引入|获得|调整|转变|对接|合作|协调|整合|增加|减少|推进|执行|实施|完成|实现)'
    has_verb = bool(re.search(verb_indicators, code))

    # 评分逻辑
    if not has_info and not has_verb and len(code) <= 6:
        return 'D'  # 太短且无信息
    if not has_info and len(code) <= 5:
        return 'C'  # 很短但也许可接受

    # A级: 有信息词+有动词结构+长度适中
    if has_info and has_verb and 6 <= len(code) <= 20:
        return 'A'
    # B级: 有信息词但无动词结构，或长度稍长但完整
    if has_info and 6 <= len(code) <= 24:
        return 'B'
    # B级: 有动词结构且长度适中
    if has_verb and 6 <= len(code) <= 20:
        return 'B'
    # C级: 长度合理但信息量少
    if 6 <= len(code) <= 20:
        return 'C'
    # 其他情况
    if len(code) >= 4:
        return 'C'

    return 'D'


def main():
    """主测试流程"""
    # 1. 加载模块
    from model_manager import EnhancedModelManager
    from enhanced_coding_generator import EnhancedCodingGenerator

    # 2. 提取所有句子
    print("=" * 60)
    print("一阶编码质量测试")
    print("=" * 60)

    all_sentences = []
    docx_files = sorted([
        f for f in os.listdir(TEST_DIR)
        if f.endswith('.docx') and not f.startswith('~')
    ])

    print(f"\n找到 {len(docx_files)} 个 docx 文件")

    for filename in docx_files:
        filepath = os.path.join(TEST_DIR, filename)
        try:
            sentences = extract_sentences_from_docx(filepath)
            all_sentences.extend(sentences)
            print(f"  {filename}: {len(sentences)} 个句子")
        except Exception as e:
            print(f"  {filename}: 提取失败 - {e}")

    print(f"\n总共提取 {len(all_sentences)} 个句子")

    # 3. 初始化编码生成器和模型管理器
    print("\n初始化模型管理器...")
    model_manager = EnhancedModelManager()

    print("初始化编码生成器...")
    generator = EnhancedCodingGenerator()

    # 4. 对每个句子进行一阶编码
    print("\n开始一阶编码...")
    results = []
    candidate_details = []

    for i, sent_info in enumerate(all_sentences):
        content = sent_info['content']
        trace = generator.build_first_level_candidate_trace(
            content,
            model_manager=model_manager,
        )
        code = trace.get('selected_candidate', '') or ''
        candidates = trace.get('candidates', [])
        top3 = [c.get('text', '') for c in candidates[:3]]

        results.append({
            'index': i + 1,
            'file': sent_info['file'],
            'speaker': sent_info['speaker'],
            'original': content,
            'code': code,
            'top3_candidates': top3,
        })

        candidate_details.append({
            'index': i + 1,
            'original': content[:80],
            'code': code,
            'all_candidates': [
                {
                    'text': c.get('text', ''),
                    'rule_score': c.get('rule_score'),
                    'rerank_score': c.get('rerank_score'),
                    'conservative_score': c.get('conservative_score'),
                }
                for c in candidates[:10]
            ],
        })

    # 5. 质量评分
    for r in results:
        r['grade'] = grade_code_quality(r['code'], r['original'])

    # 6. 统计
    total = len(results)
    coded = sum(1 for r in results if r['code'])
    no_code = total - coded

    # 质量分布 (仅统计有编码的结果)
    coded_results = [r for r in results if r['code']]
    grades = Counter(r.get('grade', 'D') for r in coded_results)
    acceptable = sum(v for k, v in grades.items() if k in ('A', 'B', 'C'))
    accuracy = acceptable / max(len(coded_results), 1) * 100

    # 长度分布
    lengths = [len(r['code']) for r in results if r['code']]
    avg_len = sum(lengths) / max(len(lengths), 1)

    # 口语残留检查
    colloquial_patterns = [
        r'[吧呢啊嘛呀哦哈哎诶噢呃]',
        r'(怎么说呢|就是说|我觉得|相当于|这个东西|这个事情|这个问题|什么的|之类的)',
        r'^(我|我们|你|你们|他|他们|大家)',
        r'(那种感觉|这种感觉|这样子|那样子)',
    ]
    colloquial_count = 0
    for r in results:
        code = r['code']
        if code:
            for pat in colloquial_patterns:
                if re.search(pat, code):
                    colloquial_count += 1
                    break

    # 语义残缺检查
    incomplete_patterns = [
        r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$',
        r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)',
        r'(什么|怎么|哪些|怎么样|如何)',
    ]
    incomplete_count = 0
    for r in results:
        code = r['code']
        if code:
            for pat in incomplete_patterns:
                if re.search(pat, code):
                    incomplete_count += 1
                    break

    # 短码/长码
    too_short = sum(1 for r in results if r['code'] and len(r['code']) < 4)
    too_long = sum(1 for r in results if r['code'] and len(r['code']) > 30)

    print(f"\n{'=' * 60}")
    print(f"编码统计")
    print(f"{'=' * 60}")
    print(f"  总句子数:       {total}")
    print(f"  产生编码:       {coded} ({coded/total*100:.1f}%)" if total else "")
    print(f"  无编码(跳过):   {no_code} ({no_code/total*100:.1f}%)" if total else "")
    print(f"  平均编码长度:   {avg_len:.1f} 字")
    print(f"")
    print(f"  质量分布:")
    print(f"    A (优秀):     {grades.get('A', 0)} ({grades.get('A', 0)/max(total,1)*100:.1f}%)")
    print(f"    B (良好):     {grades.get('B', 0)} ({grades.get('B', 0)/max(total,1)*100:.1f}%)")
    print(f"    C (合格):     {grades.get('C', 0)} ({grades.get('C', 0)/max(total,1)*100:.1f}%)")
    print(f"    D (不合格):   {grades.get('D', 0)} ({grades.get('D', 0)/max(total,1)*100:.1f}%)")
    print(f"")
    if accuracy >= 60:
        print(f"  准确率(A+B+C):  {accuracy:.1f}% [达标]")
    else:
        print(f"  准确率(A+B+C):  {accuracy:.1f}% [未达标, 目标60%]")
    print(f"  口语残留:       {colloquial_count}")
    print(f"  语义残缺:       {incomplete_count}")
    print(f"  过短(<4字):     {too_short}")
    print(f"  过长(>30字):    {too_long}")

    # 7. 输出结果
    # JSON 详细结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'stats': {
                'total': total,
                'coded': coded,
                'no_code': no_code,
                'code_rate': f"{coded/total*100:.1f}%" if total else "N/A",
                'avg_len': round(avg_len, 1),
                'colloquial_count': colloquial_count,
                'incomplete_count': incomplete_count,
                'too_short': too_short,
                'too_long': too_long,
                'grades': dict(grades),
                'accuracy': f"{accuracy:.1f}%",
                'acceptable': acceptable,
            },
            'results': results,
            'candidate_details': candidate_details,
        }, f, ensure_ascii=False, indent=2)

    # 可读文本结果
    with open(OUTPUT_TEXT, 'w', encoding='utf-8') as f:
        f.write("一阶编码测试结果\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"总句子数: {total}  产生编码: {coded}  编码率: {coded/total*100:.1f}%\n" if total else "")
        f.write(f"准确率(A+B+C): {accuracy:.1f}%  ")
        f.write("[达标]\n" if accuracy >= 60 else "[未达标, 目标60%]\n")
        f.write(f"质量分布: A={grades.get('A',0)} B={grades.get('B',0)} C={grades.get('C',0)} D={grades.get('D',0)}\n")
        f.write(f"口语残留: {colloquial_count}  语义残缺: {incomplete_count}\n")
        f.write(f"过短: {too_short}  过长: {too_long}  平均长度: {avg_len:.1f} 字\n\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'#':<5} {'等级':<5} {'文件':<25} {'原文(截)':<45} {'一阶编码':<28}\n")
        f.write("-" * 80 + "\n")

        for r in results:
            code = r['code'] or '(无编码)'
            grade = r.get('grade', 'D')
            f.write(f"{r['index']:<5} {grade:<5} {r['file'][:23]:<25} {r['original'][:43]:<45} {code[:26]:<28}\n")

        f.write("\n\n" + "=" * 80 + "\n")
        f.write("候选详情 (含评分)\n")
        f.write("=" * 80 + "\n\n")

        for cd in candidate_details:
            f.write(f"[{cd['index']}] {cd['original']}\n")
            f.write(f"  选中: {cd['code']}\n")
            for c in cd['all_candidates']:
                marker = ' ★' if c['text'] == cd['code'] else '  '
                f.write(f"  {marker} {c['text'][:40]:<42} rule={c['rule_score']} rerank={c['rerank_score']} cons={c['conservative_score']}\n")
            f.write("\n")

    print(f"\n详细结果已保存到:")
    print(f"  JSON: {OUTPUT_FILE}")
    print(f"  TXT:  {OUTPUT_TEXT}")

    # 8. 输出一些样本供快速查看
    print(f"\n{'=' * 60}")
    print(f"样本编码结果 (前20条)")
    print(f"{'=' * 60}")
    for r in results[:20]:
        code = r['code'] or '(无编码)'
        grade = r.get('grade', 'D')
        print(f"\n[{r['index']}] [{grade}] {r['original'][:80]}")
        print(f"  → {code}")
        top3 = r.get('top3_candidates', [])
        if top3:
            print(f"  候选: {' | '.join(str(c)[:30] for c in top3[:3])}")

    # 9. D级样本 (不合格)
    d_grade = [r for r in results if r.get('grade') == 'D' and r['code']]
    if d_grade:
        print(f"\n{'=' * 60}")
        print(f"D级编码样本 (不合格, 共{len(d_grade)}条, 显示前10)")
        print(f"{'=' * 60}")
        for r in d_grade[:10]:
            print(f"\n[{r['index']}] {r['original'][:80]}")
            print(f"  → {r['code']}")

    return results


if __name__ == '__main__':
    main()
