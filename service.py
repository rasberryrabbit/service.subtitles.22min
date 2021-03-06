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
import datetime
import urllib2
import gzip
import zlib
import StringIO
import cookielib
import socket
import httplib
from urlparse import urlparse

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('path')), 'utf-8')
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__resource__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')), 'utf-8')
__resource_dict__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp')), 'utf-8')
time_script_begin = time.time()

def check_script_time():
    _curr_time = time.time();
    return _curr_time - time_script_begin

# prepare cookie url opener
cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener2 = urllib2.build_opener(*handlers)

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'),level=xbmc.LOGERROR)

# remove file and dir with 365 days before / now after time
def clear_tempdir(strpath):
    if sys.platform.startswith('win'):
        workpath=strpath
    else:
        workpath=strpath.encode('utf-8')

    if os.path.exists(workpath):
        try:
            low_time = time.mktime((datetime.date.today() - datetime.timedelta(days=365)).timetuple())
            now_time = time.time()
            for file_name in os.listdir(workpath):
                full_path = os.path.join(workpath, file_name)
                cfile_time = os.path.getmtime(full_path)
                if low_time > cfile_time:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                    #log(__scriptname__,"delete - "+full_path.decode('utf-8'))
        except Exception as e:
            log(__scriptname__,str(e))

clear_tempdir(__temp__)

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
use_engkor_dict = __addon__.getSetting("use_engkor_dict")
file_engkor_dict = __addon__.getSetting("file_engkor_dict")
enable_bunyuc = __addon__.getSetting("enable_bunyuc")
bunyuc_login_id = __addon__.getSetting("bunyuc_id")
bunyuc_login_pass = __addon__.getSetting("bunyuc_pass")
engkor_dict = {}
use_convertsrt = __addon__.getSetting("use_convertsrt")

def dict_read(filename):
    dict = {}
    fin = open(filename, 'r')
    while True:
        line = fin.readline()
        if len(line)==0:
            break
        sh, sd = line.split('=',1)
        sd = sd.strip()
        if len(sd)>0:
            dict[sh]=sd
    fin.close()
    return dict

def find_dict(istr):
    ret = []
    a = istr.split()
    for sstr in a:
        if sstr.lower() in engkor_dict.keys():
            ret.append(engkor_dict[sstr.lower()])
    rs = ' '.join(ret)
    #log(__scriptname__,'find_dict res, %s' % rs.decode("utf-8"))
    return urllib.quote(rs)

# init dictionary
if file_engkor_dict=='':
    file_engkor_dict = os.path.join(__resource_dict__.encode("utf-8"),'engkor_dict.txt')
if use_engkor_dict=='true':
    try:
        engkor_dict = dict_read(file_engkor_dict)
    except:
        use_engkor_dict = 'false'
        log(__scriptname__,'cannot find file %s' % file_engkor_dict)
        pass

ep_expr = re.compile("[\D\S]+(\d{1,2})(\s+)?[^\d\s\.]+(\d{1,3})")
subtitle_txt = re.compile("\d+\:\d+\:\d+\:")
sub_ext_str = [".smi",".srt",".sub",".ssa",".ass",".txt"]

def CheckSUBIsSRT(s):
    m = re.search('\d+\s+\d+\:\d+\:[0-9\,\.]+\s+\-\-\>\s+\d+\:\d+\:[0-9\,\.]+\d+',s)
    return m

def smart_quote(str):
    ret = ''
    spos = 0
    epos = len(str)
    while spos<epos:
        ipos = str.find('%',spos)
        if ipos == -1:
            ret += urllib.quote(str[spos:])
            spos = epos
        else:
            ret += urllib.quote(str[spos:ipos])
            spos = ipos
            ipos+=1
            # check '%xx'
            if ipos+1<epos:
                if str[ipos] in string.hexdigits:
                    ipos+=1
                    if str[ipos] in string.hexdigits:
                        # pass encoded
                        ipos+=1
                        ret+=str[spos:ipos]
                    else:
                        ret+=urllib.quote(str[spos:ipos])
                else:
                    ipos+=1
                    ret+=urllib.quote(str[spos:ipos])
                spos = ipos
            else:
                ret+=urllib.quote(str[spos:epos])
                spos = epos
    return ret

def prepare_search_string(s):
    s = string.strip(s)
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    return s

