#!/usr/bin/python3

# Walk crawl json and add things up

import os,string, sys
import json
import requests
import iiab.adm_lib as adm


site_urls = {}
site_pages = {}
site_redirects = {}
site_ignored_urls = {}
site_error_urls = {}

unique_urls = set()
content_types = {}
case_insensitive = {}
all_pages = {}
broken_links = {}
image_urls = {}
total_bytes = 0

def main(argv):
    global site_urls
    global site_pages
    global site_redirects
    global site_ignored_urls
    global site_error_urls

    # Pass in json file name
    if len(sys.argv) > 1:
        site = sys.argv[1]
    else:
        print('usage: site-analzyer.py <site>')
        sys.exit(1)

    url_json_file = site + '_urls.json'
    page_json_file = site + '_pages.json'
    redirects_json_file = site + '_redirects.json'
    ignored_urls_json_file = site + '_ignored_urls.json'
    error_urls_json_file = site + '_error_urls.json'

    try:
        site_urls = adm.read_json(url_json_file)
        site_pages = adm.read_json(page_json_file)
        site_redirects = adm.read_json(redirects_json_file)
        site_error_urls = adm.read_json(ignored_urls_json_file)
        site_ignored_urls = adm.read_json(error_urls_json_file)
    except:
        print('Unable to read one or more site files')
        sys.exit(1)

    calc_page_children()
    compare_urls() # look for page/url mismatches

    sum_content_types()
    #recursive_visit_extract_urls(channel_dict)

    json_formatted_str = json.dumps(content_types, indent=2)
    print(json_formatted_str)

    for content_type in content_types:
        print (content_type, content_types[content_type]['count'], human_readable(content_types[content_type]['bytes']))

    print ('Total Site Size: ' + human_readable(total_bytes))

def sum_content_types():
    global content_types
    global broken_links
    global total_bytes

    # pass through urls and sum by content type
    for url in site_urls:
        content_type = site_urls[url].get('content-type', None)
        size = int(site_urls[url].get('content-length', 0))
        if content_type not in content_types:
            content_types[content_type] = {'count': 1, 'bytes': size}
        else:
            content_types[content_type]['count'] += 1
            content_types[content_type]['bytes'] += size
            if content_type == "broken-link":
                broken_links[url] = "broken-link"
    for content_type in content_types:
        total_bytes += content_types[content_type]['bytes']

def sum_level1():
    top_level = {}
    for u in site_urls:
        if site_urls[u]['content-type'] != "text/html": continue
        url_parts = urlparse(u)
        top_dir = url_parts.path.split('/')[1].lower()
        if top_dir in top_level:
            top_level[top_dir] +=1
        else:
            top_level[top_dir] =1
    return top_level

def recursive_visit_extract_urls(subtree):
    global unique_urls
    global content_types

    url = subtree['url']
    if url not in unique_urls:
        unique_urls.add(url)
    for child in subtree['children']:
        kind = child['kind']
        if kind == 'PageWebResource':
            recursive_visit_extract_urls(child)
        elif kind == 'MediaWebResource':
            content_type = child.get('content-type', None)
            size = int(child.get('content-length', 0))
            if content_type not in content_types:
                content_types[content_type] = {'count': 1, 'bytes': size}
            else:
                content_types[content_type]['count'] += 1
                content_types[content_type]['bytes'] += size
        else:
            pass # no other types now

def check_lc():
    global case_insensitive
    case_insensitive = {}
    for url in site_urls:
        url_lc = url.lower()
        if url != url_lc:
            r = requests.head(url_lc)
            if int(r.headers['Content-Length']) != site_urls[url]['content-length']:
                print(url, r.headers['Content-Length'], site_urls[url]['content-length'])
            if url_lc not in case_insensitive:
                case_insensitive[url_lc] = 1
            else:
                case_insensitive[url_lc] += 1
                if 'feedback/spanish' not in url:
                    print(url)
                    print (url_lc)
                #print(case_insensitive[url_lc])
    #print_json(case_insensitive)
    for url in case_insensitive:
        if case_insensitive[url] != 1:
            #print (url)
            pass

def compare_urls():
    cnt = 0
    cnt2 = 0
    for u in site_urls:
        if  site_urls[u]["content-type"] != "text/html":
            continue
        if u not in site_pages:
            print ('url not in pages: ' + u)
            cnt += 1
        if u not in all_pages:
            print ('url not in pages or children: ' + u)
            cnt2 += 1
    print ('total urls not in pages: ' + str(cnt))
    print ('total urls not in pages or children: ' + str(cnt2))

def calc_page_children():
    global all_pages

    for p in site_pages:
        all_pages[p] = 1
        for c in site_pages[p]['children']:
            all_pages[c] = 1

def calc_image_sources():
    global image_urls
    for p in site_pages:
        for c in site_pages[p]['children']:
            contyp = site_urls[c]['content-type'].strip()
            if 'image' in contyp:
                u = c
                if c[-1] == '/':
                    u = c[:-1]
                u = u.rpartition('/')[0]
                if u not in image_urls:
                    image_urls[u] = {'count': 1, 'children': {}}
                    image_urls[u]['children'][c] = 1
                else:
                    image_urls[u]['count'] += 1
                    if c in image_urls[u]['children']:
                        image_urls[u]['children'][c] += 1
                    else:
                        image_urls[u]['children'][c] = 1


def print_json(inp_dict):
    json_formatted_str = json.dumps(inp_dict, indent=2)
    print(json_formatted_str)

def read_json(filename):
    try:
        with open(filename) as f:
            return_dict = json.load(f)
    except Exception as e:
        print('Unable to read url json file')
        return_dict = None
    return return_dict

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

def list_type_urls(type):
    for p in site_pages:
        children = site_pages[p]['children']
        for c in children:
            ctype = site_urls[c]['content-type']
            if 'video' in ctype:
                print (p)


if __name__ == "__main__":
    main(sys.argv)
