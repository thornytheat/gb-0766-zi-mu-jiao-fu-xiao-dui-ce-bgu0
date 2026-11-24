import csv
from io import StringIO
from app.problems import Rejection


def tabulate(source, aliases, fields, optional=()):
    reader = csv.reader(StringIO(source.removeprefix('﻿'), newline=''), strict=True)
    rows, skipped = [], []
    headings, blanks, data_lines = 1, 0, 0
    required = set(fields)
    allowed = required | set(optional)
    try:
        raw_header = next(reader, None)
        if raw_header is None:
            raise Rejection('EMPTY', '文件为空')
        if not any(raw_header):
            raise Rejection('BLANK', '文件首行为空')
        header = [aliases.get(field, field) for field in raw_header]
        if len(header) != len(raw_header) or set(header) - allowed or not required <= set(header):
            raise Rejection('HEADER', '文件表头不符')
        while True:
            line = reader.line_num + 1
            values = next(reader, None)
            if values is None:
                break
            data_lines += 1
            if not any(value.strip() for value in values):
                blanks += 1
            elif [aliases.get(field, field) for field in values] == header:
                headings += 1
            elif len(values) != len(header):
                skipped.append(dict(line=line, code='WIDTH', raw=values))
            else:
                clean = {key: value.strip() for key, value in zip(header, values)}
                for key in optional:
                    clean.setdefault(key, '')
                rows.append(dict(line=line, raw=values, **clean))
    except csv.Error as exc:
        raise Rejection('CSV', f'第 {reader.line_num} 行 CSV 损坏') from exc
    if not data_lines:
        raise Rejection('HEADER_ONLY', '文件仅含表头')
    if data_lines == blanks:
        raise Rejection('BLANK', '文件记录全为空')
    return rows, skipped, headings, blanks, data_lines
