from bs4 import BeautifulSoup as bs
import re
import requests

def get_stories(soup): 
    stories = []
    title_rows = soup.find_all('td',class_='title')
    for x in title_rows:
        if x.a != None:
            title = x.a.string.strip()
            URL   = x.a['href']
            if str(type(x.span)) == "<type 'NoneType'>":
                com = "NA"
            else: 
                com = ''.join(list(x.span.string.strip())[1:-1])
            item = [title,URL,com]
            stories.append(item)
    return stories[:-1]

def parse_metadata(snip):
    snippet = bs(str(snip))
    try:
        #some posts have no votes
        sub1 = snippet.span.string
        votes = re.search(r'\d+',sub1).group()
    except AttributeError:
        votes = 0
    try:
        sub2 = snippet.span['id']
        iD = re.search(r'\d+',sub2).group()
        sub3 = snippet.find('a',href=u'item?id='+iD).string
        comm_num = re.search(r'\d+|discuss',sub3).group()
    except:
        #some posts have no comments page/id
        iD = '0'
        comm_num = '0'
    if comm_num == u'discuss':
        comm_num = 0
    return [iD,votes,comm_num]

def get_metadata(soup):
    meta_rows = soup.find_all('td',class_='subtext')
    return [parse_metadata(x) for x in meta_rows ]

def get_all(address='http://news.ycombinator.com'):
    headers = {'User-agent': 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0'}
    s = requests.Session()
    r = s.get(address,headers=headers)
    soup = bs(r.text)
    megalist =[]
    stories = get_stories(soup)
    metadata = get_metadata(soup)
    for x in range(0,len(stories)):
        item = {
        'id': metadata[x][0],
        'votes': metadata[x][1],
        'comments': metadata[x][2],
        'title': stories[x][0],
        'url': stories[x][1],
        'comhead': stories[x][2]
        }
        megalist.append(item)
    return megalist



