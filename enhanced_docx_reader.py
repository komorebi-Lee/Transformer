"""
增强的文档读取器 - 处理特殊格式的访谈文本

支持的格式：
1. 时间戳和说话人在单独段落
2. 时间戳在单独段落，问答在同一段落
3. 标准格式（说话人: 内容）
"""

import re
from typing import List, Dict
from docx import Document


class EnhancedDocxReader:
    """增强的 docx 读取器"""
    
    def __init__(self):
        self.time_pattern = re.compile(r'^\s*[●•]?\s*\d{2}:\d{2}')
        self.speaker_pattern = re.compile(r'说话人\d+')
    
    def read_docx(self, file_path: str) -> str:
        """
        读取 docx 文件并转换为标准格式
        
        Returns:
            标准格式的文本（说话人: 内容）
        """
        doc = Document(file_path)
        
        # 提取所有段落
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        # 检测格式
        format_type = self._detect_format(paragraphs)
        
        print(f"检测到格式类型: {format_type}")
        
        # 根据格式转换
        if format_type == 'format1':
            return self._convert_format1(paragraphs)
        elif format_type == 'format2':
            return self._convert_format2(paragraphs)
        else:
            return '\n'.join(paragraphs)
    
    def _detect_format(self, paragraphs: List[str]) -> str:
        """检测文档格式"""
        # 检查前30个段落
        sample = paragraphs[:30]
        
        # 格式1: 时间戳 + 说话人标签在单独段落
        # 例如: "00:00 说话人1" 或 "里弄管家1:" 或 "采访者:"
        format1_count = 0
        speaker_label_pattern = re.compile(
            r'^(说话人\d+|里弄管家\d+|采访者|访谈员|受访者|游客\d+|老师\d*|主持人|记者)\s*[:：]\s*$'
        )
        
        for para in sample:
            # 检查是否包含说话人标签（单独一行）
            if (self.time_pattern.match(para) and self.speaker_pattern.search(para)) or \
               speaker_label_pattern.match(para.strip()):
                format1_count += 1
        
        if format1_count >= 3:
            return 'format1'
        
        # 格式2: 时间戳在单独段落，问答在同一段落
        # 例如: "● 00:01" 后面跟 "问题？回答。"
        format2_count = 0
        for para in sample:
            if self.time_pattern.match(para) and len(para) < 20:
                format2_count += 1
        
        if format2_count >= 3:
            return 'format2'
        
        return 'standard'
    
    def _convert_format1(self, paragraphs: List[str]) -> str:
        """
        转换格式1: 时间戳 + 说话人在单独段落
        
        输入:
            00:00 说话人1
            我是本厂的老员工。
            00:03 说话人2
            您也是本厂的老员工。
        
        或:
            里弄管家1:
            事情在这方面，我们不管是从硬件还是软件方面...
            采访者:
            老师，我们针对一些问题整理了一下...
        
        输出:
            说话人1: 我是本厂的老员工。
            说话人2: 您也是本厂的老员工。
        """
        result = []
        current_speaker = None
        
        # 扩展的说话人标签模式
        speaker_label_pattern = re.compile(
            r'^(说话人\d+|里弄管家\d+|采访者|访谈员|受访者|游客\d+|老师\d*|主持人|记者)\s*[:：]?\s*$'
        )
        
        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            
            # 检查是否是时间戳 + 说话人标签
            if self.time_pattern.match(para) and self.speaker_pattern.search(para):
                # 提取说话人
                match = self.speaker_pattern.search(para)
                current_speaker = match.group()
                i += 1
                
                # 收集该说话人的内容（直到下一个时间戳+说话人）
                content_parts = []
                while i < len(paragraphs):
                    next_para = paragraphs[i]
                    # 如果遇到下一个时间戳+说话人，停止
                    if self.time_pattern.match(next_para) and self.speaker_pattern.search(next_para):
                        break
                    # 跳过纯时间戳
                    if not self.time_pattern.match(next_para):
                        content_parts.append(next_para)
                    i += 1
                
                # 组合内容
                if content_parts:
                    content = ' '.join(content_parts)
                    result.append(f"{current_speaker}: {content}")
            
            # 检查是否是单独的说话人标签（如"里弄管家1:"）
            elif speaker_label_pattern.match(para):
                current_speaker = para.strip().rstrip(':：')
                i += 1
                
                # 收集该说话人的内容（直到下一个说话人标签）
                content_parts = []
                while i < len(paragraphs):
                    next_para = paragraphs[i]
                    # 如果遇到下一个说话人标签，停止
                    if speaker_label_pattern.match(next_para):
                        break
                    # 如果遇到时间戳+说话人，停止
                    if self.time_pattern.match(next_para) and self.speaker_pattern.search(next_para):
                        break
                    # 跳过纯时间戳和元数据
                    if not self.time_pattern.match(next_para) and len(next_para) > 5:
                        content_parts.append(next_para)
                    i += 1
                
                # 组合内容
                if content_parts:
                    content = ' '.join(content_parts)
                    result.append(f"{current_speaker}: {content}")
            else:
                i += 1
        
        return '\n'.join(result)
    
    def _convert_format2(self, paragraphs: List[str]) -> str:
        """
        转换格式2: 时间戳在单独段落，问答在同一段落
        
        输入:
            ● 00:01
            您是哪一年来景德镇的？我是二三年来的景德镇。
            ● 00:04
            那之前是学什么专业？做什么？
            ● 00:07
            我是工艺美术专业，然后毕业就到这边来了。
        
        输出:
            采访者: 您是哪一年来景德镇的？
            受访者: 我是二三年来的景德镇。
            采访者: 那之前是学什么专业？做什么？
            受访者: 我是工艺美术专业，然后毕业就到这边来了。
        """
        result = []
        
        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            
            # 跳过时间戳
            if self.time_pattern.match(para) and len(para) < 20:
                i += 1
                continue
            
            # 跳过元数据
            if any(x in para for x in ['时间:', '主题:', '书面化润色版']):
                i += 1
                continue
            
            # 处理内容段落
            # 按问号分割（问答可能在同一段落）
            if '？' in para or '?' in para:
                # 分割问答
                parts = re.split(r'([？?])', para)
                
                j = 0
                while j < len(parts):
                    part = parts[j].strip()
                    if not part:
                        j += 1
                        continue
                    
                    # 如果是问号
                    if part in ['？', '?']:
                        j += 1
                        continue
                    
                    # 检查下一个是否是问号
                    if j + 1 < len(parts) and parts[j + 1] in ['？', '?']:
                        # 这是问句
                        question = part + parts[j + 1]
                        result.append(f"采访者: {question}")
                        j += 2
                    else:
                        # 这是回答（问号后的内容）
                        if len(part) >= 5:
                            result.append(f"受访者: {part}")
                        j += 1
            else:
                # 没有问号，根据内容特征判断
                # 包含第一人称 = 受访者
                if any(x in para for x in ['我是', '我们', '我觉得', '我认为', '我的']):
                    result.append(f"受访者: {para}")
                # 短句 = 采访者
                elif len(para) < 30:
                    result.append(f"采访者: {para}")
                # 长句 = 受访者
                else:
                    result.append(f"受访者: {para}")
            
            i += 1
        
        return '\n'.join(result)


# ============================================================
# 测试
# ============================================================

if __name__ == '__main__':
    reader = EnhancedDocxReader()
    
    print("=" * 60)
    print("测试文件1: 陶阳里 非遗手艺人 9.docx")
    print("=" * 60)
    
    file1 = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人 9.docx'
    text1 = reader.read_docx(file1)
    
    lines1 = text1.split('\n')
    print(f"\n转换后共 {len(lines1)} 行")
    print("\n前10行:")
    for i, line in enumerate(lines1[:10]):
        print(f"{i+1}. {line[:80]}")
    
    print("\n" + "=" * 60)
    print("测试文件2: 陶溪川 景漂6")
    print("=" * 60)
    
    file2 = r'C:\Users\33288\Downloads\新文本\润色后文件\陶溪川 景漂6 广州美术学院_润色版.docx'
    text2 = reader.read_docx(file2)
    
    lines2 = text2.split('\n')
    print(f"\n转换后共 {len(lines2)} 行")
    print("\n前10行:")
    for i, line in enumerate(lines2[:10]):
        print(f"{i+1}. {line[:80]}")
