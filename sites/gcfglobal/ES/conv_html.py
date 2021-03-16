#!/usr/bin/python3
import os, string, sys
import copy
import json
import re
import string
import argparse
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup, Comment, SoupStrainer
import youtube_dl
from basicspider.sp_lib import *

START_PAGE = 'https://edu.gcfglobal.org/es/topics/'
MAIN_SOURCE_DOMAIN = None
# HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/es/', 'http://www.gcfaprendelibre.org/']
HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/es/']
HTML_EXCL_PATTERNS = []
OUTPUT_FILE_PREFIX = 'site'
DOWNLOAD_DIR = 'site-download/'
DOWNLOAD_ASSETS = True

dst_dir = '/library/www/html/modules/es-GCF2021/'
external_url_not_found = '/not-offline.html'

# read stats
site_urls = read_json_file(OUTPUT_FILE_PREFIX + '_urls.json')
site_redirects = read_json_file(OUTPUT_FILE_PREFIX + '_redirects.json')

page_links = {}

# for test
url = 'https://edu.gcfglobal.org/es/como-usar-whatsapp/como-instalar-y-crear-una-cuenta-en-whatsapp-/1/'
url2 = 'https://edu.gcfglobal.org/es/como-usar-windows-10/que-es-el-area-de-notificaciones-de-windows-10/1/'
url3 = 'https://edu.gcfglobal.org/es/excel-2016/como-crear-un-nuevo-archivo-en-excel-2016/1/'
url4 = 'https://edu.gcfglobal.org/es/seguridad-en-internet/'

def main(args):
    global DOWNLOAD_ASSETS
    if args.nodownload:
        DOWNLOAD_ASSETS = False

    top_url = START_PAGE

    page, page_file_name = get_page(top_url)
    course_list = get_topic_list(page, top_url)

    for course_index in course_list:
        #do_course(course_index)
        pass

    page = do_top_index_page(top_url, page)
    output_converted_page(page, page_file_name)

def get_topic_list(index_page, index_url):
    # topic section ul all-topics
    #   topic li all-topics
    #     topic courses ul level-1 (only one per topic)
    #       course li
    course_list = []
    topic_section = index_page.find('ul', class_ = 'all-topics')
    topics = topic_section.find_all('li', class_ = 'all-topics')
    for topic in topics:
        topic_header = topic.find('ul', class_ = 'level-1')
        topic_courses = topic_header.find_all('li')
        for course in topic_courses:
            course_url = urljoin(index_url, course.a['href'])
            course_list.append(course_url)
    return course_list

def do_top_index_page(top_url, page):
    page = scrub_header(page)

    title_div = BeautifulSoup('<div class="title-content"><h1>Todos los cursos</h1></div>', 'html.parser')
    main_content = page.find('ul', class_ = 'all-topics')

    # make topics headings not links
    topics = main_content.find_all('li', class_ = 'all-topics')
    for topic in topics:
        heading = BeautifulSoup('<h2>' + topic.a.text + '</h2>', 'html.parser')
        topic.a.replace_with(heading)

    logo_lines = BeautifulSoup(get_logo_lines(), 'html.parser')

    page.body.clear()
    page.body.append(logo_lines)
    #page.body.append(title_div)
    page.body.append(BeautifulSoup('<div style="margin-left:20px;">', 'html.parser'))
    page.body.div.append(title_div)
    page.body.div.append(main_content)

    head_lines = BeautifulSoup('<link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/alltopics.concat.css">', 'html.parser')
    bottom_lines = BeautifulSoup(get_bottom_lines(), 'html.parser')
    page.head.append(head_lines)
    page.body.append(bottom_lines)
    #print(page.head)

    page = handle_page_links(page, top_url)
    #print(page.head)
    return page

