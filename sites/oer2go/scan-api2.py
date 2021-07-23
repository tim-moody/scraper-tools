#!/usr/bin/python3
# Scan OER2Go
import xml.etree.ElementTree as ET
import json
import csv
import operator
import base64
import os.path
import sys
import shutil
import urllib.request, urllib.error, urllib.parse
import json
import time
import subprocess
import shlex
import uuid
import re
import argparse
import fnmatch
from datetime import date

import iiab.iiab_lib as iiab
import iiab.adm_lib as adm

v2_api = 'http://oer2go.org/cgi/json_api_v2.pl'
v2_catalog = {}
oer2go_duplicates = {'en': [5, 6, 17, 19, 20, 23, 36, 44, 50, 60, 65, 68, 86, 88, 93, 122, 139, 155, 205],
  'es': [26, 49, 51, 53, 58, 59, 61, 63, 66, 69, 72, 75, 94],
  'fr': [],
  'misc': [98,114]}

dup_list = []
for lang in oer2go_duplicates:
    dup_list += oer2go_duplicates[lang]
dup_list = [str(i) for i in dup_list]


skip_zims = ['fr-gutenberg_2021', 'pt-wikipedia_2021', 'hi-phet-zim_2021', 'fr-wikipedia_for_schools_2021', 'de-gutenberg_2021', 'id-wikipedia_2021',
    'en-wikivoyage_2021', 'en-mindfield_2021', 'en-ted_med_2021', 'en-gutenberg_2021', 'id-wikibooks_2021', 'pt-wikibooks_2021', 'es-gutenberg_2021',
    'id-wiktionary_2021', 'fr-wikiversity_2021', 'kn-wikipedia_2021', 'es-wikisource_2021', 'en-crash_course-zim_2021',
    'en-keylearning_resume_building_2021', 'de-wikibooks_2021', 'pt-gutenberg_2021', 'ar-phet-zim_2021', 'fr-wikivoyage_2021',
    'ar-wikiversity_2021', 'fr-wikiquote_2021', 'fr-bouquineux_2021', 'es-wikibooks_2021', 'es-wikipedia_for_schools_2021',
    'de-wikiversity_2021', 'de-wikisource_2021', 'es-phet-zim_2021', 'en-proof_wiki_2021', 'fr-phet-zim_2021', 'es-wiktionary_2021',
    'en-ted_design_2021', 'hi-wikiversity_2021', 'en-keylearning_art_2021', 'fr-wikisource_2021', 'es-wikivoyage_2021', 'id-wikisource_2021',
    'ar-wikisource_2021', 'pt-wiktionary_2021', 'pt-wikiquote_2021', 'en-vikidia_2021', 'en-wikiquote_2021', 'en-wikibooks_2021',
    'pt-phet-zim_2021', 'en-ted_technology_2021', 'fr-wiktionary_2021', 'hi-wikivoyage_2021', 'fr-wikipedia_2021', 'en-wikipedia_for_schools_2021',
    'en-appropedia_2021', 'es-wikiquote_2021', 'kn-wiktionary_2021', 'ar-wikipedia_2021', 'ar-wiktionary_2021', 'en-wikisource_2021',
    'en-wikihow_2021', 'hi-wiktionary_2021', 'en-ted_global_issues_2021', 'ar-wikiquote_2021', 'kn-phet-zim_2021', 'es-wikipedia_2021',
    'de-wikiquote_2021', 'pt-wikiversity_2021', 'fr-wikibooks_2021', 'id-wikiquote_2021', 'de-phet-zim_2021', 'hi-wikibooks_2021',
    'en-wikispecies_2021', 'id-phet-zim_2021', 'hi-wikipedia_2021', 'de-wikipedia_2021', 'en-keylearning_basic_budgeting_2021', 'kn-wikisource_2021',
    'en-wikipedia_2021', 'ar-wikibooks_2021', 'pt-wikivoyage_2021', 'kn-wikiquote_2021', 'ar-gutenberg_2021', 'pt-wikipedia_for_schools_2021',
    'en-ted_ed_2021', 'de-wiktionary_2021', 'hi-wikiquote_2021', 'en-wiktionary_2021', 'es-wikiversity_2021', 'pt-wikisource_2021',
    'en-ted_business_2021', 'fr-ubongo_kids_2021', 'en-phet-zim_2021', 'de-wikivoyage_2021', 'en-ted_most_popular_2021', 'en-ted_science_2021',
    'en-wikiversity_2021']

# ? leave in catalog, but don't download correctly
# these are known, but not sure if they work
# they are not in the v1 catalog
# as of 7/23/2021 they are not in the IIAB module catalog
skip = ['en-BYU_math',
    'es-mineduc',
    'es-appeducativas',
    'es_appeducativas',
    'en-powertyping',
    'fr-wikipedia_for_schools',
    'pt-wikipedia_for_schools',
    'es-wikipedia_for_schools',
    'es-ingles',
    'en-etbooks',
    'en-etvideos'
    ]

new_zims = []

def main():
    global v2_catalog
    global new_zims
    v1_cat = adm.read_json_file('oer2go_catalog-2021-06-22.json')['modules']
    try:
        url_handle = urllib.request.urlopen(v2_api)
        v2_catalog_json = url_handle.read()
        url_handle.close()
        v2_catalog = json.loads(v2_catalog_json)
    except (urllib.error.URLError) as exc:
        print('GET-OER2GO-CAT ERROR - ' + str(exc.reason))
        sys.exit(99)

    for moddir in v2_catalog:
        mod_id = v2_catalog[moddir]['module_id']
        if mod_id in dup_list:
            #print ('skipping ' + moddir)
            continue
        if moddir in v1_cat:
            #print ('skipping ' + moddir)
            continue
        if moddir in skip:
            #print ('skipping ' + moddir)
            continue
        if moddir in skip_zims:
            #print ('skipping ' + moddir)
            continue
        print(mod_id, moddir)
        php = get_index_file(moddir)
        print (php)
        # print(php)
        if "rachel-kiwix-init.php" in php:
            print(moddir + ' is zim: rachel-kiwix-init.php')
            new_zims.append(moddir)
            continue
        if 'zim' in php:
            print(moddir + ' is zim: $zim')
            new_zims.append(moddir)
            continue
    print(new_zims)

def get_index_file(moddir):
    module = {}
    #module = v2_catalog[moddir]
    module['rsync_url'] = 'rsync://dev.worldpossible.org/rachelmods/' + moddir
    module['moddir'] = moddir
    working_dir = 'modules/' + moddir + '/'
    target = working_dir + "rachel-index.php"
    # cmdstr = "rsync -Pavz " + module['rsync_url'] + "/rachel-index.php " + working_dir
    if not os.path.isfile(target):
        cmdstr = "rsync -Pavz " + 'rsync://dev.worldpossible.org/rachelmods/' + moddir + "/rachel-index.php " + working_dir
        args = shlex.split(cmdstr)
        outp = subprocess.check_output(args)
    #adm.generate_module_extra_html(module, working_dir)
    with open(working_dir + "rachel-index.php", 'r') as fp:
        php = fp.read()
    return php

if __name__ == "__main__":
    # Now run the main routine
    main()
