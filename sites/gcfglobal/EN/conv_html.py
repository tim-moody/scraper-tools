#!/usr/bin/python3
import os, string, sys
import copy
import json
import re
import string
import argparse
from urllib.parse import urljoin, urldefrag, urlparse
import requests
from bs4 import BeautifulSoup, Comment, SoupStrainer
import youtube_dl
from icu import UnicodeString, Locale
from basicspider.sp_lib import *

START_PAGE = 'https://edu.gcfglobal.org/en/topics/'
MAIN_SOURCE_DOMAIN = None
# HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/es/', 'http://www.gcfaprendelibre.org/']
HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/en/']
HTML_EXCL_PATTERNS = []
OUTPUT_FILE_PREFIX = 'site'
HTML_DOWNLOAD_DIR = 'site-download/html/'
NON_HTML_DOWNLOAD_DIR = 'site-download/non-html/'
DOWNLOAD_ASSETS = True
INCL_YOUTUBE = True
# PREF_YOUTUBE_FORMATS = ['244', '243', '135', '134', '18'] # 480p webm, etc.
NO_VIDEO_MSG = 'Video not available'
NATIVE_LANGUAGE = 'en'

# Stop converting when this course is encountered
SKIP_FROM_COURSE = 'https://edu.gcfglobal.org/en/basicspanishskills/'

TARGET_DIR = '/library/www/html/modules/en-gcf_learn_2021/'
external_url_not_found = '/not-offline.html'

# read stats
site_urls = read_json_file(OUTPUT_FILE_PREFIX + '_urls.json')
site_redirects = read_json_file(OUTPUT_FILE_PREFIX + '_redirects.json')

page_links = {}

skip_from_course = 'https://edu.gcfglobal.org/en/basicspanishskills/'

# for test
u1 = 'https://edu.gcfglobal.org/en/computerbasics/about-this-tutorial/1/'
u2 = 'https://edu.gcfglobal.org/en/powerpoint2010/animating-text-and-objects/1/'
u3 = 'https://edu.gcfglobal.org/en/youtube/troubleshooting-common-problems/1/'
u4 = 'https://edu.gcfglobal.org/en/computerbasics/'

c1 = 'https://edu.gcfglobal.org/en/computerbasics/'

def main(args):
    global DOWNLOAD_ASSETS
    if args.nodownload:
        DOWNLOAD_ASSETS = False

    top_url = START_PAGE

    page, page_file_name = get_page(top_url)
    course_list = get_topic_list(page, top_url)

    for course_index in course_list:
        # stop when we reach indicated section of main index
        if course_index == SKIP_FROM_COURSE:
            break
        do_course(course_index)
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
        heading = BeautifulSoup('<a>' + topic.a.text + '</a>', 'html.parser') # needs to be <a> not to break css
        topic.a.replace_with(heading)

    logo_lines = BeautifulSoup(get_logo_lines(), 'html.parser')

    page.body.clear()
    page.body.append(logo_lines)
    #page.body.append(title_div)
    page.body.append(BeautifulSoup('<div style="margin-left:20px;">', 'html.parser'))
    page.body.div.append(title_div)
    page.body.div.append(main_content)

    head_html = '<link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/alltopics.concat.css">'
    head_html += '<script src="https://edu.gcfglobal.org/scripts/deployment-es/alltopics.concat.js" type="text/javascript"></script>'
    head_lines = BeautifulSoup(head_html, 'html.parser')

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
    input_file_path = HTML_DOWNLOAD_DIR + page_file_name

    # if an html file has not been downloaded just go get it
    if os.path.exists(input_file_path):
        html = read_html_file(input_file_path)
        # with open(input_file_path, 'r') as f: html = f.read()
    else:
        print ('Downloading missing url ' + url)
        response = requests.get(url)
        response.encoding = 'utf-8'
        html = response.text
        write_html_file(input_file_path, html)

    page = BeautifulSoup(html, "html5lib")
    return page, page_file_name

