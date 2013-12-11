# -*- coding: utf-8 -*-

import re
import os
import sys
import time
import json
import urllib
import urllib2
import urlparse
from gzip import GzipFile
from StringIO import StringIO


def deflate(data):   # zlib only provides the zlib compress format, not the deflate format;
    # deflate support
    import zlib

    try:               # so on top of all there's this workaround:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except zlib.error:
        return zlib.decompress(data)


def wlog(msg):
    """
    日志

    @param msg  日志内容
    """
    print "[%s] %s" % (t2date(time.time(), '%X'), msg)


def t2date(timestamp, format="%Y-%m-%d %X"):
    """
    转换时间戳为字符串

    @param timestamp    时间戳
    @param format       格式化字符串
    """
    return time.strftime(format, time.localtime(timestamp))


def json_decode(text):
    """
    json_decode

    @param text     json string
    @return dict    dict

    """
    if (re.search(r'''^("(\\.|[^"\\\n\r])*?"|[,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t])+?$''', text) == None): return None
    return json.loads(text)


def mid(content, start, end=None, clear=None):
    """
    字符串截取函数

    @param content      内容
    @param start        开始字符串   以括号"("开始且结尾的则按照正则表达式执行
    @param end          结束字符串   以括号"("开始且结尾的则按照正则表达式执行
    @param clear        清理
    @return string      截取之后的内容

    """

    if len(content) == 0 or len(start) == 0: return ''

    # start
    if start[0] == '(' and start[-1] == ')':
        start = re.search(start, content, re.I)
        if start == None:
            return ''
        else:
            start = start.group()

    # end
    if end and end[0] == '(' and end[-1] == ')':
        end = re.search(end, content, re.I)
        if end == None:
            end == ''
        else:
            end = end.group()

    # find start
    start_pos = content.find(start)
    if start_pos == -1 or end == '': return ''
    # substr
    if end == None:
        content = content[start_pos:]
    else:
        start_len = len(start)
        end_pos = content[start_pos + start_len:].find(end)
        if end_pos == -1:
            return ''
        else:
            content = content[start_pos + start_len: end_pos + start_pos + start_len]

    # clear
    if isinstance(clear, list) or isinstance(clear, tuple):
        for rule in clear:
            if rule[0] == '(' and rule[-1] == ')':
                content = re.sub(rule, '', content, re.I | re.S)
            else:
                content = content.replace(rule, '')
    elif clear != None:
        if clear[0] == '(' and clear[-1] == ')':
            content = re.sub(clear, '', content, re.I | re.S)
        else:
            content = content.replace(clear, '')

    return content


def format_url(base_url, html):
    """
    格式化URL

    @param base_url     基础URL
    @param html         html内容
    @return string      处理之后的html
    """
    urls = []
    matches = re.findall(r'''(<(?:a|link)[^>]+?href=([^>\s]+)[^>]*>)''', html, re.I)
    if matches != None:
        for url in matches:
            if (url in urls) == False:
                urls.append(url)

    matches = re.findall(r'''(<(?:img|script)[^>]+?src=([^>\s]+)[^>]*>)''', html, re.I)
    if matches != None:
        for url in matches:
            if (url in urls) == False:
                urls.append(url)

    if urls.count == 0: return html
    # parse url
    aurl = urlparse.urlparse(base_url)
    # base host
    base_host = "%s://%s" % (aurl.scheme, aurl.netloc)
    # base path
    if aurl.path:
        base_path = os.path.dirname(aurl.path) + '/'
    else:
        base_path = '/'
        # base url
    base_url = base_host + base_path
    # foreach urls
    for tag in urls:
        url = tag[1].strip('"').strip("'")
        # url empty
        if url == '': continue
        # http https ftp skip
        if re.search(r'''^(http|https|ftp)\:\/\/''', url, re.I): continue
        # 邮件地址,javascript,锚点
        if url[0] == '#' or url[0:7] == 'mailto:' or url[0:11] == 'javascript:': continue
        # 绝对路径 /xxx
        if url[0] == '/':
            url = base_host + url

        # 相对路径 ../xxx
        elif url[0:3] == '../':
            while url[0:3] == '../':
                url = url[3:]
                if len(base_path) > 0:
                    base_path = os.path.dirname(base_path)
                    if base_path == '/': base_path = ''

                if url == '../':
                    url = ''
                    break

            url = base_host + base_path + '/' + url
        # 相对于当前路径 ./xxx
        elif url[0:2] == './':
            url = base_url + url[2:]
        # 其他
        else:
            url = base_url + url
            # 替换标签
        href = tag[0].replace(tag[1], '"%s"' % (url))
        html = html.replace(tag[0], href)

    return html


