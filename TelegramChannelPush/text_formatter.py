import re

# 用于将数字映射到Unicode上标字符
SUPERSCRIPT_MAP = {
    1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵',
    6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹'
}

def process_markdown_links_and_add_references(text: str):
    """
    处理文本中的Markdown链接，将其转换为带上标引用的格式，并在末尾附加引用列表。
    比如说把 "一些文本 [链接名称](链接地址) 更 多文本"
    转换为："一些文本 链接名称¹ 更 多文本"
    并在末尾追加 "\n\n¹:链接地址"
    """
    if not text:
        return text, ""

    matches = list(re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text))
    if not matches:
        return text, ""

    references_lines = []
    modified_text_parts = []
    current_pos = 0
    citation_count = 0

    for i, match in enumerate(matches):
        if citation_count >= len(SUPERSCRIPT_MAP): # 最多处理9个引用
            break
        
        link_text = match.group(1)
        link_url = match.group(2)
        
        # 添加匹配之前的部分
        modified_text_parts.append(text[current_pos:match.start()])
        
        citation_count += 1
        superscript = SUPERSCRIPT_MAP.get(citation_count, str(citation_count)) # 获取上标，如果超过9，则用普通数字
        
        # 添加带上标的链接文本
        modified_text_parts.append(link_text + superscript)
        
        references_lines.append(f"{superscript}:{link_url}")
        current_pos = match.end()

    # 添加最后一个匹配之后的部分
    modified_text_parts.append(text[current_pos:])
    
    final_text = "".join(modified_text_parts)
    references_string = "\n".join(references_lines)
    
    return final_text, references_string 