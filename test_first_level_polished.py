"""
一阶编码质量测试 — 润色后文件
对 D:\c盘\新文本\润色后文件 中的 docx 文件进行一阶编码测试。
不采用自动编码管线的细粒度分句，使用段落级提取 + 粗略分句。

用法: D:\anaconda3\envs\zthree5\python.exe test_first_level_polished.py
"""
import json
import logging
import os
import re
import sys
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

TEST_DIR = r"D:\c盘\新文本\润色后文件"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "polished_coding_results.json")
OUTPUT_TEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "polished_coding_results.txt")


def extract_sentences_from_docx(filepath):
    """从润色后 docx 文件提取受访者句子（说话人2/说话人B/受访者）。

    分句策略（粗粒度，避免 pipeline 的过细分句）：
    - 首先按段落提取，识别说话人标记
    - 仅按句号、问号、感叹号分句（不按分号/逗号分句）
    - 最小句子长度 15 字，避免碎片
    """
    from docx import Document
    doc = Document(filepath)

    sentences = []
    current_speaker = None
    respondent_labels = {'说话人2', '说话人B', '说话人C', 'B', 'C', '答',
                         '受访者', '被访者', '嘉宾', '专家',
                         '讲话人2', '讲话人B', '讲话人C',
                         '手艺人', '商户', '游客', '景漂', '非遗手艺人',
                         '里弄管家', '管理层', '居民', '学徒', '传承人'}

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text or len(text) < 4:
            continue

        # 检测说话人标记: 说话人N, A:/B:/C:, 受访者: 等
        speaker_match = re.match(
            r'^(说话人\s*(\d+)|讲话人\s*(\d+)|[A-C]|问|答|采访者|访谈员|访员|主持人|记者|'
            r'受访者|被访者|嘉宾|专家|里弄管家\s*(\d+)|游客\s*(\d+)|手艺人\s*(\d+)|'
            r'商户\s*(\d+)|居民\s*(\d+)|学徒\s*(\d+)|传承人\s*(\d+)|'
            r'管理层\s*(\d+)|非遗手艺人\s*(\d+)|景漂\s*(\d+)|'
            r'工作人员\s*(\d+)|管理人员\s*(\d+)|一线工作人员\s*(\d+)|'
            r'高校教师\s*(\d+)|NPC\s*(\d+)|npc\s*(\d+)|AI\s*)'
            r'\s*[：:]\s*',
            text
        )
        if speaker_match:
            label = speaker_match.group(1)
            text = text[speaker_match.end():].strip()

            # 判断说话人角色
            interviewer_labels = {'说话人1', '讲话人1', 'A', '问', '采访者', '访谈员', '访员', '主持人', '记者'}
            if any(label.startswith(l) or label == l for l in interviewer_labels):
                current_speaker = 'interviewer'
            elif any(label.startswith(l) or label == l for l in respondent_labels):
                current_speaker = 'respondent'
            elif re.match(r'^(说话人|讲话人)\s*(\d+)', label):
                # 编号说话人：1=采访者，其他=受访者
                num_match = re.search(r'(\d+)', label)
                if num_match and num_match.group(1) == '1':
                    current_speaker = 'interviewer'
                else:
                    current_speaker = 'respondent'
            else:
                # 手艺人/商户/游客等角色标签 — 都是受访者
                current_speaker = 'respondent'

        if not text or len(text) < 4:
            continue

        # 跳过时间戳行
        if re.match(r'^\d{2}:\d{2}$', text):
            continue

        # 跳过采访者内容
        if current_speaker in ('interviewer',):
            continue

        # 粗粒度分句：仅按 。！？ 分句（不按分号分句，避免过散）
        raw_sentences = re.split(r'[。！？!?]', text)
        for sent in raw_sentences:
            sent = sent.strip()
            # 过滤问句
            if re.search(r'[吗呢呀嘛啊][？?]?$', sent):
                continue
            # 最小长度提高到 15 字，避免碎片
            if len(sent) >= 15:
                sentences.append({
                    'content': sent,
                    'speaker': current_speaker or 'unknown',
                    'file': os.path.basename(filepath),
                })

    return sentences


