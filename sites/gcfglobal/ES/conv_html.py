#!/usr/bin/python3
import os, string, sys
import copy
import json
import re
import string
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup, Comment, SoupStrainer
from basicspider.sp_lib import *

START_PAGE = 'https://edu.gcfglobal.org/es/topics/'
MAIN_SOURCE_DOMAIN = None
HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/es/', 'http://www.gcfaprendelibre.org/']
HTML_EXCL_PATTERNS = []
OUTPUT_FILE_PREFIX = 'site'
DOWNLOAD_DIR = 'site-download/'

dst_dir = '/library/www/html/modules/es-GCF2021/'
external_url_not_found = '/not-offline.html'

# read stats
site_urls = read_json_file(OUTPUT_FILE_PREFIX + '_urls.json')
site_redirects = read_json_file(OUTPUT_FILE_PREFIX + '_redirects.json')

page_links = {}

# for test
url = 'https://edu.gcfglobal.org/es/como-usar-whatsapp/como-instalar-y-crear-una-cuenta-en-whatsapp-/1/'
url2 = 'https://edu.gcfglobal.org/es/como-usar-windows-10/que-es-el-area-de-notificaciones-de-windows-10/1/'

def main(argv):
    top_list = START_PAGE
    topic_list = get_topic_list(top_list)
    for topic in topic_list:
        lesson_list = get_lesson_list(topic)
        # convert_page(topic, 'topic')
        for lesson in lesson_list:
            pass
            # convert_page(lesson, 'lesson')

    pass

def get_topic_list(index_url):
    topic_list = []
    page, page_file_name = get_page(index_url)
    for topic in page.find_all('ul', class_ = 'level-1'):
        li_list = topic.find_all('li')
        for li in li_list:
            topic_url = urljoin(index_url, li.a['href'])
            topic_list.append(topic_url)
    #return ['https://edu.gcfglobal.org/es/como-usar-whatsapp/']
    return topic_list

def get_lesson_list(topic_url):
    return ['https://edu.gcfglobal.org/es/como-usar-whatsapp/como-instalar-y-crear-una-cuenta-en-whatsapp-/1/']

def convert_page(url, page_type):
    print('Converting ' + url)

    page, page_file_name = get_page(url)

    if page_type == 'topic':
        page = do_topic_page(url, page)
    if page_type == 'lesson':
        page = do_lesson_page(url, page)

    html_output = page.encode_contents(formatter='html')
    output_file_name = dst_dir + page_file_name

    write_html_file(output_file_name, html_output)
    print(output_file_name)

def get_page(url):
    content_type = site_urls[url]['content-type']
    page_file_name = url_to_file_name(url, content_type)
    input_file_path = DOWNLOAD_DIR + page_file_name

    with open(input_file_path, 'r') as f: html = f.read()

    page = BeautifulSoup(html, "html5lib")
    return page, page_file_name

def do_topic_page(url, page):
    pass
    return page

def do_lesson_page(url, page):
    css_files = page.find_all('link',{'rel':'stylesheet'})

    for link in css_files:
        link.extract()

    for s in page(["script", "style"]): # remove all javascript and stylesheet code
        s.extract()

    for comments in page.head.findAll(text=lambda text:isinstance(text, Comment)):
        comments.extract()

    #for tag in page.find_all('iframe'):
    #    tag.decompose()

    #main_content = page.find("div", id = 'background')
    main_content = page.find("div", id = 'content-area')

    main_content.find("div", class_ = 'infinite-nav').decompose()


    # wes4BlAXgzg
    # u_0Ns6paWQE

    video_blocks =  main_content.find_all("div", class_ = 'video-embed')
    for video_block in video_blocks:
        new_embed = get_video_block(video_block)
        video_block.iframe.replace_with(new_embed)

    logo_lines = BeautifulSoup(get_logo_lines(), 'html.parser')
    #main_content.div.insert_before(logo_lines)

    page.body.clear()
    page.body.append(logo_lines)
    #page.body.append(left_nav)
    page.body.append(main_content)

    head_lines = BeautifulSoup(get_head_lines(), 'html.parser')

    #print(head_lines)
    bottom_lines = BeautifulSoup(get_bottom_lines(), 'html.parser')
    #print(bottom_lines)

    page.head.append(head_lines)
    page.body.append(bottom_lines)

    page = fix_links(page, url)

    return page

def get_video_block(block):
    embed_html = '<video controls width="853" height="480" src="/videos/'
    video_link = block.iframe['src']
    video_id = urlparse(video_link).path.split('/')[-1]
    embed_html += video_id + '.mp4" poster="/videos/' + video_id
    embed_html += '.webp"></video>'
    #return '<video controls width="853" src="/videos/wes4BlAXgzg.mp4" poster="/videos/wes4BlAXgzg.webp"></video>'
    print(embed_html)
    new_embed = BeautifulSoup(embed_html, 'html.parser')
    return new_embed


