import re

# def remove_chinese(text):
#     # 匹配所有中文字符（Unicode范围：\u4e00-\u9fff）
#     pattern = re.compile('[\u4e00-\u9fff]+')
#     return pattern.sub('', text)

def remove_chinese(text):
    return ''.join(
        char for char in text 
        if not ('\u4e00' <= char <= '\u9fff')
    )