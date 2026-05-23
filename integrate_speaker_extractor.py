"""
修改 identify_interview_paragraphs 方法，支持精准提取
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在 identify_interview_paragraphs 方法开头添加精准提取逻辑
old_method_start = '''    def identify_interview_paragraphs(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """智能识别采访段落，区分采访人和受访人"""
        paragraphs = []'''

new_method_start = '''    def identify_interview_paragraphs(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """智能识别采访段落，区分采访人和受访人（支持精准提取）"""
        
        # 如果启用了精准提取，使用 SpeakerRoleExtractor
        if self.use_advanced_extraction and self.speaker_extractor:
            return self._identify_paragraphs_advanced(content, filename)
        
        # 否则使用原有逻辑
        paragraphs = []'''

if old_method_start in content:
    content = content.replace(old_method_start, new_method_start)
    print('OK: Added advanced extraction support')
else:
    print('WARN: Method start not found')

# 在 identify_interview_paragraphs 方法后添加新方法
# 找到 detect_speaker 方法的位置
insert_pos = content.find('    def detect_speaker(self, line: str) -> Optional[str]:')

if insert_pos > 0:
    # 在 detect_speaker 前插入新方法
    new_method = '''
    def _identify_paragraphs_advanced(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """使用 SpeakerRoleExtractor 进行精准提取"""
        try:
            # 使用 SpeakerRoleExtractor 提取受访者语句
            interviewee_segments = self.speaker_extractor.extract_interviewee_sentences(
                content,
                return_metadata=True
            )
            
            # 转换为 data_processor 的格式
            paragraphs = []
            for i, seg in enumerate(interviewee_segments):
                paragraphs.append({
                    'speaker': 'respondent',  # 只返回受访者
                    'content': seg['text'],
                    'start_line': i,
                    'end_line': i + 1,
                    'filename': filename,
                    'confidence': seg.get('confidence', 1.0),
                    'method': seg.get('method', 'advanced')
                })
            
            logger.info(f"精准提取: {filename} - {len(paragraphs)} 个受访者段落")
            return paragraphs
            
        except Exception as e:
            logger.error(f"精准提取失败，降级到原有逻辑: {e}")
            # 降级到原有逻辑
            self.use_advanced_extraction = False
            return self._identify_paragraphs_simple(content, filename)
    
    def _identify_paragraphs_simple(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """原有的简单段落识别（兼容）"""
        paragraphs = []
        lines = content.split('\\n')

        current_paragraph = []
        current_speaker = None
        paragraph_start_line = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_paragraph and current_speaker:
                    # 保存当前段落
                    paragraph_text = '\\n'.join(current_paragraph)
                    paragraphs.append({
                        'speaker': current_speaker,
                        'content': paragraph_text,
                        'start_line': paragraph_start_line,
                        'end_line': i,
                        'filename': filename
                    })
                    current_paragraph = []
                    current_speaker = None
                continue

            # 检测说话人
            speaker = self.detect_speaker(line)

            if speaker and current_speaker != speaker:
                # 保存上一个段落
                if current_paragraph and current_speaker:
                    paragraph_text = '\\n'.join(current_paragraph)
                    paragraphs.append({
                        'speaker': current_speaker,
                        'content': paragraph_text,
                        'start_line': paragraph_start_line,
                        'end_line': i,
                        'filename': filename
                    })

                # 开始新段落
                current_paragraph = [line]
                current_speaker = speaker
                paragraph_start_line = i
            else:
                current_paragraph.append(line)

        # 添加最后一个段落
        if current_paragraph and current_speaker:
            paragraph_text = '\\n'.join(current_paragraph)
            paragraphs.append({
                'speaker': current_speaker,
                'content': paragraph_text,
                'start_line': paragraph_start_line,
                'end_line': len(lines),
                'filename': filename
            })

        return paragraphs

'''
    
    content = content[:insert_pos] + new_method + content[insert_pos:]
    print('OK: Added new methods')
else:
    print('WARN: Insert position not found')

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