def clear_space(html):
    """
    清除html代码里的多余空格

    @param html     html
    @return string  html
    """
    if len(html) == 0: return ''
    html = re.sub('\r|\n|\t', '', html)
    while html.find("  ") != -1 or html.find('&nbsp;') != -1:
        html = html.replace('&nbsp;', ' ').replace('  ', ' ')
    return html


def get_urls(html):
    """
    取得所有连接

    @param html     html内容
    @return array   url list
    """
    urls = []
    if len(html) == 0: return urls
    matches = re.findall(r'''<a[^>]+href=([^>\s]+)[^>]*>''', html, re.I)
    if matches != None:
        for href in matches:
            url = href.strip('"').strip("'")
            if url == '' or url == '#': continue
            anchor = url.find('#')
            if anchor != -1:
                url = url[0:anchor]
            urls.append(url)

    return urls

# 抓取页面
def fetch(url, data=None):
    urls = urlparse.urlparse(url)
    if data != None:
        data = urllib.urlencode(data)
    http = urllib2.urlopen(urllib2.Request(url, data=data, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0) Gecko/20100101 Firefox/25.0',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'http://%s' % (urls.hostname)
    }), timeout=10)

    content = ''

    if (http.code == 200):
        content_encoding = http.headers.get('Content-Encoding')
        content_type = http.headers.get('Content-Type')
        if content_encoding == 'gzip':
            content = GzipFile(fileobj=StringIO(http.read()), mode='r').read()
        elif content_encoding == 'deflate':
            content = StringIO(deflate(http.read())).getvalue()
        else:
            content = http.read()

        charset = 'utf-8'
        re_charset = re.compile(r'''charset=([^$]+)''', re.I).findall(content_type)

        if re_charset != None and len(re_charset) > 0:
            charset = re_charset[0]
        elif len(content) > 0:
            re_charset = re.compile(r'''<meta[^>]+charset=([^'"]+)''', re.I).findall(content_type)
            if re_charset != None and len(re_charset) > 0:
                charset = re_charset[0]

        if charset != 'utf-8':
            content = content.decode(charset, 'ignore').encode('utf-8')

    return content


'''------------------------------------------------- coding... ------------------------------------------------------'''

try:
    import xbmc, xbmcplugin, xbmcgui

    xbmc_loaded = True
except Exception:
    xbmc_loaded = False

try:
    plugin_url = sys.argv[0]
    handle = int(sys.argv[1])
    params = dict(urlparse.parse_qsl(sys.argv[2].lstrip('?')))
except Exception:
    plugin_url = 'plugin://plugin.video.qq/'
    handle = 0
    params = {}

wlog(params)

CURRENT_YEAR = int(t2date(time.time(), '%Y'))
PAGE_SIZE = '20'

MOVIE_TYPE_LIST = [
    ['全部', '-1'], ['动作', '0'], ['冒险', '1'], ['喜剧', '3'], ['爱情', '2'], ['战争', '5'], ['恐怖', '6'], ['犯罪', '7'],
    ['悬疑', '8'], ['惊辣', '9'], ['武侠', '10'], ['科幻', '4'], ['音乐', '19'], ['歌舞', '20'], ['动画', '16'], ['奇幻', '17'],
    ['家庭', '18'], ['剧情', '15'], ['伦理', '14'], ['记录', '22'], ['历史', '13'], ['传记', '24'], ['院线', '25']
]
MOVIE_AREA_LIST = [
    ['全部', '-1'], ['内地', '0'], ['香港', '1'], ['台湾', '9'], ['日本', '4'], ['韩国', '3'], ['美国', '6'], ['印度', '2'],
    ['泰国', '10'], ['欧洲', '5'], ['其他', '9999']
]
MOVIE_YEAR_LIST = [['全部', '-1']]
for year in range(CURRENT_YEAR, 2003, -1):
    MOVIE_YEAR_LIST.append([str(year), str(year)])
MOVIE_YEAR_LIST.append(['其他', '9999'])

