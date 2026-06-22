"""
批量 LLM 一阶编码测试 — 对润色后文件夹的 82 个 docx 文件进行编码并测量质量。

用法:
  D:/anaconda3/envs/zthree5/python.exe test_llm_coding_batch.py

流程:
  1. 加载 Qwen2.5-0.5B GGUF 模型
  2. 逐文件读取 docx（EnhancedDocxReader 标准化格式）
  3. 提取受访者语句（SpeakerRoleExtractor 过滤采访者）
  4. LLM 一阶编码
  5. 输出 CSV + 质量报告
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from collections import Counter
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from llm_first_level_coder import LLMFirstLevelCoder
from enhanced_docx_reader import EnhancedDocxReader
from speaker_role_extractor import SpeakerRoleExtractor
import config

# ── 配置 ──
SOURCE_DIR = r"D:\c盘\新文本\润色后文件"
OUTPUT_CSV = "llm_coding_results_taoxichuan.csv"
OUTPUT_JSON = "llm_coding_results_taoxichuan.json"
OUTPUT_DETAILED_JSON = "llm_coding_detailed_taoxichuan.json"

# 模型路径
MODEL_DIR = os.path.join("local_models", "llm_first_level_coder")
MODEL_NAME = "qwen2.5-0.5b-coding-Q4_K_M.gguf"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

# LLM 参数
TEMPERATURE = 0.1
TOP_P = 0.9
MAX_TOKENS = 128
N_GPU_LAYERS = -1  # 全部 GPU

# 测试控制
MAX_FILES = None  # None=全部，设数字限制测试数量
SENTENCE_MIN_LEN = 8  # 最短句子（过滤噪声）


def split_sentences(text):
    """按中文标点分句，保留10字以上有意义的句子。"""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r'[。！？；\n]', text)
    results = []
    for p in parts:
        p = p.strip()
        p = re.sub(r'[，、]{2,}', '', p)
        if len(p) >= SENTENCE_MIN_LEN:
            results.append(p)
    return results


def main():
    print("=" * 70)
    print("LLM 一阶编码批量测试 — 陶溪川访谈文本")
    print("=" * 70)

    # ── 1. 初始化 ──
    print(f"\n[1/5] 加载模型: {MODEL_NAME}")
    t0 = time.time()

    if not os.path.exists(MODEL_PATH):
        print(f"错误: 模型文件不存在: {MODEL_PATH}")
        print("请先运行 llm_first_level_coder 的 GGUF 导出流程")
        sys.exit(1)

    coder = LLMFirstLevelCoder(
        model_path=MODEL_PATH,
        n_gpu_layers=N_GPU_LAYERS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        max_tokens=MAX_TOKENS,
        verbose=False,
    )
    print(f"  模型加载耗时: {time.time() - t0:.1f}s")

    # ── 2. 收集文件 ──
    print(f"\n[2/5] 扫描文件: {SOURCE_DIR}")
    source = Path(SOURCE_DIR)
    docx_files = sorted(source.glob("*.docx"))

    if not docx_files:
        print(f"错误: 未找到 .docx 文件: {SOURCE_DIR}")
        sys.exit(1)

    if MAX_FILES:
        docx_files = docx_files[:MAX_FILES]

    print(f"  找到 {len(docx_files)} 个文件")

    # ── 3. 初始化读取器 ──
    reader = EnhancedDocxReader()
    speaker_extractor = SpeakerRoleExtractor()

    # ── 4. 逐文件处理 ──
    print(f"\n[3/5] 开始编码处理...")
    all_results = []       # 每条句子一个记录
    all_detailed = []      # 详细 trace（按文件）
    stats = {
        "total_sentences": 0,
        "total_coded": 0,
        "total_empty": 0,
        "total_files": 0,
        "total_interviewer_filtered": 0,
        "total_segments_raw": 0,
        "file_details": [],
    }

    coding_start = time.time()

    for file_idx, docx_path in enumerate(docx_files):
        fname = docx_path.name
        file_start = time.time()

        try:
            # 读取并标准化格式
            normalized_text = reader.read_docx(docx_path)

            # 提取受访者语句
            segments = speaker_extractor.extract_interviewee_sentences(
                normalized_text, return_metadata=True
            )

            # segments 可能是 list[dict] (with metadata) 或 list[str]
            stats["total_segments_raw"] += len(segments)

            # 分句并编码
            file_results = []
            for seg in segments:
                if isinstance(seg, dict):
                    text = seg.get("text", "")
                    speaker_label = seg.get("speaker_label", "")
                    confidence = seg.get("confidence", 0)
                    method = seg.get("method", "")
                else:
                    text = seg
                    speaker_label = ""
                    confidence = 1.0
                    method = ""

                # 二次分句（speaker extractor 可能返回长段落）
                sub_sentences = split_sentences(text)

                for sent in sub_sentences:
                    stats["total_sentences"] += 1
                    llm_code = coder.code_single(sent)

                    if not llm_code or llm_code == sent[:30]:
                        stats["total_empty"] += 1

                    stats["total_coded"] += 1

                    file_results.append({
                        "source_file": fname,
                        "sentence": sent,
                        "llm_code": llm_code,
                        "code_len": len(llm_code) if llm_code else 0,
                        "speaker_label": speaker_label,
                        "speaker_confidence": confidence,
                        "speaker_method": method,
                    })

            elapsed = time.time() - file_start
            stats["total_files"] += 1
            stats["file_details"].append({
                "file": fname,
                "sentences": len(file_results),
                "time": round(elapsed, 1),
            })

            all_results.extend(file_results)
            all_detailed.append({
                "file": fname,
                "sentences": len(file_results),
                "results": file_results,
            })

            # 进度
            if (file_idx + 1) % 5 == 0 or file_idx == 0:
                avg_time = (time.time() - coding_start) / (file_idx + 1)
                remaining = avg_time * (len(docx_files) - file_idx - 1)
                print(f"  [{file_idx+1}/{len(docx_files)}] {fname} "
                      f"({len(file_results)} 句, {elapsed:.1f}s) "
                      f"预计剩余 {remaining/60:.0f}min")

        except Exception as e:
            print(f"  [{file_idx+1}/{len(docx_files)}] {fname} 失败: {e}")
            import traceback
            traceback.print_exc()

    total_elapsed = time.time() - coding_start

    # ── 5. 质量报告 ──
    print(f"\n[4/5] 生成质量报告")
    print("=" * 70)
    print(f"处理完成: {stats['total_files']} 文件, {stats['total_sentences']} 句")
    print(f"总耗时: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")
    print(f"平均: {total_elapsed/stats['total_sentences']:.2f}s/句" if stats["total_sentences"] else "")

    # 编码长度统计
    code_lens = [r["code_len"] for r in all_results if r["code_len"] > 0]
    empty_codes = [r for r in all_results if r["code_len"] == 0]

    print(f"\n── 编码长度 ──")
    print(f"总编码数: {len(all_results)}")
    print(f"空编码: {len(empty_codes)} ({len(empty_codes)/len(all_results)*100:.1f}%)" if all_results else "N/A")
    if code_lens:
        print(f"平均长度: {sum(code_lens)/len(code_lens):.1f} 字")
        print(f"中位数: {sorted(code_lens)[len(code_lens)//2]} 字")
        print(f"最短: {min(code_lens)} 字, 最长: {max(code_lens)} 字")

        # 长度分布
        buckets = Counter()
        for l in code_lens:
            if l <= 4:
                buckets["1-4字"] += 1
            elif l <= 7:
                buckets["5-7字"] += 1
            elif l <= 10:
                buckets["8-10字"] += 1
            elif l <= 15:
                buckets["11-15字"] += 1
            elif l <= 20:
                buckets["16-20字"] += 1
            else:
                buckets[">20字"] += 1
        print(f"\n长度分布:")
        for k in ["1-4字", "5-7字", "8-10字", "11-15字", "16-20字", ">20字"]:
            count = buckets.get(k, 0)
            pct = count / len(code_lens) * 100
            bar = "█" * int(pct / 2)
            print(f"  {k:8s}: {count:5d} ({pct:5.1f}%) {bar}")

    # 编码多样性
    unique_codes = set(r["llm_code"] for r in all_results if r["code_len"] > 0)
    diversity = len(unique_codes) / len(all_results) * 100 if all_results else 0
    print(f"\n── 编码多样性 ──")
    print(f"唯一编码数: {len(unique_codes)}")
    print(f"多样性: {diversity:.1f}%")

    # 高频编码 top 20
    code_freq = Counter(r["llm_code"] for r in all_results if r["code_len"] > 0)
    print(f"\n高频编码 Top 20:")
    for code, count in code_freq.most_common(20):
        print(f"  [{count:4d}] {code}")

    # 说话人统计
    speaker_counts = Counter(r["speaker_label"] for r in all_results if r["speaker_label"])
    if speaker_counts:
        print(f"\n── 说话人分布 ──")
        for label, count in speaker_counts.most_common(10):
            print(f"  {label}: {count}")

    # ── 6. 保存结果 ──
    print(f"\n[5/5] 保存结果")

    # CSV（简化版）
    df = pd.DataFrame(all_results)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"  CSV: {OUTPUT_CSV} ({len(df)} 行)")

    # JSON（含统计）
    summary = {
        "model": MODEL_NAME,
        "source_dir": SOURCE_DIR,
        "total_files": stats["total_files"],
        "total_sentences": stats["total_sentences"],
        "total_coded": stats["total_coded"],
        "total_empty": stats["total_empty"],
        "empty_rate": len(empty_codes) / len(all_results) if all_results else 0,
        "avg_code_len": sum(code_lens) / len(code_lens) if code_lens else 0,
        "median_code_len": sorted(code_lens)[len(code_lens)//2] if code_lens else 0,
        "unique_codes": len(unique_codes),
        "diversity": diversity,
        "total_time": total_elapsed,
        "avg_time_per_sentence": total_elapsed / stats["total_sentences"] if stats["total_sentences"] else 0,
        "file_details": stats["file_details"],
        "top_codes": code_freq.most_common(30),
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  摘要: {OUTPUT_JSON}")

    # 详细结果
    with open(OUTPUT_DETAILED_JSON, "w", encoding="utf-8") as f:
        json.dump(all_detailed, f, ensure_ascii=False, indent=2)
    print(f"  详细: {OUTPUT_DETAILED_JSON}")

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
