#!/usr/bin/python3

from basicspider.crunch import SpiderCrunch
from basicspider.sp_lib import *

cr = SpiderCrunch()

cr.crunch()

#write_json_file(cr.content_types, 'site_content_types.json')