TV_TYPE_LIST = [
    ['全部', '-1'], ['偶像', '1'], ['喜剧', '2'], ['爱情', '3'], ['都市', '4'], ['古装', '5'], ['武侠', '6'], ['历史', '7'],
    ['警匪', '8'], ['家庭', '9'], ['神话', '10'], ['剧情', '11'], ['悬疑', '12'], ['战争', '13'], ['军事', '14'], ['犯罪', '15'],
    ['情景', '16'], ['谍战', '17'], ['片花', '18'], ['魔幻', '19'], ['动作', '20'], ['网络剧', '21']
]
TV_AREA_LIST = [
    ['全部', '-1'], ['内地', '0'], ['美国', '8'], ['英国', '1'], ['台湾', '4'], ['韩国', '5'], ['其他', '9999']
]
TV_YEAR_LIST = [['全部', '-1']]
for year in range(CURRENT_YEAR, 2009, -1):
    TV_YEAR_LIST.append([str(year), str(year)])
TV_YEAR_LIST.append(['其他', '9999'])

ORDER_LIST = [['最热', '1'], ['好评', '2'], ['最新', '0']]


def get_movie_url(bClass=1, vType='-1', vArea='-1', vYear='-1', vOrder='1', vPage='0', vPageSize=PAGE_SIZE, vVType='0',
                  vActorRank='-1'):
    """
    1. 大分类：电影、电视剧
    2. 按类型：动作、冒险
    3. 按地区：内地、香港
    4. 按年份：2013
    5. 排序规则：0=最新、1=最热、2=好评
    6. 显示方式：0=海报、1=详情
    7. 当前页数：从0开始
    8. 每页显示多少个
    9. 按分类：免费、会员、预告片、微电影
    10. 热门人物标签排名
    11. 是否收费：1=收费、0=免费
    """
    return "http://v.qq.com/list/%s_%s_%s_%s_%s_0_%s_%s_%s_%s_0.html" % (
        bClass, vType, vArea, vYear, vOrder, vPage, vPageSize, vVType, vActorRank)


def get_TV_url(bClass=2, vType='-1', vArea='-1', vYear='-1', vOrder='1', vPage='0', vPageSize=PAGE_SIZE,
               vActorRank='-1'):
    """
    1. 大分类：电影、电视剧
    2. 按类型：动作、冒险
    3. 按地区：内地、香港
    4. 按年份：2013
    5. 排序规则：0=最新、1=最热、2=好评
    6. 显示方式：0=海报、1=详情
    7. 当前页数：从0开始
    8. 每页显示多少个
    9. 没用
    10. 热门人物标签排名
    11. 是否收费：1=收费、0=免费
    """
    return "http://v.qq.com/list/%s_%s_%s_%s_%s_0_%s_%s_-1_%s_0.html" % (
        bClass, vType, vArea, vYear, vOrder, vPage, vPageSize, vActorRank)

# 首页
def index():
    global MOVIE_TYPE_LIST, TV_TYPE_LIST

    # 输出电影菜单
    url = plugin_url + '?act=select&type=movie'
    wlog("index.url: 电影 %s" % (url,))
    if xbmc_loaded: xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('【电影】 - 点击这里进行筛选：类型、地区、年份...'), True)
    # 输出电影子菜单
    for vtype in MOVIE_TYPE_LIST:
        url = plugin_url + '?act=list_channel&type=movie&url=' + get_movie_url(vType=vtype[1])
        typename = '    |-- ' + vtype[0]
        wlog("index.url: %s %s" % (typename, url,))
        if xbmc_loaded: xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(typename), True)

    # 输出电视剧菜单
    url = plugin_url + '?act=select&type=tv'
    wlog("index.url: 电视剧 %s" % (url,))
    if xbmc_loaded: xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('【电视剧】 - 点击这里进行筛选：类型、地区、年份...'), True)
    # 输出电视剧子菜单
    for vtype in TV_TYPE_LIST:
        url = plugin_url + '?act=list_channel&type=tv&url=' + get_TV_url(vType=vtype[1])
        typename = '    |-- ' + vtype[0]
        wlog("index.url: %s %s" % (typename, url,))
        if xbmc_loaded: xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(typename), True)

    if xbmc_loaded:
        xbmcplugin.setContent(handle, 'movies')
        xbmcplugin.endOfDirectory(handle)


