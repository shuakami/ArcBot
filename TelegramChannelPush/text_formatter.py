import re
from typing import List, Tuple, Optional, Any

SUPERSCRIPT_MAP = {      # 1-9 → Unicode 上标
    1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵",
    6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹"
}

def _extract_entity_links(
    txt: str, entities: Optional[List[Any]]
) -> List[Tuple[int, int, str, str]]:
    """从 Telegram MessageEntityTextUrl 解析链接"""
    if not entities:
        return []
    out: List[Tuple[int, int, str, str]] = []
    for ent in entities:
        if hasattr(ent, "url") and hasattr(ent, "offset") and hasattr(ent, "length"):
            off: int = ent.offset  # type: ignore
            length: int = ent.length  # type: ignore
            out.append((off, off + length, txt[off:off + length], ent.url))  # type: ignore
    return out

def _should_skip(link_txt: str, link_url: str, removal_kw: List[str]) -> bool:
    """
    判定该链接是否应丢弃：
      • 链接文本为空白
      • URL 属于 t.me / telegram.me
      • link_txt 或 link_url 含任意过滤关键词
    """
    if not link_txt.strip():
        return True
    if "t.me/" in link_url or "telegram.me/" in link_url:
        return True
    if any(kw in link_txt or kw in link_url for kw in removal_kw):
        return True
    return False

# ────────────────────────── 对外主函数 ──────────────────────────
def process_markdown_links_and_add_references(
    text: str,
    *,
    entities: Optional[List[Any]] = None,
    removal_strings: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    返回 `(正文, 引用块)`；若无链接，引用块为空串。
    """
    if not text:
        return text, ""

    removal_kw = removal_strings or []

    # 1️⃣ 预先剔除正文里的关键词（如“投稿”/“频道”）
    for kw in removal_kw:
        text = text.replace(kw, "")

    # 2️⃣ 收集所有链接
    links = _extract_entity_links(text, entities)
    if not links:
        return text.strip(), ""

    # 3️⃣ 过滤、去重
    uniq: List[Tuple[int, int, str, str]] = []
    spans = set()
    for start, end, ltxt, lurl in sorted(links, key=lambda x: x[0]):
        if (start, end) in spans:
            continue
        if _should_skip(ltxt, lurl, removal_kw):
            continue
        uniq.append((start, end, ltxt, lurl))
        spans.add((start, end))

    if not uniq:
        return text.strip(), ""

    # 4️⃣ 构造正文 + 引用
    body_parts: List[str] = []
    refs: List[str] = []
    pos = 0
    for idx, (s, e, ltxt, lurl) in enumerate(uniq[:9], start=1):
        body_parts.append(text[pos:s])
        sup = SUPERSCRIPT_MAP[idx]
        body_parts.append(f"{ltxt}{sup}")
        refs.append(f"{sup}:{lurl}")
        pos = e
    body_parts.append(text[pos:])

    body = "".join(body_parts)

    # 5️⃣ 收尾：压缩杂行距 & 去掉 superscript 前多余空白
    body = re.sub(r"[ \t]*\n+[ \t]*([¹²³⁴⁵⁶⁷⁸⁹])", r"\1", body)  # 换行→贴前面
    body = re.sub(r"\n{3,}", "\n\n", body)                          # >2 连续行 → 2 行
    body = body.strip()

    reference_block = "\n".join(refs)
    return body, reference_block
