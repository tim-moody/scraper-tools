import os, string, sys
import copy
import glob
import json
import re
import requests
import shutil
import posixpath
import uuid
import shlex
import subprocess
from urllib.parse import urljoin, urldefrag, urlparse
import youtube_dl

def download_urls(url_list, content_type, dest_dir, refresh=False):
    # handles a single content type
    for url in url_list:
        download_file_name = url_to_file_name(url, content_type)
        output_file_name = dest_dir + download_file_name
        if os.path.exists(output_file_name) and not refresh:
            continue

        print('Downloading ' + url)
        if content_type[0:4] == 'text/' or content_type == 'application/javascript':
            text = lib_download_page(url)

            output_dir = os.path.dirname(output_file_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(output_file_name, 'w') as f:
                f.write(text)
        else:
            download_binary_url(url, output_file_name)

def read_html_file(input_file_path):
    with open(input_file_path, 'r') as f:
        text = f.read()
    return text

def write_html_file(output_file_name, text):
    output_dir = os.path.dirname(output_file_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_file_name, 'w') as f:
        f.write(text)

def download_binary_url(url, output_file_name):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        output_dir = os.path.dirname(output_file_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_file_name, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
    else:
        print('Failed to download ' + url)

def copy_downloaded_file(src_file, dst_file):
    output_dir = os.path.dirname(dst_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    shutil.copy2(src_file, dst_file)

def copy_multiple_files(pattern, dst_dir):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    for file in glob.glob(pattern):
        #print(file)
        shutil.copy(file, dst_dir)

def filter_urls(url_dict, content_type, match_regexes):
    # handles a single content type
    # assumes url_dict has structure of site_urls
    filtered_urls = {}
    matches = []
    for rx in match_regexes:
        matches.append(re.compile(rx))
    for url in url_dict:
        #if not is_url_type(url, content_types, url_dict[url]['content-type']):
        if url_dict[url]['content-type'] != content_type:
            continue
        for rg in matches:
            if rg.match(url):
                filtered_urls[url] = url_dict[url]
                break
            else:
                continue
    return filtered_urls

def is_url_type(url, content_types, url_type):
    for content_type in content_types:
        if url_type == content_type:
            return True
    return False

def should_include_url(url, incl_list, excl_list):
    # incl and excl are lists of string, compiled regex or callables (not currently used)
    # string matches if url starts with it
    include_flag = False
    if match_url(url, incl_list):
        include_flag = True
    if match_url(url, excl_list):
        include_flag = False
    return include_flag

def should_ignore_link(link, ignore_list):
    """
    Returns True if `url` matches any of the IGNORE_URL criteria.
    ignore_list elements can be string, compiled regex or callables (not currently used)
    string matches on equality to link
    """
    return match_url(link, ignore_list, str_equal=True)

def match_url(url, match_list, str_equal=False):
    for pattern in match_list:
        if isinstance(pattern, str):
            if str_equal:
                if url == pattern:
                    return True
            else:
                if url.startswith(pattern):
                    return True
        elif isinstance(pattern, re.Pattern):
            if pattern.match(url):
                return True
        elif callable(pattern):
            if pattern(url):
                return True
        else:
            raise ValueError('Unrecognized pattern in match_list. Use strings, REs, or callables.')

def compile_regex_list(regex_list):
    compiled_list = []
    for rx in regex_list:
        compiled_list.append(re.compile(rx))
    return compiled_list

def source_domain_to_regex(domain_list):
    # parameter must be list, e.g. ['www.x.com']
    regex_list = []
    for domain in domain_list:
        parsed_domain = urlparse(domain)
        if parsed_domain.scheme:
            reg = '^' + parsed_domain.scheme + '://'
        else:
            reg = '^https?://'
        if parsed_domain.netloc:
            reg += parsed_domain.netloc
        else:
            reg += domain
        regex_list.append(reg)
        return regex_list

def url_to_file_name(url, content_type, url_map=None, incl_netloc=True, incl_query=True):
    # url expected to be absolute
    # https://developers.google.com/safe-browsing/v4/urls-hashing as alternative
    #print(url, content_type)
    if url_map and url in url_map:
        return url_map[url]
    parsed_url = urlparse(url)
    if incl_netloc:
        netloc = parsed_url.netloc + '/'
    else:
        netloc = ''
    path = parsed_url.path
    if not path:
        path = '/'
    query = parsed_url.query
    if query != '':
        query = '?' + query
    ext = path.split('.')[-1]
    if '/' not in ext: # is dot in path or before extension
        file_name = netloc + path
        if incl_query:
            file_name += query

        #print(re.sub('/+', '/', file_name))
        return re.sub('/+', '/', file_name) # remove multiple /s
    # Fix up other paths
    # Treat html as directory and others as file name
    if content_type == None:
        return None
    elif content_type == 'text/html':
        ext = '/index.html'
    else:
        if path and path[-1] == '/': # treat final string as name not directory
            path = path[:-1]
        if content_type == 'image/jpeg':
            ext = '.jpg'
        elif content_type == 'image/svg+xml':
            ext = '.svg'
        elif content_type in ['text/javascript', 'application/javascript']:
            ext = '.js'
        elif '/' in content_type: # skip our pseudo content types like broken-link
            ext = '.' + content_type.split('/')[1]
        else:
            ext = ''
    file_name = netloc + path + ext
    if incl_query:
        file_name += query
    #print(re.sub('/+', '/', file_name))
    return re.sub('/+', '/', file_name) # remove multiple /s

# urljoin(abs_url, rel_url') # returns absolute url for relative

def abs_to_rel_url(base_url, target_url):
    # Calculate relative link from one url to another
    # if both or either has no domain assumed to be from same domain

    base=urlparse(base_url)
    target=urlparse(target_url)
    if base.netloc != '' and target.netloc != '' and base.netloc != target.netloc:
        raise ValueError('target and base netlocs do not match')
    base_dir='.'+posixpath.dirname(base.path)
    target='.'+target.path
    return posixpath.relpath(target,start=base_dir)

def anchor_to_span(a_tag, page):
    new_tag = page.new_tag("span")
    new_tag.string = a_tag.string
    # a_tag.replace_with(new_tag)
    return new_tag

def cleanup_url(url):
    """
    Removes URL fragment that falsely make URLs look diffent.
    Subclasses can overload this method to perform other URL-normalizations.
    """
    url = urldefrag(url)[0]
    url_parts = urlparse(url)
    url_parts = url_parts._replace(path=url_parts.path.replace('//','/'))
    return url_parts.geturl()

def lib_download_page(url):
    response = requests.get(url)
    if not response:
        return (None)
    response.encoding = 'utf-8'
    html = response.text
    return (html)

def get_page_not_found(site_url):
    test_url = site_url if site_url[-1] == '/' else site_url + '/'
    test_url += str(uuid.uuid4())
    page_not_found = {}
    r = requests.get(test_url)
    page_not_found['html'] = r.text
    page_not_found['content-length'] = r.headers['content-length']
    return page_not_found

def find_page_not_found(url_dict, page_not_found): # no hits on rarediseases?!
    comp_size = int(page_not_found['content-length'])
    gzip_size = 8690
    for url in url_dict:
        this_size = int(url_dict[url]['content-length'])
        if this_size >= comp_size - 1000 and this_size <= comp_size + 1000:
            print(this_size, comp_size)
        if url_dict[url]['content-length'] == page_not_found['content-length']:
            print(url)

def select_video_format(video_id):
    video_info = get_youtube_video_info(video_id)
    video_formats = get_youtube_video_formats(video_info)
    ext, video_fmt, audio_fmt = select_480p_format(video_formats)
    print(video_fmt, video_formats[video_fmt])
    print(audio_fmt, video_formats[audio_fmt])
    return video_fmt + '+' + audio_fmt

def select_480p_format(video_formats):
    # can have a webm audio format and no webm video format
    webm_audio_fmt, mp4_audio_fmt = select_audio_format(video_formats)
    if webm_audio_fmt: # try webm first
        video_fmt = select_webm_480p_format(video_formats)
        if video_fmt:
            return 'webm', video_fmt, webm_audio_fmt
    if mp4_audio_fmt:
        video_fmt = select_mp4_480p_format(video_formats)
        if video_fmt:
            return 'mp4', video_fmt, mp4_audio_fmt
    return None, None, None # neither found

def select_audio_format(video_formats):
    # select between webm (preferred) and mp4
    webm_audio_fmts = ['249', '250', '171', '251']
    mp4_audio_fmts = ['139', '140', '141']
    webm_audio_fmt = None
    mp4_audio_fmt = None
    for fmt in webm_audio_fmts:
        if fmt in video_formats:
            webm_audio_fmt = fmt
            break
    for fmt in mp4_audio_fmts:
        if fmt in video_formats:
            mp4_audio_fmt = fmt
            break
    return webm_audio_fmt, mp4_audio_fmt

def select_webm_480p_format(video_formats):
    # try known combinations
    # find based on width
    webm_video = ['244']
    for fmt in webm_video:
        if fmt in video_formats:
            video_fmt = fmt
            return video_fmt
    return select_vid_format_by_width(video_formats, 'webm', 900)

def select_mp4_480p_format(video_formats):
    # find based on resolution
    # try known combinations
    video_fmt = select_vid_format_by_res(video_formats, 'mp4', '480p') # try by resolution
    if video_fmt:
        return video_fmt
    video_fmt = select_vid_format_by_width(video_formats, 'mp4', 900) # try by width
    if video_fmt:
        return video_fmt
    mp4_video = ['135'] # try by known format - but can return 240 x 480 instead of 853 x 480
    for fmt in mp4_video:
        if fmt in video_formats:
            video_fmt = fmt
            return video_fmt

def select_vid_format_by_res(video_formats, selected_fmt, resolution):
    video_fmt = None
    for fmt in video_formats:
        if video_formats[fmt]['ext'] != selected_fmt:
            continue
        if video_formats[fmt]['resolution'] == resolution:
            video_fmt = fmt
            break
    return video_fmt

def select_vid_format_by_width(video_formats, selected_fmt, max_width):
    video_fmt = None
    width = 0
    for fmt in video_formats:
        if video_formats[fmt]['ext'] != selected_fmt:
            continue
        if video_formats[fmt]['audio'] != None:
            continue
        fmt_width = video_formats[fmt]['width']
        if fmt_width > max_width:
            continue
        if fmt_width > width:
            width = fmt_width
            video_fmt = fmt
    return video_fmt

def get_youtube_video_formats(video_info):
    mp4_audio = ['139', '140', '141']
    webm_audio = ['249', '250', '171', '251']
    mp4_480p = '83'
    webm_480p = '101'
    video_formats = {}
    formats = video_info['formats']
    for fmt in formats:
        id = fmt['format_id']
        if id in mp4_audio:
            audio = 'mp4'
        elif id in webm_audio:
            audio = 'webm'
        else:
            audio = None
        video_formats[id] = {'ext': fmt['ext'], 'resolution': fmt['format_note'], 'width': fmt['width'], 'height': fmt['height'], 'audio': audio}
    #return dict(sorted(video_formats.items()))
    return video_formats

def get_youtube_subtitles(video_info):
    vtt_subs = []
    subtitles = video_info['subtitles']
    for sub in subtitles:
        tracks = subtitles[sub]
        for track in tracks:
            #print (track['ext'])
            if track['ext'] == 'vtt':
                vtt_subs.append(sub)
    return vtt_subs

def dump_formats(video_id):
    video_info = get_youtube_video_info(video_id)
    video_formats = get_youtube_video_formats(video_info)
    for id in video_formats:
        print(id, video_formats[id])

def get_youtube_video_info(video_id):
    ydl_opts = {
        'writesubtitles': True, #Adds a subtitles file if it exists
        'writeautomaticsub': True, #Adds auto-generated subtitles file
        'subtitle': '--write-sub --all-subs', #writes subtitles file in english
        'subtitlesformat':'vtt', #writes the subtitles file in "srt" or "ass/srt/best"
        'skip_download': True, #skips downloading the video file
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info('https://www.youtube.com/watch?v=' + video_id, download=False)
    return info

def download_youtube_video(video_id, video_format, download_dir):
    # does video and poster
    ydl_opts = {
        'writethumbnail': True,
        'format': video_format,
        'outtmpl': download_dir + '/%(id)s.%(ext)s'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://www.youtube.com/watch?v=' + video_id])

def download_youtube_subs(video_id, download_dir):
    # can't get YTDL api to work
    # download all natural subtitles, not auto generated
    if download_dir[-1] != '/':
        download_dir += '/'
    cmd = 'youtube-dl --skip-download --all-subs -o "' + download_dir + '%(id)s.%(ext)s" ' + video_id
    subproc_run(cmd)

def download_youtube_auto_sub(video_id, lang, download_dir):
    # can't get YTDL api to work
    # download one autogenerated sub
    if download_dir[-1] != '/':
        download_dir += '/'
    cmd = 'youtube-dl --skip-download --write-auto-sub --sub-lang "' + lang + '" -o "' + download_dir + '%(id)s.auto" ' + video_id
    subproc_run(cmd)

def download_youtube_video_files(video_id, ydl_opts, download_dir):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://www.youtube.com/watch?v=' + video_id])

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

# These are taken from adm cons adm_lib so as not require dependency
def read_json_file(file_path):
    try:
        with open(file_path, 'r') as json_file:
            readstr = json_file.read()
            json_dict = json.loads(readstr)
        return json_dict
    except OSError as e:
        print('Unable to read url json file', e)
        raise

def write_json_file(src_dict, target_file, sort_keys=False):
    try:
        with open(target_file, 'w', encoding='utf8') as json_file:
            json.dump(src_dict, json_file, ensure_ascii=False, indent=2, sort_keys=sort_keys)
            json_file.write("\n")  # Add newline cause Py JSON does not
    except OSError as e:
        raise

def print_json(inp_dict):
    json_formatted_str = json.dumps(inp_dict, indent=2)
    print(json_formatted_str)

def human_readable(num):
    '''Convert a number to a human readable string'''
    # return 3 significant digits and unit specifier
    # TFM 7/15/2019 change to factor of 1024, not 1000 to match similar calcs elsewhere
    num = float(num)
    units = ['', 'K', 'M', 'G']
    for i in range(4):
        if num < 10.0:
            return "%.2f%s"%(num, units[i])
        if num < 100.0:
            return "%.1f%s"%(num, units[i])
        if num < 1000.0:
            return "%.0f%s"%(num, units[i])
        num /= 1024.0

def subproc_run(cmdstr, shell=False, check=False):
    args = shlex.split(cmdstr)
    try:
        compl_proc = subprocess.run(args, shell=shell, check=check,
                                    universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        raise
    return compl_proc
