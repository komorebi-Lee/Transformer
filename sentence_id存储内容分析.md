# sentence_id 存储的内容分析

## 答案

**`sentence_id` 存储的是不带字母的数字编号，如 `"1"`, `"2"`, `"3"`**

## 详细分析

### 1. sentence_id 的来源

**位置**：`data_processor.py` 第607-610行

```python
sentence_id = self._lookup_sentence_number(clean_sentence, sentence_number_lookup or [])
if sentence_id:
    sentence_info['sentence_id'] = sentence_id
    sentence_info['code_id'] = sentence_id
```

### 2. _lookup_sentence_number 函数（第537-547行）

```python
def _lookup_sentence_number(self, sentence: str, sentence_number_lookup: List[Tuple[int, str]]) -> str:
    target = self._normalize_for_sentence_lookup(sentence)
    if not target:
        return ''
    for number, numbered_sentence in sentence_number_lookup or []:
        if target == numbered_sentence:
            return str(number)  # ← 返回 str(number)，如 "1", "2", "3"
    for number, numbered_sentence in sentence_number_lookup or []:
        if len(target) >= 8 and (target in numbered_sentence or numbered_sentence in target):
            return str(number)  # ← 返回 str(number)
    return ''
```

**关键**：返回的是 `str(number)`，这是一个**纯数字字符串**。

### 3. sentence_number_lookup 的构建（第513-535行）

```python
def _build_sentence_number_lookup(self, text: str) -> List[Tuple[int, str]]:
    # ... 分割句子 ...
    
    lookup = []
    for sentence in sentences:
        self._processing_sentence_counter = getattr(self, '_processing_sentence_counter', 0) + 1
        lookup.append((self._processing_sentence_counter, self._normalize_for_sentence_lookup(sentence)))
    return lookup
```

**结构**：`List[Tuple[int, str]]`
- 第一个元素：`int` 类型的计数器（1, 2, 3, ...）
- 第二个元素：标准化后的句子文本

**示例**：
```python
[
    (1, "这是第一个句子"),
    (2, "这是第二个句子"),
    (3, "这是第三个句子"),
    ...
]
```

### 4. 对比：sentence_id vs code_id

| 字段 | 存储内容 | 示例 | 来源 |
|------|---------|------|------|
| `sentence_id` | 纯数字字符串 | `"1"`, `"2"`, `"3"` | `_lookup_sentence_number` |
| `code_id` | 纯数字字符串 | `"1"`, `"2"`, `"3"` | 与 `sentence_id` 相同 |
| `text_number` | 整数或None | `123`, `456`, `None` | `_find_text_number` |

**注意**：
- `sentence_id` 和 `code_id` 是**相同的值**（第610行）
- 它们都是**纯数字字符串**，不是 `"A01"` 这种格式

### 5. 一阶编码标识符（如 A01）的来源

**一阶编码标识符（如 A01, A02）是在编码生成阶段由 `EnhancedCodingGenerator` 创建的，不是 `sentence_id`！**

**位置**：`enhanced_coding_generator.py`

```python
# 生成一阶编码时
code_id = f"A{str(i+1).zfill(2)}"  # 生成 A01, A02, A03, ...
```

### 6. 数据结构对比

**sentence_info（在 data_processor 中）**：
```python
{
    'content': '句子内容',
    'sentence_id': '123',      # ← 纯数字字符串
    'code_id': '123',          # ← 与 sentence_id 相同
    'text_number': 456,        # ← TextNumbering 编号（整数）
    ...
}
```

**first_content（在编码生成后）**：
```python
{
    'code_id': 'A01',          # ← 一阶编码标识符（字母+数字）
    'content': '编码内容',
    'sentence_details': [
        {
            'content': '句子内容',
            'sentence_id': '123',  # ← 纯数字字符串
            'code_id': '123',      # ← 与 sentence_id 相同
            'text_number': 456,    # ← TextNumbering 编号
            ...
        }
    ]
}
```

**注意**：
- 外层的 `code_id` 是一阶编码标识符（`"A01"`）
- 内层 `sentence_details` 的 `code_id` 是句子编号（`"123"`）

### 7. 在 update_coding_tree 中的使用

**第2234-2237行**：
```python
# 从sentence_details提取
if not all_ids and sentence_details:
    for s in sentence_details:
        if isinstance(s, dict) and s.get('sentence_id'):
            all_ids.add(str(s.get('sentence_id')))  # ← 获取纯数字字符串
```

**第5828-5838行（show_sentence_details_dialog）**：
```python
# 获取实际的句子编号
first_code_number = first_detail.get('code_id', '') or first_detail.get('sentence_id', '')

# 如果获取到的是编码标识符（如A01），则从关联编号中获取
if first_code_number and not first_code_number.isdigit():  # ← 检查是否是纯数字
    if associated_numbers_list:
        first_code_number = associated_numbers_list[0]
```

**逻辑**：
- 如果 `code_id` 或 `sentence_id` 是纯数字（如 `"123"`），直接使用
- 如果是编码标识符（如 `"A01"`），则从关联编号列表获取

## 总结

### ✅ sentence_id 存储的是纯数字字符串

**示例**：
- ✅ `"1"`, `"2"`, `"3"`, `"123"`, `"456"`
- ❌ 不是 `"A01"`, `"A02"`, `"B01"`

### 🔍 三种编号的区别

| 编号类型 | 格式 | 示例 | 用途 |
|---------|------|------|------|
| **sentence_id** | 纯数字字符串 | `"1"`, `"123"` | 句子的顺序编号 |
| **text_number** | 整数 | `123`, `456` | TextNumbering 编号（用于定位） |
| **code_id（一阶）** | 字母+数字 | `"A01"`, `"A02"` | 一阶编码标识符 |

### 🎯 关键点

1. `sentence_id` 是**句子的顺序编号**，从1开始递增
2. `text_number` 是**TextNumbering 编号**，用于在原文中定位
3. 两者**可能不同**：
   - `sentence_id` 是处理过程中的计数器
   - `text_number` 是原文中的实际编号
4. 编码树第5列应该显示 `text_number`，而不是 `sentence_id`

---

**结论**：`sentence_id` 存储的是不带字母的纯数字字符串（如 `"1"`, `"123"`），不是一阶编码标识符（如 `"A01"`）。
