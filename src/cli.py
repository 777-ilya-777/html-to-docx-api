
import argparse
from html.parser import HTMLParser
from pathlib import Path

from docx import Document


HEADING_TAGS = {f"h{level}" for level in range(1, 7)}
FORMAT_TAGS = {"strong", "b", "em", "i", "u"}
PARAGRAPH_TAGS = {"p", "div", "li"}
LIST_STYLES = {"ul": "List Bullet", "ol": "List Number"}


class HTMLToDOCXParser(HTMLParser):
    """Преобразует HTML в документ DOCX."""

    def __init__(self, document):
        """Инициализирует HTML-парсер."""
        super().__init__()
        self.document = document
        self.in_body = False
        self.paragraph = None
        self.heading_level = None
        self.list_type = None
        self.in_list_item = False
        self.formats = []

    def handle_starttag(self, tag, attrs):
        """Обрабатывает открывающие HTML-теги."""
        if tag == "body":
            self.in_body = True
        if not self.in_body:
            return
        self.process_starttag(tag)

    def process_starttag(self, tag):
        """Обрабатывает структурные HTML-теги."""
        if tag in LIST_STYLES:
            self.list_type = tag
        elif tag == "li":
            self.in_list_item = True
            self.start_paragraph()
        elif tag in {"p", "div"}:
            self.start_paragraph()
        elif tag in HEADING_TAGS:
            self.start_heading(tag)
        else:
            self.process_inline_tag(tag)

    def process_inline_tag(self, tag):
        """Обрабатывает теги переноса и форматирования."""
        if tag == "br":
            self.add_line_break()
        elif tag in FORMAT_TAGS:
            self.formats.append(tag)

    def start_heading(self, tag):
        """Создаёт заголовок соответствующего уровня."""
        self.heading_level = int(tag[1])
        self.start_paragraph()

    def add_line_break(self):
        """Добавляет перенос строки внутри абзаца."""
        if self.paragraph is not None:
            self.paragraph.add_run().add_break()

    def handle_endtag(self, tag):
        """Обрабатывает закрывающие HTML-теги."""
        if not self.in_body:
            return
        self.process_endtag(tag)
        if tag == "body":
            self.in_body = False

    def process_endtag(self, tag):
        """Выбирает действие для закрывающего тега."""
        if tag in PARAGRAPH_TAGS:
            self.end_paragraph(tag)
        elif tag in HEADING_TAGS:
            self.paragraph = None
            self.heading_level = None
        elif tag in LIST_STYLES:
            self.list_type = None
        elif tag in FORMAT_TAGS:
            self.end_format(tag)

    def end_paragraph(self, tag):
        """Завершает абзац или элемент списка."""
        self.paragraph = None
        if tag == "li":
            self.in_list_item = False

    def end_format(self, tag):
        """Завершает форматирование текста."""
        if tag in self.formats:
            self.formats.remove(tag)

    def handle_data(self, data):
        """Добавляет текст из HTML в документ."""
        if not self.in_body or not data.strip():
            return
        if self.paragraph is None:
            self.start_paragraph()
        self.add_formatted_run(data)

    def add_formatted_run(self, data):
        """Создаёт текстовый фрагмент с форматированием."""
        run = self.paragraph.add_run(data)
        run.bold = bool({"strong", "b"} & set(self.formats))
        run.italic = bool({"em", "i"} & set(self.formats))
        run.underline = "u" in self.formats

    def start_paragraph(self):
        """Создаёт абзац с соответствующим стилем."""
        if self.heading_level is not None:
            self.paragraph = self.document.add_heading(
                level=self.heading_level
            )
        elif self.in_list_item and self.list_type in LIST_STYLES:
            self.paragraph = self.document.add_paragraph(
                style=LIST_STYLES[self.list_type]
            )
        else:
            self.paragraph = self.document.add_paragraph()


def convert_html_to_docx(input_path, output_path):
    """Преобразует HTML-файл в DOCX."""
    html = Path(input_path).read_text(encoding="utf-8")
    document = Document()
    parser = HTMLToDOCXParser(document)
    parser.feed(html)
    document.save(output_path)


def main():
    """Обрабатывает аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Преобразование HTML-файла в DOCX."
    )
    parser.add_argument("input", help="Путь к HTML-файлу")
    parser.add_argument("output", help="Путь к DOCX-файлу")
    args = parser.parse_args()
    convert_html_to_docx(args.input, args.output)


if __name__ == "__main__":
    main()