# 메인 함수로 질의를 넣으면 해당하는 자막을 찾음.
def get_subpages(query,list_mode=0):
    file_count = 0
    page_count = 1
    # 한글은 인코딩되어서 전달됨
    if item['mansearch']:
        newquery = smart_quote(query)
    else:
        newquery = smart_quote(prepare_search_string(query))
    # first page
    url = base_page+"/?q=%s" % (newquery)
    while page_count<=max_pages and file_count<max_file_count:
        if check_script_time()>29.5:
            # log(__scriptname__,"Time Limit Break")
            break
        f_count, l_count = get_list(url,max_file_count-file_count,list_mode)
        file_count += f_count
        if l_count==0:
            break
        # next page
        page_count+=1
        url = base_page+"/?q=%s&page=%d" % (newquery,page_count)
    return file_count

def check_ext(str):
    retval = -1
    for ext in sub_ext_str:
        if str.lower().find(ext)!=-1:
            retval=1
            break
    return retval

def check_ext_pos(str):
    retval = -1
    for ext in sub_ext_str:
        retval=str.lower().find(ext)
        if retval!=-1:
            break
    return retval    

# support compressed content
def decode_content (page):
    encoding = page.info().get("Content-Encoding")    
    if encoding in ('gzip', 'x-gzip', 'deflate'):
        content = page.read()
        if encoding == 'deflate':
            data = StringIO.StringIO(zlib.decompress(content))
        else:
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
        page = data.read()
    else:
        page = page.read()
    return page

def read_url(url):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent',user_agent), ('Accept-Encoding','gzip,deflate')]
    rep = opener.open(url)
    res = decode_content(rep)
    rep.close()
    return res
    
def read_url2(url):
    urlinfo = urlparse(url)
    conn = httplib.HTTPConnection(urlinfo.netloc)
    headers = { "User-Agent" : user_agent, "Accept": "text/plain" }
    conn.request("GET",urlinfo.path+"?"+urlinfo.query,urlinfo.params,headers)
    rsp = conn.getresponse()
    res = rsp.read()
    conn.close()
    return res

# 디씨 웹페이지의 사용된 파일이면 2를 되돌림.
link_idno = '\?id=([^\&]+)\&no=([^\&"]+)'
def check_webfiles(link, pagetxt):
    res = re.search(link_idno,link)
    result = 0
    if res:
        fid = res.group(1)
        fno = res.group(2)
        res2 = re.findall(link_idno, pagetxt)
        if res2:
            for idtxt, notxt in res2:
                if idtxt==fid and notxt==fno:
                    result+=1
    return result

# 디씨인사이드의 페이지를 파싱해서 파일의 이름과 다운로드 주소를 얻어냄.
def get_files(url):
    ret_list = []
    r_isbunyuc = False
    file_pattern = "<li class=\"[^b][^\"]+\"><a href=\"([^\"]+)\">([^<]+)<"
    content_file = read_url2(url)
    files = re.findall(file_pattern,content_file)
    for flink,name in files:
        #if check_webfiles(flink,content_file)<2:
            # 확장자를 인식해서 표시.
            if check_ext_pos(name)!=-1 or name.lower().find('.jpg')!=-1 or name.lower().find('.png')!=-1:
                ret_list.append([url, name, flink])
    # get naver link
    nbloglist=[]
    link_pattern = "<a\s+href=\"([^\"]+)\"\s+target=\"_blank\"\s+class=\"tx\-link\">"
    files = re.findall(link_pattern,content_file,re.IGNORECASE)
    for link in files:
        if link.find("blog.naver.com")!=-1:
            r_isbunyuc = True
            nbloglist.append(link)
            ret_naver = get_files_naver(link)
            for name, flink in ret_naver:
                ret_list.append([link, name, flink])
        else:
            content_file = read_url2(link)
            fwdlink_pattern = "<frame\s+[^>]+\s+src=\'([^\']+)\'"
            framedat = re.findall(fwdlink_pattern,content_file,re.IGNORECASE)
            for framelink in framedat:
                if framelink.find("blog.naver.com")!=-1:
                    r_isbunyuc = True
                    nbloglist.append(framelink)
                    ret_naver = get_files_naver(framelink)
                    for name, flink in ret_naver:
                        ret_list.append([framelink, name, flink])
    # check non-url link
    nblog = re.findall(">([^<]+blog\.naver\.com[^<]+)<",content_file,re.IGNORECASE)
    for nbloglink in nblog:
        InList=False
        for nlink in nbloglist:
            if nlink==nbloglink and nlink!="":
                InList=True
                break
        if InList==False:
            r_isbunyuc = True
            ret_naver = get_files_naver(nbloglink)
            for name, flink in ret_naver:
                ret_list.append([nbloglink, name, flink])
    return ret_list, r_isbunyuc
    
