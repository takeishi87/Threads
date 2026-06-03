#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown -> Gutenberg ブロックHTML 変換器
記事Markdown（output/posts/*.md）をWordPress Gutenbergブロック形式に変換する。
- # 見出し（記事タイトル行）は除外（投稿タイトルで持つため）
- ## ─── ... ─── -> wp:heading h2
- ### ...        -> wp:heading h3
- | ... |        -> wp:table（figure + table、th/td対応）
- ---            -> wp:separator
- **bold**       -> <strong>
- 通常段落        -> wp:paragraph
- - 箇条書き      -> wp:list
"""
import re, sys, json, html

def inline(text):
    # エスケープしてから ** を strong へ
    text = html.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
    return text

def convert(md):
    lines = md.split('\n')
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # 空行
        if stripped == '':
            i += 1
            continue

        # 記事タイトル（# ）は除外
        if re.match(r'^#\s+', stripped):
            i += 1
            continue

        # 区切り線
        if stripped == '---':
            blocks.append('<!-- wp:separator -->\n<hr class="wp-block-separator has-alpha-channel-opacity"/>\n<!-- /wp:separator -->')
            i += 1
            continue

        # 見出し h2 (## ─── ... ───)
        m = re.match(r'^##\s+(.*)', stripped)
        if m:
            inner = inline(m.group(1).strip())
            blocks.append(f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{inner}</h2>\n<!-- /wp:heading -->')
            i += 1
            continue

        # 見出し h3 (### ...)
        m = re.match(r'^###\s+(.*)', stripped)
        if m:
            inner = inline(m.group(1).strip())
            blocks.append(f'<!-- wp:heading {{"level":3}} -->\n<h3 class="wp-block-heading">{inner}</h3>\n<!-- /wp:heading -->')
            i += 1
            continue

        # テーブル
        if stripped.startswith('|') and '|' in stripped[1:]:
            tbl_lines = []
            while i < n and lines[i].strip().startswith('|'):
                tbl_lines.append(lines[i].strip())
                i += 1
            blocks.append(build_table(tbl_lines))
            continue

        # 箇条書き
        if re.match(r'^[-*]\s+', stripped):
            items = []
            while i < n and re.match(r'^[-*]\s+', lines[i].strip()):
                item = re.sub(r'^[-*]\s+', '', lines[i].strip())
                items.append(f'<!-- wp:list-item -->\n<li>{inline(item)}</li>\n<!-- /wp:list-item -->')
                i += 1
            inner = '\n'.join(items)
            blocks.append(f'<!-- wp:list -->\n<ul class="wp-block-list">\n{inner}\n</ul>\n<!-- /wp:list -->')
            continue

        # 通常段落
        blocks.append(f'<!-- wp:paragraph -->\n<p>{inline(stripped)}</p>\n<!-- /wp:paragraph -->')
        i += 1

    return '\n\n'.join(blocks)

def split_row(row):
    # 先頭末尾の | を除去してセル分割
    row = row.strip()
    if row.startswith('|'):
        row = row[1:]
    if row.endswith('|'):
        row = row[:-1]
    return [c.strip() for c in row.split('|')]

def is_separator_row(cells):
    return all(re.match(r'^:?-{2,}:?$', c) for c in cells if c != '')

def build_table(tbl_lines):
    rows = [split_row(r) for r in tbl_lines]
    # 区切り行を検出
    header = None
    body = []
    if len(rows) >= 2 and is_separator_row(rows[1]):
        header = rows[0]
        body = rows[2:]
    else:
        body = rows
    parts = ['<figure class="wp-block-table"><table><tbody>']
    if header:
        ths = ''.join(f'<th>{inline(c)}</th>' for c in header)
        parts.append(f'<tr>{ths}</tr>')
    for r in body:
        tds = ''.join(f'<td>{inline(c)}</td>' for c in r)
        parts.append(f'<tr>{tds}</tr>')
    parts.append('</tbody></table></figure>')
    table_html = ''.join(parts)
    return f'<!-- wp:table -->\n{table_html}\n<!-- /wp:table -->'

if __name__ == '__main__':
    path = sys.argv[1]
    out = sys.argv[2]
    with open(path, encoding='utf-8') as f:
        md = f.read()
    result = convert(md)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"OK: {path} -> {out} ({len(result)} chars, tables={result.count('wp:table')//2})")
