#!/usr/bin/python3
import os, string, sys
import copy
import json
import re
import string
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup, Comment, SoupStrainer
from sp_lib import *

site = 'rarediseases.info.nih.gov'

orig_dir = '/articlelibrary/viewarticle/'
base_url = 'https://' + site + orig_dir
download_dir = 'site-download'
dst_dir = '/library/www/html/modules/en-nih_rarediseases'
external_url_not_found = '/not-offline.html'

# read stats
site_urls = read_json_file(site + '_urls.json')
site_redirects = read_json_file(site + '_redirects.json')

disease_catalog = read_json_file('disease-catalog.json')

page_links = {}

def main(argv):
    convert_nav()
    convert_diseases()
    convert_disease_cases()
    convert_glossary()
    convert_glossary_desc()
    convert_es_diseases()
    convert_es_glossary()
    pass

def convert_nav():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/diseases/categories',
               match_prefix + '/diseases/diseases-by-category',
               match_prefix + '/diseases/browse-by-first-letter']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    for url in url_list:
        #read_file_name = url_to_file_name(url, content_type)
        #read_file_path = download_dir + read_file_name

        print('Converting ' + url)

        page, page_file_name = do_nav_page(url, download_dir)
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

def convert_diseases():
    # need site_urls for type of image - see below

    disease_list = [
        "/diseases/6710/hyperprolinemia-type-2",
        "/diseases/1323/chromosome-10p-deletion",
        "/diseases/5299/chromosome-10p-duplication",
        "/diseases/3711/chromosome-10q-deletion",
        "/diseases/8630/chromosome-10q-duplication",
        "/diseases/13018/10q223q23-microdeletion-syndrome",
        "/diseases/9882/cortisone-reductase-deficiency",
        "/diseases/5658/11-beta-hydroxylase-deficiency",
        "/diseases/1732/chromosome-11p-deletion",
        "/diseases/5528/wagr-syndrome",
        "/diseases/10845/chromosome-11p-duplication",
        "/diseases/5784/alpha-1-antitrypsin-deficiency",
        "/diseases/9762/potocki-shaffer-syndrome"]
    disease_list = list(disease_catalog)

    for disease_url in disease_list:
        url = 'https://' + site + disease_url
        print('Converting ' + url)

        page, page_file_name = do_disease_page(url, download_dir)
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

def convert_disease_cases():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/diseases/.+/cases/[0-9]'] # disease cases. exclude some bogus ones
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    for url in url_list:
        #read_file_name = url_to_file_name(url, content_type)
        #read_file_path = download_dir + read_file_name

        print('Converting ' + url)

        page, page_file_name = do_disease_page(url, download_dir)
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

def convert_glossary():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/glossary']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    for url in url_list:
        #read_file_name = url_to_file_name(url, content_type)
        #read_file_path = download_dir + read_file_name

        print('Converting ' + url)

        page, page_file_name = do_glosary_page(url, download_dir)
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

def convert_glossary_desc():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/GlossaryDesc']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    for url in url_list:
        #read_file_name = url_to_file_name(url, content_type)
        #read_file_path = download_dir + read_file_name

        print('Converting ' + url)

        page, page_file_name = do_glosary_desc_page(url, download_dir)
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

# Spanish translations
# diseases are in /espanol/nnnn
# cases in espanol/nnnn  ... cases/nnnn
# nav is /espanol/enfermedades (no by category and alpha are sections in enfermidades)
# glossary in /glosario
# glossay description in /GlossaryDescription

def convert_es_diseases():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [ # diseases, cases, and nav
            match_prefix + '/espanol/[0-9]+/[^.]+$',
            match_prefix + '/espanol/enfermedades'
            ]
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    for url in url_list:
        if is_page_not_found(url):
            continue
        #read_file_name = url_to_file_name(url, content_type)
        #read_file_path = download_dir + read_file_name

        print('Converting ' + url)

        page, page_file_name = do_disease_page(url, download_dir, lang='es')
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

