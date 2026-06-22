"""LLM 一阶编码推理模块。

使用 llama-cpp-python 加载 GGUF 模型，支持 GPU/CPU 自动切换。
"""

import json
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

INSTRUCTION = (
    "你是扎根理论编码助手。"
    "任务：根据访谈文本生成高质量一阶编码（Level 1），严格贴近原文。"
    "规则："
    "1. 保留主体、动作、对象"
    "2. 禁止心理推断、解释性词汇、抽象概念和理论名词"
    "3. 优先使用原文词汇"
    "输入：访谈文本"
    "输出：只输出一条一阶编码。不超过10字。不输出分号。不输出斜杠。不输出多个编码。不输出解释。"
)


class LLMFirstLevelCoder:
    """LLM 一阶编码器。

    委托 llama-cpp-python 加载 GGUF 模型进行推理。
    GPU 可用时自动 offload 到 CUDA，否则回退 CPU。
    """

    def __init__(
        self,
        model_path: str,
        n_gpu_layers: int = -1,
        n_ctx: int = 512,
        temperature: float = 0.1,
        top_p: float = 0.9,
        max_tokens: int = 48,
        repeat_penalty: float = 1.3,
        verbose: bool = False,
    ):
        """
        Args:
            model_path: GGUF 模型文件路径
            n_gpu_layers: offload 到 GPU 的层数，-1=全部，0=仅CPU
            n_ctx: 上下文长度
            temperature: 采样温度（低=稳定）
            top_p: nucleus sampling
            max_tokens: 最大生成token数
            repeat_penalty: 重复惩罚，>1 抑制小模型退化式复读
            verbose: llama.cpp 详细输出
        """
        # ggml-cuda.dll 依赖 CUDA 运行时（cudart/cublas），这些 DLL 随 torch 分发。
        # 必须先完整 import torch（把 CUDA DLL 载入进程并注册搜索路径），
        # 否则 Windows 下 llama.dll 加载会因找不到依赖而失败。
        import torch  # noqa: F401

        from llama_cpp import Llama

        self.model = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=verbose,
        )
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.repeat_penalty = repeat_penalty
        self.n_gpu_layers = n_gpu_layers

        gpu_info = f"{n_gpu_layers} layers on GPU" if n_gpu_layers != 0 else "CPU only"
        logger.info(f"LLMFirstLevelCoder loaded: {model_path} ({gpu_info})")

    def code_single(self, sentence: str) -> str:
        """对单句生成一阶编码。

        Args:
            sentence: 原始句子

        Returns:
            一阶编码文本，如果解析失败则返回原始LLM输出
        """
        messages = [
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": sentence},
        ]

        response = self.model.create_chat_completion(
            messages=messages,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            repeat_penalty=self.repeat_penalty,
        )

        raw_output = response["choices"][0]["message"]["content"]
        return self._parse_response(raw_output, sentence)

    def code(self, sentences: List[str]) -> List[Dict]:
        """批量编码。

        Args:
            sentences: 原始句子列表

        Returns:
            [{"code": "...", "sentence": "..."}, ...]
        """
        results = []
        for sent in sentences:
            code = self.code_single(sent)
            results.append({"code": code, "sentence": sent})
        return results

    @staticmethod
    def _parse_response(response: str, original_sentence: str) -> str:
        """从LLM响应中提取一阶编码文本。

        模型直接输出编码文本，清理掉可能混入的额外内容。
        """
        # 取响应文本，去首尾空白
        code = response.strip()

        # 去掉可能混入的引号包裹
        if code.startswith('"') and code.endswith('"'):
            code = code[1:-1]
        if code.startswith("'") and code.endswith("'"):
            code = code[1:-1]

        # 去掉可能残留的 "一阶编码：" 前缀
        code = re.sub(r'^一阶编码[：:]\s*', '', code)

        # 如果有多行，只取第一行有效内容
        lines = [l.strip() for l in code.split('\n') if l.strip()]
        if lines:
            code = lines[0]

        # 合格的一阶编码不含空格；模型跑飞时会用空格分隔多个子句/数字，
        # 取首个空白前的片段，几乎总是有效部分（如"江西吉安籍贯 2019年考入…"→"江西吉安籍贯"）
        code = re.split(r'[\s　]+', code, maxsplit=1)[0].strip()

        # 折叠退化式复读（小模型在长输出时易陷入循环）
        code = LLMFirstLevelCoder._collapse_repetition(code)

        # 跑飞输出（短输入幻觉、拖尾分析、句中句号）截断到前面的干净核心
        code = LLMFirstLevelCoder._truncate_runaway(code)

        # 去掉"且/并"连接的同义复述尾句（如"不同且存在差异"→"不同"）
        code = LLMFirstLevelCoder._drop_redundant_clause(code)

        # 去掉句尾标点与冗余的解释性尾巴，贴近参考编码风格
        code = LLMFirstLevelCoder._strip_trailing_noise(code)

        return code

    # 模型习惯在编码末尾追加的元叙述/解释性尾巴，参考编码从不使用，可安全剥离
    _TRAILING_FILLERS = (
        "的背景故事", "背景故事",
        "的愿望强烈", "愿望强烈",
        "以满足需求",
    )
    _TRAILING_PUNCT = "。．.，,、；;：:！!？?…　 "

    # 近义词组：编码内若"且/并"前后各含同组的词，尾句视为同义复述
    _SYNONYM_GROUPS = (
        ("不同", "差异", "区别", "分歧", "不一致", "不一样", "差别"),
        ("相同", "一致", "相似", "类似", "一样"),
        ("明显", "突出", "显著", "强烈", "突显"),
        ("重要", "关键", "核心"),
        ("提升", "提高", "增强", "加强"),
        ("减少", "降低", "下降"),
    )

    @staticmethod
    def _drop_redundant_clause(text: str) -> str:
        """删掉"且/并/又"连接的同义复述尾句。

        如"审美观念不同且存在差异"→"审美观念不同"（不同≈差异，尾句仅换说法重复）。
        仅当头尾两句包含同一同义词组的词时才删，避免误删表达不同概念的并列句。
        """
        m = re.search(r'[且并又]', text)
        if not m:
            return text
        head, tail = text[:m.start()], text[m.end():]
        if len(head) < 4 or not tail:
            return text
        for group in LLMFirstLevelCoder._SYNONYM_GROUPS:
            if any(w in head for w in group) and any(w in tail for w in group):
                return head
        return text

    # 一阶编码绝不应包含的二阶/解释/元叙述词；出现即视为跑飞，从此处截断
    _DRIFT_MARKERS = (
        "受访者", "一阶编码", "二阶", "三阶", "主题", "证据", "数据来源",
        "编码逻辑", "认知偏差", "刻板印象", "企业应", "消费者参与度",
        "建议", "佐证", "范畴", "归类", "战略实施", "经验来源", "背景信息",
    )

    @staticmethod
    def _truncate_runaway(text: str) -> str:
        """删掉跑飞的幻觉垃圾尾巴，保留前面的干净核心。

        触发信号：比率数字串(如 2/3、10:9)、句中句号、二阶/解释性漂移词。
        在最早出现的信号处切断（保留至少4字前缀）。这是删幻觉，不是按长度截断——
        合法但偏长的编码不会被砍（长度问题靠生成端解决，不靠硬截断）。
        注意：不误伤"35元/个"这类单价（斜杠前是汉字而非数字）。
        """
        cuts = []
        m = re.search(r'\d+\s*[/:：]\s*\d+', text)
        if m:
            cuts.append(m.start())
        p = text.find('。')
        if p >= 0:
            cuts.append(p)
        for mark in LLMFirstLevelCoder._DRIFT_MARKERS:
            i = text.find(mark)
            if i >= 0:
                cuts.append(i)
        cuts = [c for c in cuts if c >= 4]
        if cuts:
            text = text[:min(cuts)]
        return text.strip()

    @staticmethod
    def _strip_trailing_noise(text: str) -> str:
        """去掉句尾标点和冗余的解释性尾巴。

        仅在剥离后仍保留 >=4 字时生效，避免把短编码削没。
        """
        prev = None
        while text != prev:
            prev = text
            text = text.rstrip(LLMFirstLevelCoder._TRAILING_PUNCT)
            for filler in LLMFirstLevelCoder._TRAILING_FILLERS:
                if text.endswith(filler) and len(text) - len(filler) >= 4:
                    text = text[: -len(filler)]
                    break
        return text.rstrip(LLMFirstLevelCoder._TRAILING_PUNCT)

    @staticmethod
    def _collapse_repetition(text: str) -> str:
        """折叠连续重复的字串片段。

        小模型在生成较长输出时会陷入复读循环（如"远超对手远超对手…"）。
        检测连续重复 3 次及以上的单元，保留前缀加一个单元后截断。
        仅对长文本生效，避免误伤正常短编码。
        """
        if len(text) <= 20:
            return text
        for n in range(2, 13):
            i = 0
            while i + n <= len(text):
                unit = text[i:i + n]
                reps = 1
                j = i + n
                while text[j:j + n] == unit:
                    reps += 1
                    j += n
                if reps >= 3:
                    return text[:i + n]
                i += 1
        return text

    @staticmethod
    def _build_prompt(sentence: str) -> tuple:
        """构建prompt（用于测试）。"""
        return INSTRUCTION, sentence