def do_course(course_index):
    # process index
    # get lesson list
    # process each lesson

    page, page_file_name = get_page(course_index)

    course_section = page.find("div", id = 'content-area')
    for lesson in course_section.find_all('li'):
        lesson_url = urljoin(course_index, lesson.a['href'])
        convert_page(lesson_url, 'lesson')

    page = do_course_index_page(course_index, page)
    output_converted_page(page, page_file_name)

def convert_page(url, page_type):
    print('Converting ' + url)

    page, page_file_name = get_page(url)

    if page_type == 'course':
        page = do_course_index_page(url, page)
    if page_type == 'lesson':
        page = do_lesson_page(url, page)

    output_converted_page(page, page_file_name)

def get_page(url):
    content_type = site_urls[url]['content-type']
    page_file_name = url_to_file_name(url, content_type)
    input_file_path = DOWNLOAD_DIR + page_file_name

    with open(input_file_path, 'r') as f: html = f.read()

    page = BeautifulSoup(html, "html5lib")
    return page, page_file_name

def output_converted_page(page, page_file_name):
    html_output = page.encode_contents(formatter='html')
    output_file_name = dst_dir + page_file_name

    write_html_file(output_file_name, html_output)
    print(output_file_name)

def do_course_index_page(url, page):
    page = scrub_header(page)

    main_content = page.find("div", id = 'content-area')
    main_content['style'] = "width:960px; margin: 0 auto;" # because wrappers not included

    logo_lines = BeautifulSoup(get_logo_lines(), 'html.parser')
    page.body.clear()
    page.body.append(logo_lines)
    page.body.append(main_content)
    head_lines = BeautifulSoup('<link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/tutorial.concat.css">', 'html.parser')
    bottom_lines = BeautifulSoup(get_bottom_lines(), 'html.parser')
    page.head.append(head_lines)
    page.body.append(bottom_lines)
    #print(page.head)

    page = handle_page_links(page, url)
    #print(page.head)
    return page

def do_lesson_page(url, page):
    page = scrub_header(page)

    # get nav content
    nav_up_link = page.find('a', class_ = 'header-tutorial-link')['href']
    nav_block = page.find('div', class_ = 'fullpage-nav')
    nav_left_link = nav_block.find('div', class_ = 'previous').a['href']
    nav_right_link = nav_block.find('div', class_ = 'next').a['href']

    #main_content = page.find("div", id = 'background')
    main_content = page.find("div", id = 'content-area')
    main_content['style'] = "width:960px; margin: 0 auto;" # because wrappers not included

    main_content.find("div", class_ = 'infinite-nav').decompose()
    main_content.find("div", class_ = 'fullpage-nav').decompose()


    # wes4BlAXgzg
    # u_0Ns6paWQE

    video_blocks =  main_content.find_all("div", class_ = 'video-embed')
    for video_block in video_blocks:
        new_embed = get_youtube_video_block(video_block)
        video_block.iframe.replace_with(new_embed)

    logo_lines = BeautifulSoup(get_logo_lines(), 'html.parser')
    #main_content.div.insert_before(logo_lines)

    page.body.clear()
    page.body.append(logo_lines)
    #page.body.append(left_nav)
    page.body.append(main_content)

    head_lines = BeautifulSoup(get_head_lines(), 'html.parser')
    #print(head_lines)
    bottom_nav = BeautifulSoup(get_bottom_nav(nav_up_link, nav_left_link, nav_right_link), 'html.parser')
    bottom_lines = BeautifulSoup(get_bottom_lines(), 'html.parser')
    #print(bottom_lines)

    page.head.append(head_lines)
    page.body.append(bottom_nav)
    page.body.append(bottom_lines)
    print(page.head)

    page = handle_page_links(page, url)
    #print(page.head)

    return page

def scrub_header(page):
    css_files = page.find_all(['link',{'rel':'stylesheet'},'link',{'rel':'preload'}])

    for link in css_files:
        link.extract()

    for s in page(["script", "style"]): # remove all javascript and stylesheet code
        s.extract()

    for comments in page.head.findAll(text=lambda text:isinstance(text, Comment)):
        comments.extract()

    return page