# 번역 포럼의 내용을 파싱해서 파일 이름을과 다운로드 주소를 얻어냄.
def get_files_bun(url):
    ret_list = []    
    file_pattern_bun = "<a\s+class=\"[^\"]+\"\s+href=\"([^\"]+)\"><span\s+class=\"[^\"]+\"><i\s+class=\"[^\"]+\"></i>[^<]+</span><i\s+class=\"[^\"]+\"></i>([^<]+)<"
    content_file_bun = read_url(url)
    files_bun = re.findall(file_pattern_bun,content_file_bun)
    for flink,name in files_bun:
        # 확장자를 인식해서 표시
        epos = check_ext_pos(name)
        if epos!=-1:
            name = name[:epos+4]
            flink = flink.replace("&amp;","&")
            ret_list.append([url, name, flink])
    return ret_list
    
def get_files_me0e(url):
    ret_list = []    
    file_pattern_me0e = "<a\s+class.+href=\"([^\"]+)\"\s+title=\"([^\"]+)\"[^>]+>"
    content_file_me0e = read_url(url)
    files_me0e = re.findall(file_pattern_me0e,content_file_me0e)
    for flink,name in files_me0e:
        # 확장자를 인식해서 표시
        epos = check_ext_pos(name)
        if epos!=-1:
            #name = name[:epos+4]
            flink = flink.replace("&amp;","&")
            ret_list.append([url, name, flink])
    return ret_list
    
def get_files_naver(url):
    ret_naver = []
    frame_pattern="<frame\s+id=\"mainFrame\"[^>]+\s+src=\"([^\"]+)\""
    blog_addr = "http://blog.naver.com"
    content_page = read_url2(url)
    blogframes = re.findall(frame_pattern,content_page)
    item_pattern = "\'encodedAttachFileUrl\'\: \'([^\,]+)\'\,"
    for link in blogframes:
        content_text = read_url2(blog_addr+link)
        flist = re.findall(item_pattern,content_text)
        for flink in flist:
            pos = flink.rfind('/')
            if pos!=-1:
                ret_naver.append([flink[pos+1:], flink])
    return ret_naver

def check_season_episode(str_title, se, ep):
    r = re.findall('(\D+)(\d+)',str_title)
    lmatch = 0
    if r:
        numbers = []
        for mdig in r:
            try:
                newnum = int(mdig[1])
            except:
                newnum=0
            numbers.append(newnum)
        lnum = -1
        if se=="":
            se="0"
        if ep=="":
            ep="0"
        numse = int(se)
        numep = int(ep)
        for num in numbers[::-1]:
            if lnum != -1:
                if num == numse:
                    if lnum == numep:
                        return 2
                    else:
                      lmatch = 1
            lnum = num
    return lmatch
    
def stripextjpg(s):
    rre = re.compile('\.jpg|\.png|\.txt|\.smi|\.srt',re.IGNORECASE)
    return rre.sub('',s)