def grade_code_quality(code: str, original: str, is_anchor: bool = False) -> str:
    """根据一阶编码质量标准自动评分 (A/B/C/D)"""
    if not code:
        return 'D'

    # 通用硬性淘汰
    if re.search(r'[吧呢啊嘛呀哦哈哎诶噢呃]', code):
        return 'D'
    if re.search(r'(怎么说呢|就是说|我觉得|相当于|这个东西|这个事情|这个问题|什么的|之类的|那种感觉)', code):
        return 'D'
    if re.search(r'^(我|我们|你|你们|他|他们|大家|那个|这个|这些|那些|这种|那种)', code):
        return 'D'
    if re.search(r'(对不对|是不是|行不行|能不能|有没有|要不要)', code):
        return 'D'
    if re.search(r'(什么|怎么|哪些|怎么样|如何|哪方面|什么时候)', code):
        return 'D'
    if len(code) < 3:
        return 'D'
    if len(code) > 30:
        return 'D'

    if is_anchor:
        if re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', code):
            return 'D'
        if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时|而且|而|但)', code):
            return 'D'

        noun_indicators = r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险|'
        noun_indicators += r'种植|养殖|加工|收购|销售|市场|价格|成本|利润|工艺|技术|生产|标准|检验|认证|'
        noun_indicators += r'审批|协调|整合|压力|约束|冲突|规范|培训|投资|收入|资金|设备|工具|原料|'
        noun_indicators += r'制度|监督|治理|品牌|组织|团队|客户|绩效|渠道|运营|营销|供应链|'
        noun_indicators += r'传承|保护|非遗|技艺|文创|文旅|景区|教育|医疗|社区|公益|'
        noun_indicators += r'方式|方法|途径|手段|策略|模式|机制|体系|平台|系统|'
        noun_indicators += r'关系|认知|意愿|意识|态度|行为|观念|价值|文化|氛围|环境)'
        has_noun = bool(re.search(noun_indicators, code))

        verb_indicators = r'(缺乏|缺少|不足|受限|导致|影响|推动|降低|提高|优化|开展|进行|建立|引入|获得|调整|转变|对接|合作|协调|整合|增加|减少|推进|执行|实施|完成|实现)'
        has_verb = bool(re.search(verb_indicators, code))

        if 4 <= len(code) <= 8 and has_noun:
            return 'A'
        if 4 <= len(code) <= 10 and has_noun:
            return 'B'
        if has_verb and 3 <= len(code) <= 6:
            return 'B'
        if 4 <= len(code) <= 12:
            return 'C'
        return 'D'

    # 抽取式评分
    if re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', code):
        if not re.search(r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险|'
                        r'种植|养殖|加工|收购|销售|市场|价格|成本|利润|工艺|技术|生产|标准|检验|认证)', code):
            return 'D'
    if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时|而且|而|但)', code):
        if not re.search(r'(导致|影响|推动|形成|引入|转变|降低|提高|获得|支持|需求|资源|客户)', code):
            return 'D'
    if len(code) < 4:
        return 'D'

    info_terms = r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险|'
    info_terms += r'种植|养殖|加工|收购|销售|市场|价格|成本|利润|工艺|技术|生产|标准|检验|认证|'
    info_terms += r'引入|建立|调整|获得|降低|提高|推动|解决|分析|反馈|合作|转变|优化|对接|支持|'
    info_terms += r'审批|协调|整合|压力|约束|冲突|规范|培训|投资|收入|资金|设备|工具|原料|'
    info_terms += r'影响|导致|受限|不足|短板|风险|延迟|缺乏|缺少|推动|推进|降低|增加)'
    has_info = bool(re.search(info_terms, code))

    verb_indicators_ext = r'(缺乏|缺少|不足|受限|导致|影响|推动|降低|提高|优化|开展|进行|建立|引入|获得|调整|转变|对接|合作|协调|整合|增加|减少|推进|执行|实施|完成|实现)'
    has_verb_ext = bool(re.search(verb_indicators_ext, code))

    if not has_info and not has_verb_ext and len(code) <= 6:
        return 'D'
    if not has_info and len(code) <= 5:
        return 'C'
    if has_info and has_verb_ext and 6 <= len(code) <= 20:
        return 'A'
    if has_info and 6 <= len(code) <= 24:
        return 'B'
    if has_verb_ext and 6 <= len(code) <= 20:
        return 'B'
    if 6 <= len(code) <= 20:
        return 'C'
    if len(code) >= 4:
        return 'C'

    return 'D'


