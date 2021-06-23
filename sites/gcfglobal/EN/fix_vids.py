#!/usr/bin/python3
from _typeshed import NoneType
import os, sys
import copy
import json
import re
import string
import argparse
from urllib.parse import urljoin, urldefrag, urlparse
import requests
import youtube_dl
import basicspider.sp_lib as sp

import glob
import iiab.adm_lib as adm

videos = []
no249 = []
no251 = []
mp4_failed = []

# all these assume we are in /Scrapes/gcf/<lang>/site-download/non-html/www.youtube.com

# read json
videos = adm.read_json('videos.json')

# 249 audio
ydl_opts = {'writethumbnail': False, 'format': '249', 'outtmpl': '249' + '/%(id)s.%(ext)s'}
for file in glob.glob("244/*.webm"):
    #vid_webms.append(file)
    video_id = file.split('/')[-1].split('.webm')[0]
    videos.append(video_id)
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(['https://www.youtube.com/watch?v=' + video_id])
    except:
        print (video_id)
        no249.append(video_id)

# 250/251 audio
ydl_opts = {'writethumbnail': False, 'format': '249/250/251', 'outtmpl': '249' + '/%(id)s.%(ext)s'}
for video_id in no249:
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(['https://www.youtube.com/watch?v=' + video_id])
    except:
        print (video_id)
        no251.append(video_id)

# mp4 audio and video
ydl_opts = {'writethumbnail': False, 'format': '135+139/140', 'outtmpl': 'mp4' + '/%(id)s.%(ext)s'}
for video_id in mp4:
    fmt = select_video_format(video_id)
    ydl_opts['format'] = fmt
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(['https://www.youtube.com/watch?v=' + video_id])
    except:
        print (video_id)
        mp4_failed.append(video_id)

# subtitles
for video_id in videos:
    cmd = 'youtube-dl --skip-download --all-subs -o "embed/%(id)s.%(ext)s" ' + video_id
    adm.subproc_run(cmd)

# autogen subtitles
for video_id in videos:
    if not os.path.exists('embed/' + video_id + '.en.vtt'):
        if not os.path.exists('auto/' + video_id + '.auto.en.vtt'):
            print (video_id + ' no en vtt')
            sp.download_youtube_auto_sub(video_id, 'en', 'auto')

# back out mistake
for video_id in videos:
    if os.path.exists('embed/' + video_id + '.en.vtt'):
        if  os.path.exists('auto/' + video_id + '.auto.en.vtt'):
            os.remove('auto/' + video_id + '.auto.en.vtt')

# es vs es-419
for video_id in videos:
    if os.path.exists('embed/' + video_id + '.es-419.vtt'):
        if os.path.exists('auto/' + video_id + '.es.vtt'):
            print(video_id)

for video_id in videos:
    if os.path.exists('embed/' + video_id + '.es-419.vtt'):
        continue
    if os.path.exists('embed/' + video_id + '.es.vtt'):
        continue
    if os.path.exists('embed/' + video_id + '.auto.es.vtt'):
        continue
    sp.download_youtube_auto_sub(video_id, 'es', 'auto')

# test subtitles
subs = ['yJrpo4udXGU.ar.vtt',
'yJrpo4udXGU.cs.vtt',
'yJrpo4udXGU.de.vtt',
'yJrpo4udXGU.el.vtt',
'yJrpo4udXGU.en-GB.vtt',
'yJrpo4udXGU.en.vtt',
'yJrpo4udXGU.es-419.vtt',
'yJrpo4udXGU.es.vtt',
'yJrpo4udXGU.fi.vtt',
'yJrpo4udXGU.fr.vtt',
'yJrpo4udXGU.hu.vtt',
'yJrpo4udXGU.id.vtt',
'yJrpo4udXGU.ja.vtt',
'yJrpo4udXGU.ko.vtt',
'yJrpo4udXGU.nl.vtt',
'yJrpo4udXGU.pl.vtt',
'yJrpo4udXGU.pt-BR.vtt',
'yJrpo4udXGU.pt-PT.vtt',
'yJrpo4udXGU.ro.vtt',
'yJrpo4udXGU.ru.vtt',
'yJrpo4udXGU.sv.vtt',
'yJrpo4udXGU.th.vtt',
'yJrpo4udXGU.tr.vtt',
'yJrpo4udXGU.vi.vtt',
'yJrpo4udXGU.zh-CN.vtt',
'yJrpo4udXGU.zh-TW.vtt']

for s in subs:
    lang = s.split('.')[1]
    print('<track label="' + lang + '" kind="subtitles" srclang="' + lang + '" src="' + s + '">')

# merge video in 244 with audio in 249 (includes 250/251)
for v in videos:
    if v in mp4:
        continue
    cmd = 'ffmpeg -i 244/' + v + '.webm -i 249/' + v + '.webm -c copy mixed/' + v + '.webm'
    adm.subproc_run(cmd)

# test
video_info = get_youtube_video_info('yJrpo4udXGU')
video_formats = get_youtube_video_formats(video_info)
for id in video_formats:
    print(id, video_formats[id])
select_480p_format(video_formats)
select_vid_format_by_width(video_formats, 'mp4', 900)
select_vid_format_by_res(video_formats, 'mp4', '480p')
select_vid_format_by_res(video_formats, 'webm', '480p')

for v in mp4:
    select_video_format(v)

# video info

video_info = get_youtube_video_info(video_id)
thumbnails = video_info['thumbnails']
video_formats = get_youtube_video_formats(video_info)



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
