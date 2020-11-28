#!/usr/bin/python3
import os, string, sys
import copy
import json
import re
import string
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup, Comment, SoupStrainer
import iiab.adm_lib as adm

site = 'rarediseases.info.nih.gov'

orig_dir = '/articlelibrary/viewarticle/'
base_url = 'https://' + site + orig_dir
src_dir = 'raw/html/'
dst_dir = '/library/www/html/modules/en-nih_rarediseases'

# read urls
url_json_file = site + '_urls.json'
site_urls = adm.read_json(url_json_file)

def main(argv):
    # need site_urls for type of image - see below

    disease_catalog = adm.read_json('disease-catalog.json')

    disease_list = list(disease_catalog)
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
        "/diseases/9762/potocki-shaffer-syndrome"]

    for disease_url in disease_list:
        download_file_name = disease_url[1:].replace('/', '.') + '.html'
        print('Converting ' + download_file_name)

        page = do_page(os.path.join(src_dir, download_file_name))
        html_output = page.encode_contents(formatter='html')
        output_file_name = dst_dir + disease_url + '.html'
        print(output_file_name)

        output_dir = os.path.dirname(output_file_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file_name, 'wb') as f:
            f.write(html_output)

def do_page(path):
    with open(path, 'r') as f:
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
    main_content.find('a', class_='anchor-toolkit').parent.parent.decompose() # left nav and body
    main_content.find('a', class_='anchor-toolkit').parent.parent.decompose()
    listen_list = main_content.find('a', class_='rsbtn_play')
    for tag in main_content.find_all('a', class_='rsbtn_play'):
        tag.decompose()

    left_nav = main_content.find("div", class_='left-menu').ul
    left_toc  = left_nav.li
    left_nav.clear()
    left_nav.append(left_toc)

    left_nav_lines = BeautifulSoup(get_left_nav_lines(), 'html.parser')
    left_nav.append(left_nav_lines)

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

    return page

def replace_links(tag, from_link, to_link=None):
    if not to_link:
        to_link = '..' + from_link
    if to_link[-1] != '/':
        to_link += '/'
    #print('tag before len: ',len(tag))
    #os.path.join(src_dir, filename)
    links = tag.find_all(href=re.compile(from_link))
    for link_tag in links:
        #print(link_tag)
        link = link_tag['href']
        #print(link)
        # make sure this is one of our target links
        parsed_link = urlparse(link)
        if parsed_link.netloc and parsed_link.netloc != site:
            continue
        url = urljoin(base_url, link)
        url = cleanup_url(url) # put url in same format as in json

        content_type = site_urls[url].get('content-type', '')
        content_type = content_type.strip()
        if content_type == 'image/jpeg':
            suffix = 'jpg'
        else:
            suffix = content_type.split('/')[1]
        if link[-1] == '/':
            link = link[:-1]
        filename = link.rsplit('/')[-1]
        if '.' not in filename[:-1]:
            filename += '.' + suffix
        if filename[-1] == '.':
            filename += suffix

        local_file = to_link + filename
        print(local_file)
        link_tag['href'] = link_tag['href'].replace(link, local_file)
        img_link = link_tag.find('img')
        #print(img_link)
        if img_link:
            img_url = img_link['src']
            img_link['src'] = img_link['src'].replace(img_url, local_file)
    #print('tag after len: ',len(tag))
    return tag

######## NOT USED ##################
def repl_pic_links(page):
    pix_links = page.body.find_all(href=re.compile("/pictures/getimagecontent"))
    for pix_link in pix_links:
        link = pix_link['href']
        pix_url = 'https://' + site + link
        content_type = site_urls[pix_url].get('content-type', '')
        content_type = content_type.strip()
        if link[-1] == '/':
            link = link[:-1]
        filename = link.rsplit('/')[-1]
        if content_type == 'image/jpeg':
            filename += '.jpg'
        else:
            filename += '.' + content_type.split('/')[1]
        local_file = '../pictures/' + filename
        #print(local_file)
        pix_link['href'] = pix_link['href'].replace(link, local_file)
        img_link = pix_link.find('img')
        img_url = img_link['src']
        img_link['src'] = img_link['src'].replace(img_url, local_file)

def cleanup_url(url): # in future this will be done in spider
        """
        Removes URL fragment that falsely make URLs look diffent.
        Subclasses can overload this method to perform other URL-normalizations.
        """
        url = urldefrag(url)[0]
        url_parts = urlparse(url)
        url_parts = url_parts._replace(path=url_parts.path.replace('//','/'))
        return url_parts.geturl()

def get_head_lines():
    head_lines = '''
    <link href="../../assets/style.css" rel="stylesheet">
    '''
    return head_lines

def get_logo_lines():
    logo_lines = '''
    <div>
    <img class="ncats-logo-image" alt="National Center for Advancing and Translational Sciences" src="../../assets/NCATS_Logo.png">
    <img class="gard-logo-image" alt="Genetic and Rare Diseases Information Center, a program of the National Center for Advancing and Translational Sciences" src="../../assets/GARD_logo.png">
    </div>
    '''
    return logo_lines

def get_left_nav_lines():
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
