from io import BytesIO
from pathlib import Path

SUPPORTED_SUFFIXES = {".md", ".txt", ".markdown", ".pdf", ".docx"}

def _clean(text: str) -> str:
    """清洗：合并多余空行、去除首尾空白。
    有些 md 文件复制粘贴出来，会有一大堆空行，向量化之前要压缩，减少无效 chunk。
    """
    import re
    # 把连续3个及以上换行，替换成2个换行
    text = re.sub(r"\n{3,}","\n\n",text)
    # 去掉字符串最开头、最末尾的空格、换行
    return text.strip()

def _decode_text(content:bytes)->str:
   for enc in ("utf-8","gbk"):
       try:
           # .decode(编码)转文本
           text = content.decode(enc)
           return _clean(text)
       except UnicodeDecodeError:
           continue

   return _clean(content.decode("utf-8",errors="replace"))


def _extract_pdf(content):
    """PDF 提取：pdfplumber 逐页取文本，拼接。"""
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("PDF 解析依赖未安装，请运行: uv sync")
    pages_text = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
    full = "\n\n".join(pages_text)
    if not full.strip():
        raise ValueError("PDF 未提取到文本（可能是扫描件/图片型 PDF，暂不支持 OCR）")
    return _clean(full)


def _extract_docx(content):
    """Word 提取：python-docx 取段落文本（含表格）。"""
    try:
        from docx import Document
    except ImportError:
        raise ValueError("Word 解析依赖未安装，请运行: uv sync")

    doc = Document(BytesIO(content))
    # doc.paragraphs：word 所有普通段落
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    # 解析表格
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                # 姓名 | 张三 | 男
                parts.append(" | ".join(cells))
    full = "\n".join(parts)
    if not full.strip():
        raise ValueError("Word 文档未提取到文本")
    return _clean(full)

def extract_text(filename:str,content:bytes) ->str:
    """从上传文件提取纯文本。"""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"不支持的文件类型 {suffix}，支持：{sorted(SUPPORTED_SUFFIXES)}")

    if suffix in (".md", ".txt", ".markdown"):
        return _decode_text(content)

    if suffix == ".pdf":
        return _extract_pdf(content)

    if suffix == ".docx":
        return _extract_docx(content)

    raise ValueError(f"未处理的文件类型 {suffix}")