"""测试直接 completion 模式（非 chat）来看是否是模板问题。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from llama_cpp import Llama

MODEL = 'local_models/llm_first_level_coder/qwen2.5-0.5b-coding-Q4_K_M.gguf'

llm = Llama(model_path=MODEL, n_gpu_layers=-1, verbose=False)
print(f'n_ctx_train: {llm.n_ctx_train()}')

# 测试句子
sentences = [
    '我是学工艺美术的，毕业就来了景德镇。',
    '对，我是学原画设计。',
    '我觉得这里氛围挺好的。',
]

SYSTEM = '只输出一个短语作为一阶编码，不超过15字。不输出分号。不输出解释。不输出多个编码。用受访者原话中的词汇，保留主体-动作-对象。'

for sent in sentences:
    # 方式1: Qwen chat template (completion mode)
    prompt = f'<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\n{sent}<|im_end|>\n<|im_start|>assistant\n'
    output = llm(prompt, max_tokens=50, temperature=0.1, top_p=0.9)
    result = output['choices'][0]['text'].strip()
    print(f'\n原文: {sent}')
    print(f'编码: {result[:100]}')
