import os, string, sys
import copy
import json
import re
import requests
import shutil
import posixpath
import uuid
from urllib.parse import urljoin, urldefrag, urlparse

def download_urls(url_list, content_type, dest_dir, refresh=False):
    # handles a single content type
    for url in url_list:
        download_file_name = url_to_file_name(url, content_type)
        output_file_name = dest_dir + download_file_name
        if os.path.exists(output_file_name) and not refresh:
            continue

        print('Downloading ' + url)
        if content_type[0:4] == 'text/' or content_type == 'application/javascript':
            text = download_page(url)

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

def should_include_url(url, incl_regex, excl_regex):
    # incl and excl are lists of compiled regex rules
    # see basiccrawler should_ignore_url(self, url) which allows str, pattern, and function
    include_flag = False
    for rg in incl_regex:
        if rg.match(url):
            include_flag = True
            break
    if include_flag:
        for rg in excl_regex:
            if rg.match(url):
                include_flag = False
                break
    return include_flag

def should_ignore_link(link, ignore_list):
    """
    Returns True if `url` matches any of the IGNORE_URL criteria.
    ignore_list elements can be string or compiled regex
    """
    for pattern in ignore_list:
        if isinstance(pattern, str):
            if link == pattern:
                return True
        elif isinstance(pattern, re.Pattern):
            if pattern.match(link):
                return True
        elif callable(pattern):
            if pattern(link):
                return True
        else:
            raise ValueError('Unrecognized pattern in IGNORE_URLS. Use strings, REs, or callables.')

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

def url_to_file_name(url, content_type, url_map=None):
    # url expected to be absolute
    # https://developers.google.com/safe-browsing/v4/urls-hashing as alternative
    if url_map and url in url_map:
        return url_map[url]
    parsed_url = urlparse(url)
    path = parsed_url.path
    query = parsed_url.query
    if query != '':
        query = '?' + query
    ext = path.split('.')[-1]
    if '/' not in ext: # is dot in path or before extension
        return path + query # is path with valid extension
    # Fix up other paths
    # Treat html as directory and others as file name
    if content_type == None:
        return None
    elif content_type == 'text/html':
        ext = '/index.html'
    elif content_type == 'image/jpeg':
        ext = '.jpg'
    elif content_type in ['text/javascript', 'application/javascript']:
        ext = '.js'
    elif '/' in content_type: # skip our pseudo content types like broken-link
        ext = '.' + content_type.split('/')[1]
    else:
        ext = ''
    return path + ext + query

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

def download_page(url):
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

# These are taken from adm cons adm_lib so as not require dependency
def read_json_file(file_path):
    try:
        with open(file_path, 'r') as json_file:
            readstr = json_file.read()
            json_dict = json.loads(readstr)
        return json_dict
    except OSError as e:
        raise

def write_json_file(src_dict, target_file, sort_keys=False):
    try:
        with open(target_file, 'w', encoding='utf8') as json_file:
            json.dump(src_dict, json_file, ensure_ascii=False, indent=2, sort_keys=sort_keys)
            json_file.write("\n")  # Add newline cause Py JSON does not
    except OSError as e:
        raise