def convert_es_glossary():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/glosario']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    for url in url_list:
        #read_file_name = url_to_file_name(url, content_type)
        #read_file_path = download_dir + read_file_name
        print('Converting ' + url)

        page, page_file_name = do_glosary_page(url, download_dir, lang='es')
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + page_file_name

        write_html_file(output_file_name, html_output)
        print(output_file_name)

def do_disease_page(url, download_dir, lang='en'):
    content_type = site_urls[url]['content-type']
    page_file_name = url_to_file_name(url, content_type)
    input_file_path = download_dir + page_file_name

    with open(input_file_path, 'r') as f:
        html = f.read()

    page = BeautifulSoup(html, "html5lib")
    #page = BeautifulSoup(html, "html.parser")

    css_files = page.find_all('link',{'rel':'stylesheet'})

    for link in css_files:
        link.extract()

    for s in page(["script", "style"]): # remove all javascript and stylesheet code
        s.extract()

    for comments in page.head.findAll(text=lambda text:isinstance(text, Comment)):
        comments.extract()

    for tag in page.find_all('a', class_='need-help'):
        tag.decompose()

    main_content = page.find("div", id = 'MainContent').find('div', class_='row')
    if main_content:
        toolkit = main_content.find('a', class_='anchor-toolkit')
        if toolkit:
            toolkit.parent.parent.decompose() # left nav and body
        # main_content.find('a', class_='anchor-toolkit').parent.parent.decompose() WHY DOUBLED
        #listen_list = main_content.find('a', class_='rsbtn_play')
        for tag in main_content.find_all('a', class_='rsbtn_play'):
            tag.decompose()

        left_nav_block = main_content.find("div", class_='left-menu')
        if left_nav_block:
            left_nav = left_nav_block.ul
            if left_nav:
                left_toc  = left_nav.li
                left_nav.clear()
                left_nav.append(left_toc)

                left_nav_lines = BeautifulSoup(get_left_nav_lines(lang), 'html.parser')
                left_nav.append(left_nav_lines)
        disease_body = main_content.find('div', id='diseasePageContent')
        if disease_body:
            for suggestion in disease_body.select('div[class*="suggestion-"]'):
                #print (suggestion)
                suggestion.decompose()

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

    return page, page_file_name

def do_nav_page(url, download_dir):
    content_type = site_urls[url]['content-type']
    page_file_name = url_to_file_name(url, content_type)
    input_file_path = download_dir + page_file_name

    with open(input_file_path, 'r') as f:
        html = f.read()

    page = BeautifulSoup(html, "html5lib")
    #page = BeautifulSoup(html, "html.parser")

    css_files = page.find_all('link',{'rel':'stylesheet'})

    for link in css_files:
        link.extract()

    for s in page(["script", "style"]): # remove all javascript and stylesheet code
        s.extract()

    for comments in page.head.findAll(text=lambda text:isinstance(text, Comment)):
        comments.extract()

    main_content = page.find("div", id = 'MainContent').find('div', class_='row') #
    left_nav = main_content.find("div", class_='left-menu').ul
    # Remove external links from nav
    left_nav.find('a', string="List of FDA Orphan Drugs").parent.decompose()
    left_nav.find('a', string="GARD Information Navigator").parent.decompose()
    left_nav.find('a', string="FAQs About Rare Diseases").parent.decompose()

    logo_lines = BeautifulSoup(get_logo_lines(), 'html.parser')
    #main_content.div.insert_before(logo_lines)

    page.body.clear()
    page.body.append(logo_lines)
    #page.body.append(left_nav)
    page.body.append(main_content)


    # convert picture links
    #repl_pic_links(page)

    head_lines = BeautifulSoup(get_head_lines(), 'html.parser')

    #print(head_lines)
    bottom_lines = BeautifulSoup(get_bottom_lines(), 'html.parser')
    #print(bottom_lines)

    page.head.append(head_lines)
    page.body.append(bottom_lines)

    page = fix_links(page, url)

    return page, page_file_name