def output_converted_page(page, page_file_name):
    html_output = page.encode_contents(formatter='html')
    output_file_name = TARGET_DIR + page_file_name

    write_conv_html_file(output_file_name, html_output)
    print(output_file_name)

def do_course_index_page(url, page):
    page = scrub_header(page)

    main_content = page.find("div", id = 'content-area')
    #main_content['style'] = "width:960px; margin: 0 auto;" # because wrappers not included
    # remove any Quiz as it uses js we can't support
    lessons = main_content.find_all('ul', class_ = 'collection-items')
    lesson_h3 = main_content.find_all('h3')
    if lesson_h3[-1].text == 'Quiz':
        print('Removing Quiz')
        quiz = lesson_h3[-1].find_next_sibling('ul')
        quiz.decompose()
        lesson_h3[-1].decompose()
    logo_lines = BeautifulSoup(get_logo_lines(link=START_PAGE), 'html.parser')
    page.body.clear()
    page.body.append(logo_lines)
    page.body.append(main_content)
    head_lines = BeautifulSoup(get_course_index_head_lines(), 'html.parser')
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
    # main_content['style'] = "width:960px; margin: 0 auto;" # because wrappers not included

    main_content.find("div", class_ = 'infinite-nav').decompose()
    main_content.find("div", class_ = 'fullpage-nav').decompose()

    # handle data-url - FUTURE
    # <div class="wrapperpopup">
    # <div class="gcf_interactive" data-url=
    # for a in d.attrs.keys():
    # for now just remove section

    more_info = main_content.find("p", class_ = "moreInfo")
    if more_info:
        print('Removing moreInfo section.')
        more_info.decompose()

    wrapperpopup = main_content.find("div", class_ = 'wrapperpopup')
    if wrapperpopup:
        wrapperpopup.decompose()

    # keep it simple
    # just look for iframes
    iframes =  main_content.find_all("iframe")
    for ifr in iframes:
        video_link = ifr.get('src')
        if video_link:
            if '/www.youtube.com' in video_link or 'youtu.be' in video_link: # see if youtube
                new_embed = get_youtube_video_block(video_link)
                ifr.replace_with(new_embed)

    logo_lines = BeautifulSoup(get_logo_lines(link=nav_up_link), 'html.parser')
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
    #print(page.head)

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

def get_youtube_video_block(video_link):
    # use full links and convert_link will fix them later
    # block is iframe but converted to video with explicit links
    # video extension needs to agree with what get_youtube_video downloads
    # this is based on the format
    # same for poster extension
    embed_html = '<span style="margin: auto; padding-top: 225px; padding-bottom: 225px; padding-left: 335px; padding-right: 335px; line-height: 480px;'
    embed_html += ' width: 853px; background-color: grey;vertical-align: middle; color: white;">' + NO_VIDEO_MSG + '</span>'
    if INCL_YOUTUBE:
        #try: # all or nothing for now
            video_id = urlparse(video_link).path.split('/')[-1].split('.')[0]
            video_info = get_youtube_video_info(video_id)
            video_formats = get_youtube_video_formats(video_info)
            video_ext, video_fmt, audio_fmt = select_480p_format(video_formats)
            video_format = video_fmt + '+' + audio_fmt
            thumbnails = video_info['thumbnails']
            poster_ext = thumbnails[-1]['url'].split('?')[0].split('.')[-1]
            vtt_subs = get_youtube_subtitles(video_info)
            if NATIVE_LANGUAGE in vtt_subs:
                auto_gen = False
            elif NATIVE_LANGUAGE in video_info['automatic_captions']:
                auto_gen = True
            else:
                auto_gen = False
            if video_format:
                html = '<video controls width="853" height="480" class="mobile-video" '
                video_link = urljoin(video_link, urlparse(video_link).path)
                video_src = 'src="' + video_link + '.' + video_ext + '" data-video-format="' + video_format + '" '
                video_src += 'data-sub-langs="' +  ','.join(vtt_subs) + '" '
                video_src += 'data-sub-gen="' +  str(auto_gen) + '" '
                poster_src = 'poster="' + video_link + '.' + poster_ext + '"'
                html += video_src + poster_src + '>'
                if auto_gen:
                    html += get_youtube_lang_track(video_link, NATIVE_LANGUAGE, auto=True)
                for lang in vtt_subs:
                    html += get_youtube_lang_track(video_link, lang)
                html += '</video>'
                embed_html = html
        #except:
        #    print ('Error processing ' + video_link)
        #    pass
    print(embed_html)
    new_embed = BeautifulSoup(embed_html, 'html.parser')
    return new_embed

