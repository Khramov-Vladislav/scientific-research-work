from markitdown import MarkItDown

markitdown = MarkItDown()
result = markitdown.convert("main.pdf")

with open("main.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)

