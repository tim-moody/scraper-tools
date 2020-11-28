#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Make directories, and store the downloaded zip files based upon category


import os
import sys
import sqlite3
import json
import hashlib
import requests
import subprocess
from subprocess import Popen, PIPE
import zipfile
import pdb; pdb.set_trace()


# Globals
db = object
WORKING_DIR = '/library/working/rachel'
gcf_catalog = {}

class Sqlite():
   def __init__(self, filename):
      self.conn = sqlite3.connect(filename)
      self.conn.row_factory = sqlite3.Row
      self.conn.text_factory = str
      self.c = self.conn.cursor()

   def __del__(self):
      self.conn.commit()
      self.c.close()
      del self.conn

def get_module_json(path):
    with open(path,'r') as fp:
        modules = json.loads(fp.read())
    return modules


def make_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_file(url,todir):
    local_filename = url.split('/')[-1]
    r = requests.get(url)
    f = open(todir + '/' + local_filename, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024): 
        if chunk: 
            f.write(chunk)
    f.close()

def main():
    sql = '''select * from modules order by category'''
    db.c.execute(sql)
    rows = db.c.fetchall()
    category = ''
    for row in rows:
        if row['category'] != category:
            category = row['category']
            print('\n' + category);

        # Use gcf_catalog to trigger update
        if gcf_catalog[row['moddir'] + '-' + row['category']]['requires_update'] == 'True':
            print('%a requires update'%row['moddir'])
            #print('  %s  %s'%(row['moddir'],row['zip_http_url']))
            dest_dir = WORKING_DIR + '/tree/' +  category + '/' + row['moddir'] + '/'
            src_dir = WORKING_DIR + '/zip-files/'
            '''
            if os.path.exists(src_dir + os.path.basename(row['source_url'])):
                print('removing %s'%(src_dir + os.path.basename(row['source_url'])))
                os.remove(src_dir + os.path.basename(row['source_url']))
            make_directory(dest_dir)
            download_file(row['source_url'],src_dir)
            '''
            downloaded = src_dir + os.path.basename(row['source_url'])
            cdir = os.getcwd()
            os.chdir(dest_dir)
            cmd = '/usr/bin/unzip %s '%(downloaded)
            exit_code = subprocess.run(cmd,shell=True)
            print(str(exit_code))

            os.chdir(cdir)
            sys.exit(1)

###########################################################
if __name__ == "__main__":
   ########### get metadata to global space  ##############
   db = Sqlite(WORKING_DIR + '/modules.sqlite')
   gcf_catalog = get_module_json(WORKING_DIR + '/gcf-catalog.json')

   main()