def get_youtube_lang_track(video_link, lang, auto=False):
    locale = Locale(lang)
    lang_name =locale.getDisplayName(locale)
    if auto:
        auto_suffix = '.auto'
    else:
        auto_suffix = ''
    html = '<track '
    html += 'label="' + lang_name + '" kind="subtitles" srclang="' + lang + '" src="' + video_link + auto_suffix + '.' + lang + '.vtt"'
    if lang == NATIVE_LANGUAGE:
        html += ' mode="showing" default'
    html += '>\n'
    return html

def handle_page_links(page, page_url):
    # calculate links relative to current page path
    # cases
    #   broken link
    #   no link type
    #   type text/
    #   page internal link
    #   external outside of filter
    #   other asset
    #   youtube video
    #   other video
    #   other embed or iframe

    links = page.find_all(['a', 'link'], href=True) # check for both a and link tags
    for tag in links:
        href = tag['href']
        if not href:
            continue

        #print('href is ' + href + ' in ' + tag.name)
        if href[0] == '#': # internal
            continue

        href = cleanup_url(urljoin(page_url, href)) # defrag and convert to absolute link
        # first handle any redirection
        if href in site_redirects:
            href = site_redirects[href]

        # if type not text get the asset
        link_type = site_urls.get(href,{}).get('content-type', None)
        save_href = href
        external_url = external_url_not_found + '?url=' + href

        if not link_type:
            href = external_url
        elif link_type == 'broken-link':
            href = external_url

        elif link_type == 'text/html': # only take html links from within filtered urls
            if not is_link_included(href):
                href = external_url
            elif is_page_link_not_found(page_url, href):
                href = external_url

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
                if tag.get('src'):
                    tag = handle_video_tag(tag, page_url)
            elif tag.name == 'source':
                tag = handle_video_tag(tag, page_url)
            elif tag.name == 'track':
                print(tag)
                if tag.get('src'):
                    tag['src'] = convert_link(page_url, tag['src'])
            else:
                print('Unhandled tag', tag.name)
    return page

def handle_video_tag(video_tag, page_url):
    # need to handle nested source tag
    # subtitle tracks src links are converted above
    # subtitle tracks download (including autogen) is part of get_youtube_video
    video_link = video_tag.get('src')
    poster_link = video_tag.get('poster')
    is_youtube = False

    if 'www.youtube.com' in video_link or 'www.youtu.be' in video_link:
        is_youtube = True
        yt_format = video_tag.get('data-video-format') # custom attribute to save preferred format
        yt_sub_gen = video_tag.get('data-sub-gen') == 'True' # do we need to generate subtitles for native language
        # get youtube video, poster and subtitles

    if video_link:
        if is_youtube:
            get_youtube_video(video_link, yt_format, yt_sub_gen)
            video_tag['src'] = convert_link(page_url, video_link)
        else:
            get_site_media_asset(page_url, video_link)
            video_tag['src'] = convert_link(page_url, video_link)

    if poster_link:
        video_tag['poster'] = convert_link(page_url, poster_link)
        if is_youtube: # poster comes with video in youtube
            poster_file_name = url_to_file_name(poster_link, None, incl_query=False) # assume it has an extension
            download_file_name = NON_HTML_DOWNLOAD_DIR + poster_file_name # and already downloaded
            dst_file = TARGET_DIR + poster_file_name
            if not os.path.exists(dst_file):
                copy_downloaded_file(download_file_name, dst_file)
        else:
            get_site_media_asset(page_url, poster_link)
    return video_tag

