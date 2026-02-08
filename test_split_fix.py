
import re

def split_into_sentences(text):
    sentences = re.split(r'([。！？!?])', text)
    result = []
    
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)
            
    if len(sentences) % 2 == 1:
        last_part = sentences[-1].strip()
        if last_part:
            # FIX: Always append the last part as a new sentence instead of merging
            result.append(last_part)
                
    return result

text1 = "句子1。句子2"
print(f"--- Text: {text1} ---")
res1 = split_into_sentences(text1)
print(f"Result: {res1}")

text2 = "句子1。句子2。"
print(f"--- Text: {text2} ---")
res2 = split_into_sentences(text2)
print(f"Result: {res2}")

text3 = "句子1\n句子2"
print(f"--- Text: {text3} ---")
res3 = split_into_sentences(text3)
print(f"Result: {res3}")