def get_youtube_video_block(block):
    # use full links and convert_link will fix them later
    # block is iframe but converted to video with explicit links
    # video extension needs to agree with what get_youtube_video downloads
    # webm at 480p is format 244
    # we are assuming this is available for all videos
    video_ext = '.webm'

    embed_html = '<video controls width="853" height="480" '
    video_link = block.iframe['src']
    video_link = urljoin(video_link, urlparse(video_link).path)
    video_src = 'src="' + video_link + video_ext +'" '
    poster_src = 'poster="' + video_link + '.webp"'

    #video_id = urlparse(video_link).path.split('/')[-1]
    #embed_html += video_id + '.mp4" poster="/videos/' + video_id
    embed_html += video_src + poster_src + '></video>'
    #return '<video controls width="853" src="/videos/wes4BlAXgzg.mp4" poster="/videos/wes4BlAXgzg.webp"></video>'
    #print(embed_html)
    new_embed = BeautifulSoup(embed_html, 'html.parser')
    return new_embed

def handle_page_links(page, page_url):
    # calculate links relative current page path
    # cases
    #   broken link
    #   no link type
    #   type text/
    #   page internal link
    #   external outside of filter
    #   other asset
    #   youtube video
    #   other embed or iframe

    links = page.find_all(['a', 'link'], href=True) # check for both a and link tags
    for tag in links:
        href = tag['href']
        if not href:
            continue

        #print('href is ' + href + ' in ' + tag.name)
        if href[0] == '#': # internal
            continue

        href = urljoin(page_url, href) # convert to absolute linke
        # first handle any redirection
        if href in site_redirects:
            href = site_redirects[href]

        # if type not text get the asset
        link_type = site_urls.get(href,{}).get('content-type', None)
        save_href = href

        if not link_type:
            href = external_url_not_found
        elif link_type == 'broken-link':
            href = external_url_not_found

        elif link_type == 'text/html': # only take html links from within filtered urls
            if not is_link_included(href):
                href = external_url_not_found
            elif is_page_link_not_found(page_url, href):
                href = external_url_not_found

        href_path = convert_link(page_url, href)
        if not href_path:
            continue
        #tag['href'].replace(tag['href'], href_path)
        tag['href'] = href_path
        if save_href == href and link_type != 'text/html': # no broken or other overrides
            get_site_asset(href, link_type)

    elements = page.find_all(['audio', 'embed', 'iframe', 'img', 'input', 'script', 'source', 'track', 'video'])
    for tag in elements:
        if tag.name in ['img', 'script']: # easy ones with just src
            attr = 'src'
            if tag.has_attr(attr):
                #print('tag, attr, tag[attr]', tag, attr, tag[attr])
                abs_url = urljoin(page_url, tag[attr])
                #print('abs url', abs_url)

                attr_path = convert_link(page_url, tag[attr])
                tag[attr] = attr_path

                link_type = site_urls.get(abs_url,{}).get('content-type', None)
                if link_type:
                    get_site_asset(abs_url, link_type)
                else:
                    # this could be file not from source so not in site_urls
                    print('Unable to download ' + abs_url)
            else:
                continue
        else: # do the others individually
            if tag.name == 'video':
                tag = handle_video_tag(tag, page_url)
            else:
                print('Unhandled tag', tag.name)
    return page

def handle_video_tag(video_tag, page_url):
    video_link = video_tag.get('src')
    poster_link = video_tag.get('poster')
    is_youtube = False

    if 'www.youtube.com' in video_link or 'www.youtu.be' in video_link:
        is_youtube = True
        # get youtube video and poster

    if video_link:
        video_tag['src'] = convert_link(page_url, video_link)
        if is_youtube:
            get_youtube_video(video_link, format='244') # 480p webm
        else:
            get_site_media_asset(page_url, video_link)

    if poster_link:
        video_tag['poster'] = convert_link(page_url, poster_link)
        if not is_youtube: # poster comes with video in youtube
            get_site_media_asset(page_url, poster_link)

    return video_tag