def get_site_media_asset(page_url, url):
    abs_url = urljoin(page_url, url)
    link_type = site_urls.get(abs_url,{}).get('content-type', None)
    get_site_asset(url, link_type)

def get_youtube_video(video_link, video_format, sub_gen):
    # gets video, poster, and any subtitles including autogen
    # formats were precalculated
    # returns url including extension

    video_name = urlparse(video_link).path.split('/')[-1]
    video_id = video_name.split('.')[0]
    video_ext = video_name.split('.')[1]

    asset_file_name = url_to_file_name(video_link, 'video/' + video_ext, incl_query=False)
    vtt_pattern = asset_file_name.replace(video_ext, '*vtt')
    download_file_name = NON_HTML_DOWNLOAD_DIR + asset_file_name
    download_dir = os.path.dirname(download_file_name)
    print("getting", video_link, download_file_name)
    # https://github.com/ytdl-org/youtube-dl/blob/master/README.md#embedding-youtube-dl
    if not os.path.exists(download_file_name):
        download_youtube_video(video_id, video_format, download_dir) # video and poster
        download_youtube_subs(video_id, download_dir) # native subtitles
        if sub_gen:
            download_youtube_auto_sub(video_id, NATIVE_LANGUAGE, download_dir) # one generated subtitle

    dst_file = TARGET_DIR + asset_file_name
    dst_dir = os.path.dirname(dst_file)
    if not os.path.exists(dst_file):
        copy_downloaded_file(download_file_name, dst_file)
        copy_multiple_files(NON_HTML_DOWNLOAD_DIR + vtt_pattern, dst_dir) # do subtitle files

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

def write_conv_html_file(output_file_name, html_output):
    output_dir = os.path.dirname(output_file_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_file_name, 'wb') as f:
        f.write(html_output)

def get_site_asset(url, content_type):
    if not DOWNLOAD_ASSETS:
        return
    asset_file_name = url_to_file_name(url, content_type)
    download_file_name = NON_HTML_DOWNLOAD_DIR + asset_file_name
    print("getting", url, download_file_name)
    if not os.path.exists(download_file_name):
        download_binary_url(url, download_file_name)
    dst_file = TARGET_DIR + asset_file_name
    if not os.path.exists(dst_file):
        if os.path.exists(download_file_name): # in case could not be downloaded or doesn't exist at source
            copy_downloaded_file(download_file_name, dst_file)

def get_course_index_head_lines():
    head_lines = '''
    <link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/tutorial.concat.css">

    <style>
    @media only screen and (min-width: 960px) {
    #content-area {
    width: 960px;
    margin: 0 auto;
    }
    }
    </style>
    '''
    #<link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/alltopics.concat.css">
    #<script src="https://edu.gcfglobal.org/scripts/deployment-es/alltopics.concat.js" type="text/javascript"></script>
    return head_lines

def get_head_lines():
    head_lines = '''
    <link rel="stylesheet" href="https://edu.gcfglobal.org/styles/deployment-es/lessonpage-es.concat.css">
    <style>
    @media only screen and (min-width: 960px) {
    #content-area {
    width: 960px;
    margin: 0 auto;
    }
    }
    @media only screen and (max-width :960px){
    .mobile-video{
    height: auto !important;
    width: 100% !important;
    }
    }
    </style>
    '''
    return head_lines

def get_logo_lines(link='#'):
    logo_lines = '<div style="margin-left:20px;">'
    logo_lines += '<a class="logo-link" href="' + START_PAGE + '">'
    logo_lines += '<img style="height:50px;" class="logo logo-left main-logo-es" src="/assets/gcfglobal-color.png"></a>'
    logo_lines += '<a class="logo-link" href="' + link + '">'
    logo_lines += '<img style="height:60px;" class="logo logo-middle logo-es" src="/assets/logo-es.svg"></a>'
    logo_lines += '</div>'

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert downloaded html. By default downloads asset files")
    parser.add_argument("-n", "--nodownload", help="don't download assets", action="store_true")
    args = parser.parse_args()
    main(args)
