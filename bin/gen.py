# -*- coding: utf8 -*-

from hashlib import md5
from os import name
from pathlib import Path
import logging
import re
import datetime
from markdown2 import markdown

logging.basicConfig(level=logging.DEBUG)


RE_TITLE = re.compile(r'(?<=<title>).*(?=</title>)')
META_INVALID_CHARS = re.compile(r'[\[\]\"“”]')
INDEX_PATHS = map(Path, ['about', 'pages', 'posts'])
BOOKMARKS_PATHS = map(Path, ['bookmarks'])
TAGS_PATHS = map(Path, ['posts', 'pages', 'about'])

EXTS = ('md', 'html', 'htm')
TAGS_DIR = 'tags'
PAGES_DIR = 'pages'
POSTS_DIR = 'posts'

# 解析html的title
def extract_html_title(fpath: Path) -> str:
    '''提取html.title作为链接名字'''
    html = open(fpath).read()
    try:
        title = RE_TITLE.findall(html)[0]
    except IndexError:
        title = fpath.name
    finally:
        return title

class MD(object):
    def __init__(self, fpath: Path):
        with open(fpath, encoding='utf8') as fp:
            self.md = markdown(fp.read(), extras=['metadata'])
            self.meta = self.md.metadata
            self.path = fpath
    @property
    def date(self) -> str:
        try:
            return self.md.metadata['date'][:10]
        except KeyError:
            return datetime.datetime.now().strftime('%Y-%m-%d')
    
    @property
    def title(self) -> str:
        try:
            title = META_INVALID_CHARS.sub('', self.meta['title'])
        except KeyError:
            title = f'{self.md[:25].strip()}...'
        finally:
            return title

    # 解析md的tag字段
    @property
    def tags(self) -> list:
        try:
            tags = META_INVALID_CHARS.sub('', self.meta['tags'])
        except KeyError:
            tags = []
        finally:
            return tags

    #解析itemurl (bookmark)字段
    @property
    def itemurl(self) -> str:
        try:
            url = self.md.metadata['itemurl']
        except KeyError:
            url = ''
        finally:
            return url

    # 判断是否是draft
    @property
    def is_draft(self) -> bool:
        try:
            draft = self.md.metadata['draft']
        except KeyError:
            draft = 'false'
        finally:
            return True if 'true' in draft else False

def iterate_links(fpath: Path) -> list:
    result = []
    for sub_fpath in fpath.iterdir():
        # md files
        if sub_fpath.is_file() and sub_fpath.suffix == '.md':
            mk = MD(sub_fpath)
            if not mk.is_draft:
                # bookmark md without content
                if mk.itemurl: # place mark link only
                    result.append(f'1. {mk.date}, [{mk.title}]({mk.itemurl})')
                # regular md
                else:
                    result.append(f'1. {mk.date}, [{mk.title}]({fpath.name}/{sub_fpath.name})')
        # or html files
        if sub_fpath.is_file() and sub_fpath.suffix == '.html':
            title = extract_html_title(sub_fpath)
            result.append(f'1. [{title}]({fpath.name}/{sub_fpath.name})')

    return result

def iterate_all_pages_tags(fpath: Path) -> dict:
    result = {}
    for sub_fpath in fpath.iterdir():
        if sub_fpath.suffix == '.md':
            md = MD(sub_fpath)
            try:
                tags = META_INVALID_CHARS.sub('', md.meta['tags'])
                tags = tags.strip().lower().split(',')
            except KeyError:
                continue

            for tag in tags:
                links = result.get(tag, [])
                links.append(f'{sub_fpath}')
                result[tag] = links
    return result

def gen_index(dirs, index: Path, tpl: str) -> None:
    """
    dir: Path, be iterated path
    index: Path, be written with file list
    tpl: if you want to display header information
    """
    with open(index, 'w', encoding='utf8') as index_fp:
        result = [tpl]
        for fpath in dirs:
            result.append(f'## {fpath.name}')
            result.extend(iterate_links(fpath))

        index_fp.write('\n'.join(result))
        logging.info(f'{index.name} is updated successfully')


def gen_tag_pages(dirs, index: Path, tpl: str) -> None:
    """
    dirs: tags taken from dirs list
    index: tags pages
    tpl: header information
    """
    def _write_tag_page(name: str, links: list) -> None:
        result = []
        tag_fpath = Path(TAGS_DIR) / f'{name}.md'
        with open(tag_fpath, 'w', encoding='utf8') as tag_fp:
            result.append(f'## {name}')
            for link in links:
                md = MD(Path(link))
                date = md.date
                result.append(f'* {date}, [{md.path.name}](../{link})')
            tag_fp.write('\n'.join(result))
            logging.debug(f'_wrote tag page {name}')

    with open(index, 'w', encoding='utf8') as index_fp:
        result = [tpl]
        for fpath in TAGS_PATHS:
            tags = iterate_all_pages_tags(fpath)
            # sort the tags by tag count
            for name in sorted(tags, key=lambda k: len(tags[k]), reverse=True):
                if len(name) > 0:
                    _write_tag_page(name, tags[name])
                    result.append(f'* [{name}](../{TAGS_DIR}/{name}.md) ({len(tags[name])})')    
        
        index_fp.write('\n'.join(result))
        logging.info(f'{index.name} is updated successfully')


if __name__ == '__main__':
    updated_time = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # README.md
    index_tpl = f'> Last Update: {updated_time}\n'
    gen_index(INDEX_PATHS, Path('index.md'), tpl=index_tpl)

    # bookmarks page
    bookmarks_tpl = '''---
title: "文摘"
---
'''
    gen_index(BOOKMARKS_PATHS, Path('pages/bookmarks.md'), tpl=bookmarks_tpl)
    
    tags_tpl = '''---\ntitle: tags\n---\n## All Tags of This Site'''
    # tags
    gen_tag_pages(TAGS_PATHS, Path('about/tags.md'), tpl=tags_tpl)