# 22min.com의 페이지의 내용을 추출해서 링크를 얻어냄. 그리고 링크를 리스트에 추가.
def get_list(url, limit_file, list_mode):
    search_pattern = "<a class=\"list-group-item subtitle\" href=\"([^\"]+)\" [^>]+>\s+?<div [^>]+>\s+?(.+)?\s+?<span>([^<]+)</span>\s+?<span class="
    content_list = read_url(url)
    result = 0
    link_count = 0
    # 링크를 파싱
    lists = re.findall(search_pattern,content_list)
    for link, dummy_vote, title_name in lists:
        if result<limit_file:
            if check_script_time()>29.5:
                # log(__scriptname__,"Time Limit Break")
                break
            link_count+=1
            link = link.replace("&amp;","&")
            try:
                if link.find("bunyuc.com")!=-1:
                    if enable_bunyuc == 'false':
                        continue
                    list_files = get_files_bun(link)
                    isbunyuc = True
                elif link.find("me0e.com")!=-1:
                    if enable_bunyuc == 'false':
                        continue
                    list_files = get_files_me0e(link)
                    isbunyuc = True
                else:
                    list_files, isbunyuc = get_files(link)
                    #isbunyuc = False
            except socket.timeout:
                log(__scriptname__,"socket time out")
                continue
            except Exception as e:
                raise

            for furl,name,flink in list_files:
                if use_se_ep_check == "true":
                    if list_mode==1:
                        ep_check = check_season_episode(title_name,item['season'],item['episode'])
                        ep_check += check_season_episode(name,item['season'],item['episode'])
                        if ep_check < 2:
                            continue
                realfname=name
                extpos=name.rfind('.')
                if extpos!=-1:
                    realext="["+name[extpos+1:]+"]"
                else:
                    realext="[]"
                if not isbunyuc:
                    name=stripextjpg(name)
                result+=1
                labelf=""
                if isbunyuc==True:
                    labelf+="[B]"
                else:
                    labelf+="[D]"
                labelf+=realext
                labelname = realfname if use_titlename == "false" else title_name+" | "+realfname
                listitem = xbmcgui.ListItem(label          = labelf,
                                            label2         = labelname,
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

    return result, link_count

# 디시인사이드 파일 형식 체크
def check_subtitle_file(url,furl,name):
    ret = True
    if check_ext(name)==-1:
        try:
            req = urllib2.urlopen(urllib2.Request(furl,headers={'Referer': url, 'User-Agent': user_agent}))
            # check jpg file
            subbuf = req.read()
            # jpg
            if subbuf[0]==0xff:
                ret = False
            # png
            if subbuf[0]==0x89 and subbuf[1]=='P' and subbuf[2]=='N' and subbuf[3]=='G':
                ret = False
        except:
            ret = False
            pass
    return ret

def milistotime(milis):
    if milis==0:
        rtime="0:00:00,000"
    else:
        rtime=str(datetime.timedelta(milliseconds=milis))[:-3].replace('.',',')
    return rtime

def smitosrt(context):
    if re.search("<sami>",context,re.IGNORECASE):
        tag = re.compile("<sync\s+([^>]+)>",re.IGNORECASE)
        tm = re.compile("start\=(\d+|)",re.IGNORECASE)
        rbuf = ""
        index = 0
        lastpos = 0
        for match in tag.finditer(context):
            tline = tm.search(match.group(1))
            mili = tline.group(1)
            if mili!="":
                cctime = int(mili)
            if index>0:
                try:
                    temp = context[lastpos:match.start()].decode('utf-8')
                except:
                    temp = context[lastpos:match.start()]
                temp = re.sub("<p(\s+[^>]+|)>","",temp,0,re.IGNORECASE)
                rbuf += str(index)+"\n"
                rbuf += milistotime(lasttime) +" --> "+ milistotime(cctime) +"\n"
                temp = re.sub("\n","",temp)
                temp = re.sub("&nbsp;"," ", temp, flags=re.IGNORECASE)
                temp = re.sub("^<br>","",temp, flags=re.IGNORECASE)
                temp = re.sub("<br>","\n",temp, flags=re.IGNORECASE).encode('utf-8')
                if temp=="":
                    temp=" "
                rbuf += temp+"\n"
                rbuf += "\n"
            lasttime = cctime
            lastpos = match.end()
            index+=1
    else:
        rbuf=context
    return rbuf

# 디씨인사이드 사이트에서 파일을 다운로드.
def download_file(url,furl,name):
    subtitle_list = []
    local_temp_file = os.path.join(__temp__.encode('utf-8'), name)
    req = urllib2.urlopen(urllib2.Request(furl,headers={'Referer': url, 'User-Agent': user_agent}))
    # check content on txt and jpg file
    subbuf = req.read()
    subbufchk = subbuf[:500]
    if subbufchk.upper().find("<SAMI")!=-1:
        if use_convertsrt != "false":
            subbuf = smitosrt(subbuf)
            local_temp_file += '.srt'
        else:
            local_temp_file += '.smi'
    else:
        if CheckSUBIsSRT(subbufchk):
            local_temp_file += '.srt'
        else:
            # zip
            if subbufchk[0]=='\x50' and subbufchk[1]=='\x4b' and subbufchk[2]=='\x03' and subbufchk[3]=='\x04':
                local_temp_file += '.zip'
            else:
                # rar
                if subbufchk[0]=='\x52' and subbufchk[1]=='\x61' and subbufchk[2]=='\x72' and subbufchk[3]=='\x21' and subbufchk[4]=='\x1A' and subbufchk[5]=='\x07':
                    local_temp_file += '.rar'
    local_file_handle = open( local_temp_file, "wb" )
    local_file_handle.write(subbuf)
    local_file_handle.close()
    subtitle_list.append(local_temp_file)
    return subtitle_list
    
class MyClass(xbmcgui.WindowDialog):
  def __init__(self, image_url):
    image = xbmcgui.ControlImage(20, 10, 200, 80, image_url)
    self.addControl(image)
    # this shows the window on the screen
    self.show()

  def onAction(self, action):
    # the window will be closed with any key
    #self.close()
    pass
    
def remove_temp_file(folder,sstart,sext,limit):
    buf=[]
    for file in os.listdir(folder):
        if file.startswith(sstart) and file.endswith(sext):
            buf.append(os.path.join(folder,file))
    i=len(buf)
    if i>limit:
        buf.sort
        i-=limit
        for item in buf:
            os.remove(item)
            i-=1
            if i==0:
                break

def make_imgname(dir,base,ext):
    return os.path.join(dir,base+time.strftime("%Y%m%d%H%M%S")+ext)

# 번역 포럼에서 파일을 다운로드
def download_file_bun(url,furl,name):
    g5_cap = "http://bunyuc.com/plugin/kcaptcha"
    g5_cap_ss = g5_cap+ "/kcaptcha_session.php"
    g5_cap_image = g5_cap + "/kcaptcha_image.php?t="
    # downpost_old = "http://bunyuc.com/bbs/download.php?bo_table=jamakboard&wr_id=%s&no=%s"
    downpost = "http://bunyuc.com/bbs/download.php?bo_table=jamakboard&wr_id=%s&no=%s&ds=1&js=on"
    wrid_patt = "wr_id=([^\&]+)"
    fileno_patt = "no=([^\&]+)"
    login_url = "http://bunyuc.com/bbs/login_check.php"
    # init
    subtitle_list = []
    local_temp_file = os.path.join(__temp__.encode('utf-8'), name)
    local_image_file = make_imgname(__temp__.encode('utf-8'), "captcha",".jpg")
    remove_temp_file(__temp__.encode('utf-8'),"captcha",".jpg",100)
    opener2.addheaders = [('User-Agent',user_agent)]
    # login
    if bunyuc_login_id!="" and bunyuc_login_pass!="":
        login_data = urllib.urlencode({'url':'http://bunyuc.com/','mb_id':bunyuc_login_id,'mb_password':bunyuc_login_pass})
        req_login = urllib2.Request(login_url,data=login_data,headers={"Content-type": "application/x-www-form-urlencoded","Referer": url})
        try:
            rex_login = opener2.open(req_login)
        except:
            pass
    # Get cookie
    req1 = urllib2.Request(url,headers={'User-Agent': user_agent})
    res1 = opener2.open(req1)
    # 캡차 코드를 다운로드, 160x60
    req5 = urllib2.Request(g5_cap_ss,headers={"Referer": url})
    rex5 = opener2.open(req5)
    req4 = urllib2.Request(g5_cap_image + "%d" %(time.time()),headers={"Referer": url})    
    rex4 = opener2.open(req4)
    fimg = open(local_image_file,"wb")
    fimg.write(rex4.read())
    fimg.close()
    #show image
    mydisp = MyClass(local_image_file)
    dialog = xbmcgui.Dialog()
    val = dialog.input("Input captcha", type=xbmcgui.INPUT_ALPHANUM).strip()
    mydisp.close()
    del mydisp
    if val=='':
        sys.exit(0)
    # download file
    subfile = re.search(fileno_patt,furl)
    if subfile:
        subfileno = subfile.group(1)
    else:
        subfileno = "0"
    wr_id = re.search(wrid_patt,furl).group(1)
    params = urllib.urlencode({'captcha_key':val})
    req2 = urllib2.Request(downpost %(wr_id,subfileno),data=params,headers={"Content-type": "application/x-www-form-urlencoded","Referer": url})
    res2 = opener2.open(req2)
    """
    req2 = urllib2.Request(furl,headers={'User-Agent': user_agent})
    res2 = opener2.open(req2)
    """
    local_file_handle = open( local_temp_file, "wb" )
    local_file_handle.write(res2.read())
    local_file_handle.close()
    subtitle_list.append(local_temp_file)
    return subtitle_list
 
def search(item):
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    lastgot = 0
    list_mode = 0
    titlename = ''
    if item['mansearch']:
        lastgot = get_subpages(item['mansearchstr'])
        if use_engkeyhan == "true":
            lastgot += get_subpages(engtypetokor(item['mansearchstr']))
    elif item['tvshow']:
        list_mode = 1
        titlename = item['tvshow']
        lastgot = get_subpages(titlename,1)
    elif item['title'] and item['year']:
        titlename = item['title']
        lastgot = get_subpages(titlename)
    #if lastgot == 0 and list_mode != 1:
    #   lastgot = get_subpages(filename)
    if lastgot==0 and use_engkor_dict=='true' and len(titlename)>0:
        titlename = find_dict(titlename).strip()
        if len(titlename)>0:
            lastgot += get_subpages(titlename,list_mode)
        
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
    if params['url'].find("bunyuc.com")!=-1:
        subs = download_file_bun(urllib2.unquote(params['url']),urllib2.unquote(params['furl']),params['name'])
    else:    
        subs = download_file(urllib2.unquote(params['url']),urllib2.unquote(params['furl']),params['name'])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
