"""快速验证: 对前2个文件测试 LLM 编码流程。"""
import sys, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from llm_first_level_coder import LLMFirstLevelCoder
from enhanced_docx_reader import EnhancedDocxReader
from speaker_role_extractor import SpeakerRoleExtractor

MODEL_PATH = "local_models/llm_first_level_coder/qwen2.5-0.5b-coding-Q4_K_M.gguf"
SOURCE_DIR = r"D:\c盘\新文本\润色后文件"

print("加载模型...")
t0 = time.time()
coder = LLMFirstLevelCoder(model_path=MODEL_PATH, n_gpu_layers=-1, temperature=0.1, verbose=False)
print(f"模型加载: {time.time()-t0:.1f}s")

reader = EnhancedDocxReader()
extractor = SpeakerRoleExtractor()

files = sorted(Path(SOURCE_DIR).glob("*.docx"))[:2]

for fp in files:
    print(f"\n{'='*60}")
    print(f"文件: {fp.name}")
    t1 = time.time()

    text = reader.read_docx(fp)
    print(f"读取: {len(text)} 字符, 格式检测完成")

    segs = extractor.extract_interviewee_sentences(text, return_metadata=True)
    print(f"提取: {len(segs)} 个受访者段落")

    # 只编码前5句作为测试
    coded = 0
    for seg in segs[:5]:
        if isinstance(seg, dict):
            sent = seg["text"]
        else:
            sent = seg

        if len(sent) < 8:
            continue

        code = coder.code_single(sent)
        coded += 1
        print(f"  [{coded}] 原文: {sent[:60]}...")
        print(f"      编码: {code}")

    print(f"耗时: {time.time()-t1:.1f}s")