def main():
    print("=" * 60)
    print("一阶编码质量测试 — 润色后文件（粗粒度分句）")
    print("=" * 60)

    # 1. 提取所有句子
    all_sentences = []
    docx_files = sorted([
        f for f in os.listdir(TEST_DIR)
        if f.endswith('.docx') and not f.startswith('~')
    ])

    print(f"\n找到 {len(docx_files)} 个 docx 文件")

    file_stats = {}
    for filename in docx_files:
        filepath = os.path.join(TEST_DIR, filename)
        try:
            sentences = extract_sentences_from_docx(filepath)
            all_sentences.extend(sentences)
            file_stats[filename] = len(sentences)
            if len(sentences) > 0:
                print(f"  {filename}: {len(sentences)} 个句子")
        except Exception as e:
            print(f"  {filename}: 提取失败 - {e}")

    print(f"\n总共提取 {len(all_sentences)} 个受访者句子")

    if len(all_sentences) == 0:
        print("错误: 没有提取到任何句子，请检查文件格式。")
        return

    # 2. 初始化模型
    print("\n初始化模型管理器...")
    from model_manager import EnhancedModelManager
    model_manager = EnhancedModelManager()

    print("初始化编码生成器...")
    from enhanced_coding_generator import EnhancedCodingGenerator
    generator = EnhancedCodingGenerator()

    # 3. 一阶编码
    print("\n开始一阶编码...")
    results = []
    candidate_details = []

    total_count = len(all_sentences)
    for i, sent_info in enumerate(all_sentences):
        if i > 0 and i % 100 == 0:
            print(f"  进度: {i}/{total_count} ({i/total_count*100:.0f}%)", flush=True)
        content = sent_info['content']
        try:
            trace = generator.build_first_level_candidate_trace(
                content,
                model_manager=model_manager,
            )
        except Exception as e:
            logger.warning(f"编码失败 [{i}]: {e}")
            trace = {'selected_candidate': '', 'candidates': []}

        code = trace.get('selected_candidate', '') or ''
        candidates = trace.get('candidates', [])
        top3 = [c.get('text', '') for c in candidates[:3]]

        anchor_selected = trace.get('anchor_selected', False)
        anchor_source = trace.get('anchor_source', '')
        anchor_count = sum(1 for c in candidates if c.get('anchor_source'))
        grounding = trace.get('grounding')
        provenance = trace.get('provenance')
        hierarchy = trace.get('hierarchy', {})

        results.append({
            'index': i + 1,
            'file': sent_info['file'],
            'speaker': sent_info['speaker'],
            'original': content,
            'code': code,
            'top3_candidates': top3,
            'anchor_selected': anchor_selected,
            'anchor_source': anchor_source,
            'anchor_count': anchor_count,
            'grounding': grounding,
            'provenance': provenance,
            'hierarchy': hierarchy,
        })

        candidate_details.append({
            'index': i + 1,
            'original': content[:80],
            'code': code,
            'anchor_selected': anchor_selected,
            'anchor_source': anchor_source,
            'all_candidates': [
                {
                    'text': c.get('text', ''),
                    'rule_score': c.get('rule_score'),
                    'rerank_score': c.get('rerank_score'),
                    'conservative_score': c.get('conservative_score'),
                    'anchor_source': c.get('anchor_source', ''),
                    'anchor_score': c.get('anchor_score'),
                }
                for c in candidates[:10]
            ],
        })

    # 4. 质量评分
    for r in results:
        r['grade'] = grade_code_quality(r['code'], r['original'], is_anchor=r.get('anchor_selected', False))

    # 5. 统计
    total = len(results)
    coded = sum(1 for r in results if r['code'])
    no_code = total - coded

    coded_results = [r for r in results if r['code']]
    grades = Counter(r.get('grade', 'D') for r in coded_results)
    acceptable = sum(v for k, v in grades.items() if k in ('A', 'B', 'C'))
    accuracy = acceptable / max(len(coded_results), 1) * 100

    lengths = [len(r['code']) for r in results if r['code']]
    avg_len = sum(lengths) / max(len(lengths), 1)

    # 口语残留
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

    # 语义残缺
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

    too_short = sum(1 for r in results if r['code'] and len(r['code']) < 4)
    too_long = sum(1 for r in results if r['code'] and len(r['code']) > 30)

    # 锚点统计
    anchor_selected_count = sum(1 for r in results if r.get('anchor_selected'))
    anchor_pool_avg = sum(r.get('anchor_count', 0) for r in results) / max(len(results), 1)
    anchor_library_count = sum(1 for r in results if r.get('anchor_source') == 'library')

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
    print(f"")
    print(f"  概念锚点统计:")
    print(f"    锚点候选平均/句:  {anchor_pool_avg:.1f}")
    print(f"    锚点编码被选中:   {anchor_selected_count} ({anchor_selected_count/max(coded,1)*100:.1f}% of coded)")
    print(f"    选中锚点来源(library): {anchor_library_count}")

    # 按文件统计
    print(f"\n{'=' * 60}")
    print(f"按文件统计")
    print(f"{'=' * 60}")
    file_results = defaultdict(list)
    for r in results:
        file_results[r['file']].append(r)
    for fname in sorted(file_results.keys()):
        fr = file_results[fname]
        fcoded = sum(1 for r in fr if r['code'])
        faccept = sum(1 for r in fr if r.get('grade') in ('A', 'B', 'C') and r['code'])
        facc = faccept / max(fcoded, 1) * 100 if fcoded else 0
        print(f"  {fname}: {len(fr)}句, {fcoded}编码, 准确率{facc:.0f}%")

    # 6. 输出
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
                'file_stats': file_stats,
            },
            'results': results,
            'candidate_details': candidate_details,
        }, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_TEXT, 'w', encoding='utf-8') as f:
        f.write("一阶编码测试结果 — 润色后文件（粗粒度分句）\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"总句子数: {total}  产生编码: {coded}  编码率: {coded/total*100:.1f}%\n" if total else "")
        f.write(f"准确率(A+B+C): {accuracy:.1f}%  ")
        f.write("[达标]\n" if accuracy >= 60 else "[未达标, 目标60%]\n")
        f.write(f"质量分布: A={grades.get('A',0)} B={grades.get('B',0)} C={grades.get('C',0)} D={grades.get('D',0)}\n")
        f.write(f"口语残留: {colloquial_count}  语义残缺: {incomplete_count}\n")
        f.write(f"过短: {too_short}  过长: {too_long}  平均长度: {avg_len:.1f} 字\n\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'#':<5} {'等级':<5} {'文件':<30} {'原文(截)':<50} {'一阶编码':<30}\n")
        f.write("-" * 80 + "\n")

        for r in results:
            code = r['code'] or '(无编码)'
            grade = r.get('grade', 'D')
            f.write(f"{r['index']:<5} {grade:<5} {r['file'][:28]:<30} {r['original'][:48]:<50} {code[:28]:<30}\n")

        f.write("\n\n" + "=" * 80 + "\n")
        f.write("候选详情 (含评分)\n")
        f.write("=" * 80 + "\n\n")

        for cd in candidate_details:
            if not cd['code']:
                continue
            f.write(f"[{cd['index']}] {cd['original']}\n")
            f.write(f"  选中: {cd['code']}\n")
            for c in cd['all_candidates']:
                marker = ' ★' if c['text'] == cd['code'] else '  '
                f.write(f"  {marker} {c['text'][:40]:<42} rule={c['rule_score']} rerank={c['rerank_score']} cons={c['conservative_score']}\n")
            f.write("\n")

    print(f"\n详细结果已保存到:")
    print(f"  JSON: {OUTPUT_FILE}")
    print(f"  TXT:  {OUTPUT_TEXT}")

    # 7. 样本输出
    print(f"\n{'=' * 60}")
    print(f"样本编码结果 (前20条)")
    print(f"{'=' * 60}")
    for r in results[:20]:
        code = r['code'] or '(无编码)'
        grade = r.get('grade', 'D')
        print(f"\n[{r['index']}] [{grade}] {r['original'][:100]}")
        print(f"  → {code}")

    # 8. D级样本
    d_grade = [r for r in results if r.get('grade') == 'D' and r['code']]
    if d_grade:
        print(f"\n{'=' * 60}")
        print(f"D级编码样本 (不合格, 共{len(d_grade)}条, 显示前15)")
        print(f"{'=' * 60}")
        for r in d_grade[:15]:
            print(f"\n[{r['index']}] {r['original'][:100]}")
            print(f"  → {r['code']}")

    # 9. 无编码样本
    no_code_items = [r for r in results if not r['code']]
    if no_code_items:
        print(f"\n{'=' * 60}")
        print(f"无编码句子 (共{len(no_code_items)}条, 显示前10)")
        print(f"{'=' * 60}")
        for r in no_code_items[:10]:
            print(f"\n[{r['index']}] {r['original'][:120]}")

    return results


if __name__ == '__main__':
    main()