# 筛选
def select():
    stype = params['type']
    dialog = xbmcgui.Dialog()
    if stype == 'movie':
        type_list = [x[0] for x in MOVIE_TYPE_LIST]
        wlog('select.type_list: %s' % (type_list, ))
        sel_type = dialog.select('请选择电影类型', type_list)
        wlog('select.sel_type: %s' % (sel_type, ))
        area_list = [x[0] for x in MOVIE_AREA_LIST]
        wlog('select.area_list: %s' % (area_list, ))
        sel_area = dialog.select('请选择电影地区', area_list)
        wlog('select.sel_area: %s' % (sel_area, ))
        year_list = [x[0] for x in MOVIE_YEAR_LIST]
        wlog('select.year_list: %s' % (year_list, ))
        sel_year = dialog.select('请选择电影年份', year_list)
        wlog('select.sel_year: %s' % (sel_year, ))
        order_list = [x[0] for x in ORDER_LIST]
        wlog('select.order_list: %s' % (order_list, ))
        sel_order = dialog.select('请选择排序方法', order_list)
        wlog('select.sel_order: %s' % (sel_order, ))
        base_url = get_movie_url(1, MOVIE_TYPE_LIST[sel_type][1], MOVIE_AREA_LIST[sel_area][1],
                                 MOVIE_YEAR_LIST[sel_year][1], ORDER_LIST[sel_order][1])
    elif stype == 'tv':
        type_list = [x[0] for x in TV_TYPE_LIST]
        sel_type = dialog.select('请选择电视剧类型', type_list)
        area_list = [x[0] for x in TV_AREA_LIST]
        sel_area = dialog.select('请选择电视剧地区', area_list)
        year_list = [x[0] for x in TV_YEAR_LIST]
        sel_year = dialog.select('请选择电视剧年份', year_list)
        order_list = [x[0] for x in ORDER_LIST]
        sel_order = dialog.select('请选择排序方法', order_list)
        base_url = get_TV_url(2, TV_TYPE_LIST[sel_type][1], TV_AREA_LIST[sel_area][1], TV_YEAR_LIST[sel_year][1],
                              ORDER_LIST[sel_order][1])

    wlog('select.base_url: %s' % (base_url, ))
    list_channel(base_url, stype)