def do_glosary_page(url, download_dir, lang='en'):
    page, page_file_name = do_disease_page(url, download_dir, lang)
    # remove Feedback
    a_tags = page.find_all('a')
    for tag in a_tags:
        if '/Feedback' in tag['href']:
            tag.parent.decompose()

    return page, page_file_name

def do_glosary_desc_page(url, download_dir):
    content_type = site_urls[url]['content-type']
    page_file_name = url_to_file_name(url, content_type)
    input_file_path = download_dir + page_file_name

    with open(input_file_path, 'r') as f:
        html = f.read()

    page = BeautifulSoup(html, "html5lib")
    glossary_detail = page.find("div", class_="main-glossary-detail-container")
    #page = BeautifulSoup(html, "html.parser")
    head_lines_text = '''
    <html>
    <head>
    <link href="/assets/style.css" rel="stylesheet">
    <link href="/assets/style-override.css" rel="stylesheet">
    <style>
    #currentGlossaryText
        {font-weight: 700!important;
        font-size: 18px!important;
        display: block!important;
    }
    .hidden {
        display: block!important;
    }
    </style>
    </head>
    <body>
    '''
    head_lines = BeautifulSoup(head_lines_text, 'html.parser')
    bottom_lines_text = '''
    </body>
    </html>
    '''
    bottom_lines = BeautifulSoup(bottom_lines_text, 'html.parser')
    page.clear()
    page.append(head_lines)
    page.append(glossary_detail)
    page.append(bottom_lines)

    page = fix_links(page, url)

    return page, page_file_name

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
        if tag.has_attr('src'):
            src_path = convert_link(page_url, tag['src'])
            tag['src'] = src_path
        else:
            continue
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
        'https://rarediseases.info.nih.gov/diseases/10193/www.uptodate.com/contents/clinical-manifestations-pathologic-features-and-diagnosis-of-subcutaneous-panniculitis-like-t-cell-lymphoma',
        'https://rarediseases.info.nih.gov/diseases/10340/menieres-disease/cases/www.ncbi.nlm.nih.gov/pubmed/17224529',
        'https://rarediseases.info.nih.gov/diseases/10340/menieres-disease/cases/www.ncbi.nlm.nih.gov/pubmed/7642988',
        'https://rarediseases.info.nih.gov/diseases/10870/https/www.ncbi.nlm.nih.gov/pubmed/28662915',
        'https://rarediseases.info.nih.gov/diseases/13666/www.ncbi.nlm.nih.gov/pubmed/30057031',
        'https://rarediseases.info.nih.gov/diseases/3244/3/31/2015',
        'https://rarediseases.info.nih.gov/diseases/5984/www.ncbi.nlm.nih.gov/books/NBK430816',
        'https://rarediseases.info.nih.gov/diseases/6824/3/3/',
        'https://rarediseases.info.nih.gov/diseases/6824/3/com_contact/Itemid',
        'https://rarediseases.info.nih.gov/diseases/6824/com_contact/Itemid',
        'https://rarediseases.info.nih.gov/diseases/7182/www.ncbi.nlm.nih.gov/pubmed/22986871',
        'https://rarediseases.info.nih.gov/diseases/7182/www.ncbi.nlm.nih.gov/pubmed/26825155',
        'https://rarediseases.info.nih.gov/diseases/7182/www.ncbi.nlm.nih.gov/pubmed/27905021',
        'https://rarediseases.info.nih.gov/diseases/7182/www.ncbi.nlm.nih.gov/pubmed/29159247',
        'https://rarediseases.info.nih.gov/diseases/7182/www.ncbi.nlm.nih.gov/pubmed/30280066',
        'https://rarediseases.info.nih.gov/diseases/7792/tracheoesophegeal fistulawww.nlm.nih.gov/medlineplus/ency/article/002934.htm',
        'https://rarediseases.info.nih.gov/diseases/7792/tracheoesophegeal%20fistulawww.nlm.nih.gov/medlineplus/ency/article/002934.htm',
        'https://rarediseases.info.nih.gov/organizations/742',
        'https://rarediseases.info.nih.gov/espanol/12418/www.galactosemia.es',
        'https://rarediseases.info.nih.gov/espanol/13456/www.scleroderma.org',
        'https://rarediseases.info.nih.gov/espanol/12462/sindrome-de-goldenhar/cases/www.seattlechildrens.org',
        'https://rarediseases.info.nih.gov/espanol/13037/www.facebook.com',
        'https://rarediseases.info.nih.gov/espanol/12926/www.scleroderma.org',
        'https://rarediseases.info.nih.gov/espanol/12374/www.acelaweb.org',
        'https://rarediseases.info.nih.gov/espanol/12374/www.asociacionela.org.ar',
        'https://rarediseases.info.nih.gov/espanol/12374/www.asociacionela.org.ar/www.acelaweb.org',
        'https://rarediseases.info.nih.gov/espanol/12374/www.asociacionela.org.ar/www.asociacionela.org.ar/',
        'https://rarediseases.info.nih.gov/espanol/12809/www.fenaer.es',
        'https://rarediseases.info.nih.gov/espanol/12007/www.lls.org',
        'https://rarediseases.info.nih.gov/espanol/12871/www.laspghan.org',
        'https://rarediseases.info.nih.gov/espanol/11988/www.scleroderma.org',

        'https://rarediseases.info.nih.gov/espanol/12462/sindrome-de-goldenhar/cases/www.seattlechildrens.org/pdf/PE752S.pdf',
        'https://rarediseases.info.nih.gov/espanol/12970/3/3/',
        'https://rarediseases.info.nih.gov/espanol/12970/3/com_contact/Itemid',
        'https://rarediseases.info.nih.gov/espanol/12970/com_contact/Itemid',
        'https://rarediseases.info.nih.gov/espanol/13037/www.facebook.com/miasteniarosario',
        'https://rarediseases.info.nih.gov/organizations/3139',
        'https://rarediseases.info.nih.gov/organizations/3484',
        'https://rarediseases.info.nih.gov/organizations/3831'

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
    <link href="/assets/style.css" rel="stylesheet">
    <link href="/assets/style-override.css" rel="stylesheet">
    '''
    return head_lines

def get_logo_lines():
    logo_lines = '''
    <div>
    <a href="/diseases/browse-by-first-letter/A/index.html"><img class="ncats-logo-image" alt="National Center for Advancing and Translational Sciences" src="/assets/NCATS_Logo.png"></a>
    <img class="gard-logo-image" alt="Genetic and Rare Diseases Information Center, a program of the National Center for Advancing and Translational Sciences" src="/assets/GARD_logo.png">
    </div>
    '''
    return logo_lines

def get_left_nav_lines(lang):
    if lang == 'es':
        left_nav_lines = '''
        <li class="no-children">
        <a href="/espanol/enfermedades">Enfermedades</a>
        </li>
        <li class="no-children">
        <a href="/glosario" target="_self">Navigue el Glosario A-Z</a>
        </li>
        '''
    else:
        left_nav_lines = '''
        <li class="no-children">
        <a href="/diseases/browse-by-first-letter">Browse A-Z</a>
        </li>
        <li class="no-children">
        <a href="/diseases/categories">Find Diseases By Category</a>
        </li>
        <li class="no-children">
        <a href="/glossary" target="_self">Browse Glossary A-Z</a>
        </li>
        '''
    return left_nav_lines

def get_bottom_lines():
    bottom_lines = '''
    '''
    return bottom_lines

if __name__ == "__main__":
    main(sys.argv)
