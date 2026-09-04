from datetime import date, datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils.html import escape


def build_xlsx(headers: list[str], rows: list[list[object]], sheet_name: str = 'Sheet1') -> bytes:
    """Создаёт простой XLSX-файл без внешних зависимостей."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', _content_types_xml())
        archive.writestr('_rels/.rels', _root_relationships_xml())
        archive.writestr('docProps/app.xml', _app_xml(sheet_name))
        archive.writestr('docProps/core.xml', _core_xml())
        archive.writestr('xl/workbook.xml', _workbook_xml(sheet_name))
        archive.writestr('xl/_rels/workbook.xml.rels', _workbook_relationships_xml())
        archive.writestr('xl/worksheets/sheet1.xml', _sheet_xml(headers, rows))
    return buffer.getvalue()


def _sheet_xml(headers: list[str], rows: list[list[object]]) -> str:
    body = [_row_xml(1, headers)]
    for index, row in enumerate(rows, start=2):
        body.append(_row_xml(index, row))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        f'{"".join(body)}'
        '</sheetData>'
        '</worksheet>'
    )


def _row_xml(index: int, values: list[object]) -> str:
    cells = []
    for column_index, value in enumerate(values, start=1):
        cell_reference = f'{_column_name(column_index)}{index}'
        cells.append(f'<c r="{cell_reference}" t="inlineStr"><is><t>{_cell_value(value)}</t></is></c>')
    return f'<row r="{index}">{"".join(cells)}</row>'


def _cell_value(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, (date, datetime)):
        return escape(value.isoformat())
    return escape(str(value))


def _column_name(index: int) -> str:
    name = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        '</Relationships>'
    )


def _workbook_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>'
        f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>'
        '</sheets>'
        '</workbook>'
    )


def _workbook_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )


def _app_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Employee Book</Application>'
        '<TitlesOfParts><vt:vector size="1" baseType="lpstr">'
        f'<vt:lpstr>{escape(sheet_name)}</vt:lpstr>'
        '</vt:vector></TitlesOfParts>'
        '</Properties>'
    )


def _core_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>Employee Book</dc:creator>'
        '</cp:coreProperties>'
    )