# 列表页
def list_channel(base_url=None, video_type=None):
    global PAGE_SIZE, params, plugin_url
    if base_url == None:
        base_url = params['url']
    if video_type == None:
        video_type = params['type']
    wlog("list_channel.url: %s" % (base_url,))

    body = fetch(base_url)
    clear_body = clear_space(body)
    wlog("list_channel.body: %s" % (len(body), ))
    #print clear_body
    totalItems = mid(clear_body,
                     r'''(<span\s+?class="mod_pagenav_count2">\s*<span\s+?class="current">[0-9]+</span>/)''', '</span>')
    if totalItems == '': totalItems = 1
    wlog("list_channel.totalItems: %s" % (totalItems, ))
    totalItems = int(totalItems) * int(PAGE_SIZE)
    wlog("list_channel.totalItems * PAGE_SIZE: %s" % (totalItems, ))

    if xbmc_loaded == True:
        url = plugin_url + '?act=select&type=' + video_type
        if video_type == 'movie':
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('【电影】 - 点击这里进行筛选：类型、地区、年份...'), True, totalItems)
        elif video_type == 'tv':
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('【电视剧】 - 点击这里进行筛选：类型、地区、年份...'), True, totalItems)

    video_list = mid(clear_body, '<div class="mod_video_list poster">', '<div class="mod_pagenav" id="pager">')
    wlog("list_channel.video_list: %s" % (len(video_list), ))
    if video_type == 'movie':
        action = 'play_video'
        isList = False
    elif video_type == 'tv':
        action = 'list_video'
        isList = True
        #print video_list
    # <li><a href="http://v.qq.com/cover/d/dk6z4x5v536r3fz.html" class="mod_poster_130" title="一夜惊喜" target="_blank" _hot="movie.image.link.1.1"><img src="http://i.gtimg.cn/qqlive/img/jpgcache/files/qqvideo/d/dk6z4x5v536r3fz_l.jpg" onerror="picerr(this);" alt="一夜惊喜" class="_tipimg" />
    matches = re.compile(
        r'''<li><a[^>]+href="(http\://v\.qq\.com/cover/[^"]+\.html)"[^>]+title="([^"]+)"[^>]*>\s*<img\s+src="([^"]+)"[^>]+class="_tipimg"[^>]*>.+?<strong[^>]*>([\d\.]+)</strong>.+?<p>导演：.+?>(.+?)</a>.+?<p>播放：(.+?)</p>''',
        re.I).findall(video_list)
    for match in matches:
        # [周星驰]功夫 (8.8分，播放703.9万次)
        video_name = "[%s]%s (%s分，播放%s次)" % (match[4], match[1], match[3], match[5],)
        video_url = plugin_url + '?act=' + action + '&name=' + match[1] + '&type=' + video_type + '&url=' + match[0]
        if xbmc_loaded == True:
            li = xbmcgui.ListItem(video_name, thumbnailImage=match[2])
            li.setProperty('mimetype', 'video/x-msvideo') #防止列出视频时获取mime type
            li.setProperty('IsPlayable', 'true') #setResolvedUrl前必需
            xbmcplugin.addDirectoryItem(handle, video_url, li, isList, totalItems)

        wlog("%s %s %s %s %s %s" % match)

    pager_list = mid(body, '<div class="mod_pagenav" id="pager">', '</div>')
    pager_list = re.subn(r'''<span\s*class="current"><span>([0-9]+?)</span></span>''',
                         r'''<a href="#current">\1</a>''', pager_list)[0]
    wlog("list_channel.pager_list: %s" % (len(pager_list), ))

    matches = re.compile(r'''<a[^>]+href=([^>\s]+)[^>]*>(.+?)</a>''', re.I).findall(pager_list)
    for href in matches:
        list_name = re.subn(r'''(<span[^>]*>|</span>)''', '', href[1])[0]
        if list_name.isdigit():
            list_name = "第%s页" % (list_name, )
        list_url = href[0].strip('"')
        url = plugin_url + '?act=list_channel&type=' + video_type + '&url=' + list_url

        if list_url == '#current':
            list_name = '[COLOR FFFF0000]' + list_name + '[/COLOR]'
            is_dir = False
        else:
            is_dir = True

        if xbmc_loaded == True:
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(list_name), is_dir, totalItems)

        wlog("list_channel.href: %s %s" % (list_name, list_url,))

    if xbmc_loaded == True:
        xbmcplugin.setContent(handle, 'movies')
        xbmcplugin.endOfDirectory(handle)


# 电视剧集数列表
def list_video():
    global params, plugin_url
    base_url = params['url']
    wlog("list_video.url: %s" % (base_url,))

    video_type = params['type']
    wlog("list_video.type: %s" % (video_type,))

    body = fetch(base_url)
    clear_body = clear_space(body)
    wlog("list_video.body: %s" % (len(body), ))

    clear_body = format_url(base_url, clear_body)
    video_list = mid(clear_body, '<div id="mod_videolist">', '</div></div></div></div>')
    wlog("play_video.video_list: %s" % (len(video_list), ))

    if len(video_list) > 0:
        video_name = params['name']
        wlog("play_video.name: %s" % (video_name,))

        video_pic = mid(clear_body, ',pic :"', '"').strip()
        wlog("play_video.pic: %s" % (video_pic,))
        matches = re.compile(r'''<li[^>]*><a[^>]+href=([^>\s]+)[^>]*>(.+?)</a></li>''', re.I).findall(video_list)
        totalItems = len(matches)
        for href in matches:
            SE_Url = href[0].strip('"')
            SE_Name = re.subn(r'''<[^>]*>''', r'', href[1].strip())[0]
            video_url = plugin_url + '?act=play_video&type=' + video_type + '&url=' + SE_Url
            if xbmc_loaded == True:
                li = xbmcgui.ListItem(video_name + ' 第 ' + SE_Name + '集', thumbnailImage=video_pic)
                li.setProperty('mimetype', 'video/x-msvideo') #防止列出视频时获取mime type
                li.setProperty('IsPlayable', 'true') #setResolvedUrl前必需
                xbmcplugin.addDirectoryItem(handle, video_url, li, False, totalItems)

            wlog("play_video.SE_Name: %s" % ('第 ' + SE_Name + '集', ))
            wlog("play_video.SE_Url: %s" % (SE_Url, ))
            wlog("play_video.video_url: %s" % (video_url, ))

    else:
        try:
            isLocation = clear_body.index('r.replace("/cover/","/prev/");')
        except ValueError:
            isLocation = -1

        if isLocation > -1:
            base_url = params['url'].replace(r'/cover/', r'/prev/')
            wlog("list_video.url: %s" % (base_url,))

            body = fetch(base_url)
            clear_body = clear_space(body)
            clear_body = format_url(base_url, clear_body)
            wlog("list_video.body: %s" % (len(body), ))

        video_fragments = mid(clear_body, '<div class="mod_video_fragments">', '</ul>')

        matches = re.compile(r'''<li[^>]*><a[^>]+href=([^>\s]+)[^>]*>.+?src="(.+?)".+?alt="(.+?)"[^>]*>.+?</li>''',
                             re.I).findall(video_fragments)
        totalItems = len(matches)
        for href in matches:
            SE_Url = href[0].strip('"')
            SE_Name = re.subn(r'''<[^>]*>''', r'', href[2].strip())[0]
            SE_Pic = href[1]
            video_url = plugin_url + '?act=play_video&type=' + video_type + '&url=' + SE_Url
            if xbmc_loaded == True:
                li = xbmcgui.ListItem(SE_Name, thumbnailImage=SE_Pic)
                li.setProperty('mimetype', 'video/x-msvideo') #防止列出视频时获取mime type
                li.setProperty('IsPlayable', 'true') #setResolvedUrl前必需
                xbmcplugin.addDirectoryItem(handle, video_url, li, False, totalItems)

            wlog("play_video.SE_Name: %s" % (SE_Name, ))
            wlog("play_video.SE_Url: %s" % (SE_Url, ))
            wlog("play_video.SE_Pic: %s" % (SE_Pic, ))
            wlog("play_video.video_url: %s" % (video_url, ))

    if xbmc_loaded == True:
        xbmcplugin.setContent(handle, 'movies')
        xbmcplugin.endOfDirectory(handle)