def fix_links(page, page_url):
    # calculate links relative current page path
    page_domain = urlparse(page_url).netloc
    links = page.find_all(['a', 'link'], href=True) # check for both a and link tags
    for tag in links:
        href = tag['href']
        if not href:
            continue
        #print('href is ' + href)
        if href[0] == '#': # internal
            continue
        # first handle any redirection
        if href in site_redirects:
            href = site_redirects[href]

        parsed_link = urlparse(href)
        if parsed_link.netloc != '' and parsed_link.netloc != page_domain: # external link
            tag['href'] = convert_link(page_url, external_url_not_found)
        elif not is_offline_link(href):
            tag['href'] = convert_link(page_url, external_url_not_found)
        elif is_page_link_not_found(page_url, href):
            tag['href'] = convert_link(page_url, external_url_not_found)
        else:
            href_path = convert_link(page_url, href)
            if not href_path:
                continue
            #tag['href'].replace(tag['href'], href_path)
            tag['href'] = href_path

    elements = page.find_all(['audio', 'embed', 'iframe', 'img', 'input', 'script', 'source', 'track', 'video'])
    for tag in elements:
        for attr in ['src', 'poster']:
            if tag.has_attr(attr):
                attr_path = convert_link(page_url, tag[attr])
                tag[attr] = attr_path
    return page

def is_offline_link(url):
    # check if link is part off the scraped site
    pass
    match_suffixes = ['/guides', '/news', '/organizations', '/pages', '/help', '/tips', '/gard', '/about-gard', '/diseases/fda-orphan-drugs']
    url_prefix = '^https?://rarediseases.info.nih.gov'
    rel_link_prefix = '^'
    for m in match_suffixes:
        p1 = re.compile(rel_link_prefix + m)
        if p1.match(url):
            return False
        p2 = re.compile(url_prefix + m)
        if p2.match(url):
            return False
    return True

def is_page_not_found(page_url): # hard coded list
    pages_not_found = get_page_not_found_list()
    if page_url in pages_not_found:
        return True
    else:
        return False

def is_page_link_not_found(page_url, url): # hard coded list
    pages_not_found = get_page_not_found_list()
    if urljoin(page_url, url) in pages_not_found:
        return True
    else:
        return False

def get_page_not_found_list():
    pages_not_found = [

        ]
    return pages_not_found

def convert_link(base_url, href):
    # check for redirect
    # get content-type
    # compute href file name
    # convert to relative path
    href_url = urljoin(base_url, href)
    href_url_defrag = urldefrag(href_url)[0]
    base_path = url_to_file_name(base_url, 'text/html') # has to be html
    if href_url_defrag in site_redirects:
        href_url_defrag = site_redirects[href_url_defrag]
    if href_url_defrag in site_urls:
        content_type = site_urls[href_url_defrag]['content-type']
        href_path = url_to_file_name(href_url, content_type)
        href_path = posixpath.relpath(href_path, start=os.path.dirname(base_path))
        return href_path
    else:
        href_path = url_to_file_name(href_url, None) # allow links not in site_urls if have extension
        if href_path:
            return posixpath.relpath(href_path, start=os.path.dirname(base_path))
        else:
            print('Unknown URL ' + href_url + ' not in site_urls')
            return None

def write_html_file(output_file_name, html_output):
    output_dir = os.path.dirname(output_file_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_file_name, 'wb') as f:
        f.write(html_output)

def get_head_lines():
    head_lines = '''
    <link rel="stylesheet" href="/styles/deployment-es/lessonpage-es.concat.css">
    '''
    return head_lines

def get_logo_lines():
    logo_lines = '''
    <div style="margin-left:20px;">
    <a class="logo-link" href="/es/">
    <img style="height:50px;" class="logo logo-left main-logo-es" src="/assets/gcfglobal-color.png"></a>
    <img style="height:60px;" class="logo logo-middle logo-es" src="/assets/logo-es.svg">
    </div>
    '''
    return logo_lines

def get_bottom_lines():
    bottom_lines = '''
    '''
    return bottom_lines

################### BELONGS SOMEWHERE ELSE ###################
def calc_tag_struct(tag):
    struct_string = ''
    for parent in tag.parents:
        if parent.name == 'body':
            break
        if parent is None:
            print(parent)
        else:
             print(parent.name, parent.attrs)
             struct_string = f'{parent.name} {parent.attrs} {struct_string}'
    return struct_string

if __name__ == "__main__":
    main(sys.argv)
