# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import re
import string
import difflib
import HTMLParser
import time
import urllib2

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('path')), 'utf-8')
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__resource__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp')), 'utf-8')



if xbmcvfs.exists(__temp__):
    if sys.platform.startswith('win'):
        shutil.rmtree(__temp__)
    else:
        shutil.rmtree(__temp__.encode('utf-8'))
xbmcvfs.mkdirs(__temp__)

sys.path.append(__resource__)

from engchartohan import engtypetokor

base_page = "http://22min.com"
load_page_enum = [1,2,3,4,5,6,7,8,9,10]
load_file_enum = [10,20,30,40,50,60,70,80,90]
max_pages = load_page_enum[int(__addon__.getSetting("max_load_page"))]
max_file_count = load_file_enum[int(__addon__.getSetting("max_load_files"))]
use_titlename = __addon__.getSetting("use_titlename")
user_agent = __addon__.getSetting("user_agent")
use_engkeyhan = __addon__.getSetting("use_engkeyhan")
use_se_ep_check = __addon__.getSetting("use_se_ep_check")

ep_expr = re.compile("\d{1,2}[^\d\s]\d{1,3}")

def prepare_search_string(s):
    s = string.strip(s)
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    return s

# 메인 함수로 질의를 넣으면 해당하는 자막을 찾음.
def get_subpages(query,list_mode=0):
    file_count = 0
    page_count = 1
    newquery = urllib.quote_plus(prepare_search_string(query))
    # first page
    url = base_page+"/?q=%s" % (newquery)
    while page_count<=max_pages and file_count<max_file_count:
        file_count += get_list(url,max_file_count-file_count,list_mode)
        # next page
        page_count+=1
        url = base_page+"/?q=%s&page=%d" % (newquery,page_count)
    return file_count

def check_ext(str):
    ext_str = [".smi",".srt",".sub",".ssa",".ass",".txt"]
    retval = -1
    for ext in ext_str:
        if str.lower().find(ext)!=-1:
            retval=1
            break
    return retval

# 디씨인사이드의 페이지를 파싱해서 파일의 이름과 다운로드 주소를 얻어냄.
def get_files(url):
    ret_list = []
    file_pattern = "<li class=\"[^b][^\"]+\"><a href=\"([^\"]+)\">([^<]+)<"
    req_file = urllib2.urlopen(urllib2.Request(url,headers={'User-Agent': user_agent}))
    content_file = req_file.read()
    files = re.findall(file_pattern,content_file)
    for flink,name in files:
        # 확장자를 인식해서 표시.
        if check_ext(name)!=-1:
            ret_list.append([url, name, flink])
    return ret_list

def check_season_episode(str_title, se, ep):
    result = 0
    re_str = ep_expr.search(str_title)
    new_season = ""
    new_episode = ""    
    if re_str:
        str_temp = re_str.group(0)
        for i in range(0, len(str_temp)):
            c = str_temp[i]
            if c.isdigit():
                       new_season += c
            else:
                break
        for i in range(len(str_temp)-1, -1, -1):
            c = str_temp[i]
            if c.isdigit():
                       new_episode = c + new_episode
            else:
                break
    if new_season=="":
        new_season="0"            
    if new_episode=="":
        new_episode="0"
    if se=="":
        se="0"
    if ep=="":
        ep="0"
    if int(new_season)==int(se):
        result = 1
        if int(new_episode)==int(ep):
            result = 2
    return result

# 22min.com의 페이지의 내용을 추출해서 디씨인사이드의 링크를 얻어냄. 그리고 파일 다운로드를 호출.
def get_list(url, limit_file, list_mode):
    search_pattern = "<a class=\"list-group-item subtitle\" href=\"([^\"]+)\" [^>]+>\s+?<div [^>]+>\s+?<span>([^<]+)</span>"
    req_list = urllib2.urlopen(urllib2.Request(url,headers={'User-Agent': user_agent}))
    content_list = req_list.read()
    result = 0
    # 자막이 없음을 알리는 페이지를 인식.
    if content_list.find("<div class=\"alert alert-warning\">")==-1:
        lists = re.findall(search_pattern,content_list)
        for link, title_name in lists:
            if result<limit_file:
                if use_se_ep_check == "true":
                    if list_mode==1 and 2!=check_season_episode(title_name,item['season'],item['episode']):
                        continue
                link = link.replace("&amp;","&")
                list_files = get_files(link)
                result += len(list_files)
                for furl,name,flink in list_files:
                    listitem = xbmcgui.ListItem(label          = "Korean",
                                                label2         = name if use_titlename == "false" else title_name,
                                                iconImage      = "0",
                                                thumbnailImage = ""
                                                )

                    listitem.setProperty( "sync", "false" )
                    listitem.setProperty( "hearing_imp", "false" )
                    listurl = "plugin://%s/?action=download&url=%s&furl=%s&name=%s" % (__scriptid__,
                                                                                    urllib2.quote(furl),
                                                                                    urllib2.quote(flink),
                                                                                    name
                                                                                    )

                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=listurl,listitem=listitem,isFolder=False)
    else:
        result = 0
    return result

# 디씨인사이드 사이트에서 파일을 다운로드.
def download_file(url,furl,name):
    subtitle_list = []
    local_temp_file = os.path.join(__temp__.encode('utf-8'), name)
    req = urllib2.urlopen(urllib2.Request(furl,headers={'Referer': url, 'User-Agent': user_agent}))
    local_file_handle = open( local_temp_file, "wb" )
    local_file_handle.write(req.read())
    local_file_handle.close()
    subtitle_list.append(local_temp_file)
    return subtitle_list
 
def search(item):
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    lastgot = 0
    list_mode = 0
    if item['mansearch']:
        lastgot = get_subpages(item['mansearchstr'])
        if use_engkeyhan == "true":
            lastgot += get_subpages(engtypetokor(item['mansearchstr']))
    elif item['tvshow']:
        list_mode = 1
        lastgot = get_subpages(item['tvshow'],1)
    elif item['title'] and item['year']:
        lastgot = get_subpages(item['title'])
    if lastgot == 0 and list_mode != 1:
        lastgot = get_subpages(filename)
        
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
        ).encode('ascii', 'ignore')

def get_params(string=""):
    param=[]
    if string == "":
        paramstring=sys.argv[2]
    else:
        paramstring=string
    if len(paramstring)>=2:
        params=paramstring
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]

    return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path of a playing file
    item['3let_language']      = [] #['scc','eng']
    PreferredSub		      = params.get('preferredlanguage')

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        if lang == "Portuguese (Brazil)":
            lan = "pob"
        else:
            lan = xbmc.convertLanguage(lang,xbmc.ISO_639_2)
            if lan == "gre":
                lan = "ell"

    item['3let_language'].append(lan)

    if item['title'] == "":
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)

elif params['action'] == 'download':
    subs = download_file(urllib2.unquote(params['url']),urllib2.unquote(params['furl']),params['name'])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