# 播放视频
def play_video():
    global params, plugin_url
    base_url = params['url']
    wlog("play_video.url: %s" % (base_url,))

    video_type = params['type']
    wlog("play_video.type: %s" % (video_type,))

    body = fetch(base_url)
    clear_body = clear_space(body)
    wlog("play_video.body: %s" % (len(body), ))

    video_name = mid(clear_body, '<h1 class="mod_player_title">', '</h1>', r'''(<strong[^>]*>|</strong>)''').strip()
    wlog("play_video.name: %s" % (video_name,))

    video_pic = mid(clear_body, ',pic :"', '"').strip()
    wlog("play_video.pic: %s" % (video_pic,))

    video_vid = mid(clear_body, 'vid:"', '"')
    wlog("play_video.video_vid: %s" % (video_vid,))

    video_fmt = 'shd'
    getinfo = fetch('http://vv.video.qq.com/getinfo', {
        'vids': video_vid,
        'otype': 'json',
        'defaultfmt': video_fmt,
    })
    getinfo = getinfo.replace('QZOutputJson=', '').rstrip(';')
    getinfo = json_decode(getinfo)
    getinfo = getinfo['vl']['vi'][0]
    video_host = getinfo['ul']['ui'][0]['url']
    video_list = getinfo['cl']['ci']

    urls = []
    for ci in video_list:
        iformat = mid(ci['keyid'], '.', '.')
        keyid = re.subn(r'''\.10''', r'''.p''', ci['keyid'], 1)[0]
        filename = keyid + '.mp4'
        getkey = fetch('http://vv.video.qq.com/getkey', {
            'format': iformat,
            'otype': 'json',
            'filename': filename,
            'vid': video_vid,
        })
        getkey = getkey.replace('QZOutputJson=', '').rstrip(';')
        getkey = json_decode(getkey)
        video_downurl = "%s%s?type=mp4&vkey=%s&level=%s&fmt=%s" % (
            video_host, filename, getkey['key'], getkey['level'], video_fmt)
        wlog("play_video.video_downurl: %s" % (video_downurl,))
        urls.append(video_downurl)

    stackurl = 'stack://' + ' , '.join(urls)
    wlog("play_video.stackurl: %s" % (stackurl,))

    if xbmc_loaded:
        xbmcplugin.setResolvedUrl(handle, True, xbmcgui.ListItem(video_name, path=stackurl, thumbnailImage=video_pic))


{
    'index': index,
    'select': select,
    'list_channel': list_channel,
    'list_video': list_video,
    'play_video': play_video,
}[params.get('act', 'index')]()