def get_site_media_asset(page_url, url):
    abs_url = urljoin(page_url, url)
    link_type = site_urls.get(abs_url,{}).get('content-type', None)
    get_site_asset(url, link_type)

def get_youtube_video(video_link, format='bestaudio/best'):
    # gets both video and poster
    video_id = urlparse(video_link).path.split('/')[-1].split('.')[0]
    asset_file_name = url_to_file_name(video_link, None) # extension should be there from video block
    output_file_name = dst_dir + asset_file_name
    output_dir = output_dir = os.path.dirname(output_file_name)
    print("getting", video_link, output_file_name)
    # https://github.com/ytdl-org/youtube-dl/blob/master/README.md#embedding-youtube-dl
    if not os.path.exists(output_file_name):
        ydl_opts = {'writethumbnail': True, 'format': format, 'outtmpl': output_dir + '/%(id)s.%(ext)s'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(['https://www.youtube.com/watch?v=' + video_id])

        #cmd = 'youtube-dl --write-thumbnail -o ' + output_dir + '/%(id)s.%(ext)s ' + video_id
        #subproc_run(cmd)

def get_youtube_video_info(video_id):
    ydl = youtube_dl.YoutubeDL()
    ydl.add_default_info_extractors()
    info = ydl.extract_info('http://www.youtube.com/watch?v=' + video_id, download=False)
    formats = info['formats']
    # is array with 'format_id' and 'format' (description)

def is_link_included(url):
    # check if link matches patterns to include
    for m in HTML_INCL_PATTERNS:
        p1 = re.compile(m)
        if p1.match(url):
            return True
    return False

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

def get_site_asset(url, content_type):
    if not DOWNLOAD_ASSETS:
        return
    asset_file_name = url_to_file_name(url, content_type)
    output_file_name = dst_dir + asset_file_name
    print("getting", url, output_file_name)
    if not os.path.exists(output_file_name):
        download_binary_url(url, output_file_name)

def get_head_lines():
    head_lines = '''
    <link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/lessonpage-es.concat.css">
    '''
    # <script defer src="/scripts/deployment-es/tutorial.concat.js" type="text/javascript"></script> no help
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

# also http://jsfiddle.net/wSd32/1/
def get_bottom_nav(nav_up_link, nav_left_link, nav_right_link):
    left_opacity = '1.0'
    right_opacity = '1.0'

    if nav_left_link == nav_up_link:
        nav_left_link = '#'
        left_opacity = '0.4'

    if nav_right_link == nav_up_link:
        nav_right_link = '#'
        right_opacity = '0.4'

    nav_lines = '<div style="text-align:center;margin-top:40px;width: 400px;margin-left: auto;margin-right: auto;">'
    nav_lines += '<div style="float: left;"><a href="' + nav_left_link + '">'
    nav_lines += '<img src="/assets/left-arrow.png" style="opacity:' + left_opacity + ';"></a></div>'
    nav_lines += '<div style="float: right;"><a href="' + nav_right_link + '">'
    nav_lines += '<img src="/assets/right-arrow.png" style="opacity:' + right_opacity + ';"></a></div>'
    nav_lines += '<div style="text-align:left;margin:0 auto !important;display:inline-block;"><a href="' + nav_up_link + '">'
    nav_lines += '<img src="/assets/up-arrow.png"></a></div>'
    nav_lines += '</div>'
    return nav_lines

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
    parser = argparse.ArgumentParser(description="Convert downloaded html. By default downloads asset files")
    parser.add_argument("-n", "--nodownload", help="don't download assets", action="store_true")
    args = parser.parse_args()
    main(args)
