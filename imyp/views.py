from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.utils.timesince import timesince
from django.utils.text import truncate_words
from django.core import serializers
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import urlfetch
from models import *
import sha
import datetime
import random
import logging
from django.core import serializers
from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed


#import forms
import feedparser

SEARCH_MIN_LENGTH = 2
STOP_WORDS = frozenset([
   'a', 'about', 'according', 'accordingly', 'affected', 'affecting', 'after',
   'again', 'against', 'all', 'almost', 'already', 'also', 'although',
   'always', 'am', 'among', 'an', 'and', 'any', 'anyone', 'apparently', 'are',
   'arise', 'as', 'aside', 'at', 'away', 'be', 'became', 'because', 'become',
   'becomes', 'been', 'before', 'being', 'between', 'both', 'briefly', 'but',
   'by', 'came', 'can', 'cannot', 'certain', 'certainly', 'could', 'did', 'do',
   'does', 'done', 'during', 'each', 'either', 'else', 'etc', 'ever', 'every',
   'following', 'for', 'found', 'from', 'further', 'gave', 'gets', 'give',
   'given', 'giving', 'gone', 'got', 'had', 'hardly', 'has', 'have', 'having',
   'here', 'how', 'however', 'i', 'if', 'in', 'into', 'is', 'it', 'itself',
   'just', 'keep', 'kept', 'knowledge', 'largely', 'like', 'made', 'mainly',
   'make', 'many', 'might', 'more', 'most', 'mostly', 'much', 'must', 'nearly',
   'necessarily', 'neither', 'next', 'no', 'none', 'nor', 'normally', 'not',
   'noted', 'now', 'obtain', 'obtained', 'of', 'often', 'on', 'only', 'or',
   'other', 'our', 'out', 'owing', 'particularly', 'past', 'perhaps', 'please',
   'poorly', 'possible', 'possibly', 'potentially', 'predominantly', 'present',
   'previously', 'primarily', 'probably', 'prompt', 'promptly', 'put',
   'quickly', 'quite', 'rather', 'readily', 'really', 'recently', 'regarding',
   'regardless', 'relatively', 'respectively', 'resulted', 'resulting',
   'results', 'said', 'same', 'seem', 'seen', 'several', 'shall', 'should',
   'show', 'showed', 'shown', 'shows', 'significantly', 'similar', 'similarly',
   'since', 'slightly', 'so', 'some', 'sometime', 'somewhat', 'soon',
   'specifically', 'state', 'states', 'strongly', 'substantially',
   'successfully', 'such', 'sufficiently', 'than', 'that', 'the', 'their',
   'theirs', 'them', 'then', 'there', 'therefore', 'these', 'they', 'this',
   'those', 'though', 'through', 'throughout', 'to', 'too', 'toward', 'under',
   'unless', 'until', 'up', 'upon', 'use', 'used', 'usefully', 'usefulness',
   'using', 'usually', 'various', 'very', 'was', 'we', 'were', 'what', 'when',
   'where', 'whether', 'which', 'while', 'who', 'whose', 'why', 'widely',
   'will', 'with', 'within', 'without', 'would', 'yet', 'you'])


def respond(request, template, params=None):
    """Helper function for rendering output with common context"""
    if not users.get_current_user() is None:
        ac = Account.get_account_for_user(users.get_current_user())
    if params is None:
        params = {}
    if users.get_current_user() is None:
        params['auth'] = False
    else:
        params['auth'] = True
    
    if params.has_key('user_focus'):
        if params['user_focus'] == users.get_current_user():
            params['write'] = True
        else:
            params['focus_user'] = users.get_current_user()
    newsitem = NewsItem.all()[:10]
    for item in newsitem:
        if not ('month' in timesince(item.created_on) or 'months' in timesince(item.created_on) or 'year' in timesince(item.created_on) or 'week' in timesince(item.created_on) or 'weeks' in timesince(item.created_on)):
            params['newtab'] = True
            break
    params['types'] = Item.all()
    params['quote'] = RadomQuotes.get_random_quote()
    params['request'] = request
    params['is_admin'] = users.is_current_user_admin()
    params['user'] = users.get_current_user()
    params['signin'] = users.create_login_url(request.path)
    params['signout'] = users.create_logout_url(request.path)
    params['product'] = 'imyp'
    params['revision'] = '52'
    params['stage'] = 'alpha'
    try:
        return render_to_response(template, params)
    #except DeadlineExceededError:
    #    return HttpResponse("DeadlineExceededError")
    except MemoryError:
        logging.exception("MemoryError")
        return HttpResponse("MemoryError")
    except AssertionError:
        logging.exception("Assertion Error")
        return HttpResponse("AssertionError")
    

### Decorators for request handlers ###


def login_required(func):
    """Decorator that redirects to the login page if you're not logged in."""
    def login_wrapper(request, *args, **kwds):
        if users.get_current_user() is None:
            return HttpResponseRedirect(users.create_login_url(request.path))
        return func(request, *args, **kwds)
    return login_wrapper


def admin_required(func):
    def admin_wrapper(request, *args, **kwds):
        """Decorator that insists that you're logged in as administratior."""
        if users.get_current_user() is None:
            return HttpResponseRedirect(users.create_login_url(request.path))
        if not users.is_current_user_admin():
            return HttpResponse('You must be admin in for this function. <a href="%s">Login</a>' %users.create_logout_url(request.path))
        return func(request, *args, **kwds)
    return admin_wrapper
    

def test(request, template="home.html"):
    return respond(request, template)

def icon(request, key):
    if request.GET.has_key('pkey'):
        u = UserItem.get(key)
    else:
        u = UserItem.get_by_key_name(key)
    return HttpResponse(u.icon.icon_src, "image/jpg")

@admin_required
def initial(request):
    """Initialized inital data"""
    a = Item.get_or_insert("writing", title="writing", tab_title="Writing", verbose_title="Written")
    a = Item.get_or_insert("listening", title="listening", tab_title="Listening", verbose_title="Listened")
    a = Item.get_or_insert("viewing", title="viewing", tab_title="Viewing", verbose_title="Viewed")
    a = Item.get_or_insert("reading", title="reading", tab_title="Reading", verbose_title="Read")
    a = NewsItem.get_or_insert("first", title='We just fixed empty news item bug', text='Empty table never gets created in appengine, somewhat it sucks :(')
    return HttpResponse("Done")

def _random_string(num):
    """Generates random string"""
    random_string = ""
    alphArr = ['a', 'd', 'e', 'f', 'h', 'n', 'r', 'A','B','C','D','E','F','G',\
               'H','J','K','L','M','N','P','R','S','T','W','X','Z', 'a', 'd',\
               'e', 'f', 'h', 'n', 'r']
    for i in range(num):
        random_string+=random.choice(alphArr)
    return random_string

def _generic_data_adapter(type_name, user, limit=50):
    """Query Datastore"""
    tp = Item.get_by_key_name(type_name)
    if tp is None:
        return Http404
    try:
        data = UserItem.all().filter('type = ', tp.key()).filter('user = ', user).order('-item_date')[:limit]
        feed = UserFeed.all().filter('type = ', tp.key()).filter('user = ', user)
    except Exception, e:
        logging.exception("Data adapter error %s" % str(e))
    return data, feed


def dispatcher(request, method, user=None, type=None):
    force_add = False
    if user is None:
        user = users.get_current_user()
        if users.get_current_user() is None:
            response = HttpResponse("404!! Dispatcher needs at least one of the entity to dispatch request")
            response.status_code = 404
            return response
    else:
        if not '@' in user:
            user += "@gmail.com"
        ac = Account.get_account_for_email(user)
        if ac is None:
            response = HttpResponse('404!! User doesn\'t Exist')
            response.status_code = 404
            return response
        user = ac.user
    data, feed = _generic_data_adapter(method, user)
    if feed.count() == 0:
        feed_url = 'http'
    else:
        feed_url = feed[0].feed_url
    if len(data) == 0:
        force_add = True
    return respond(request, "generic.html", {'data': data, 'user_focus': user, 'force':force_add, 'feed_url':feed_url, 'event': method})


def user_handler(request, user):
    return HttpResponseRedirect('/u/writing/%s/' % user)

def poke(request, type_name, user):
    "fetch, parse and insert into DB"
    if not '@' in user:
        user += "@gmail.com"
    ac = Account.get_account_for_email(user)
    if ac is None:
        logging.warn("No User")
        response = HttpResponse('404!! User doesn\'t Exist')
        response.status_code = 404
        return response
    user = ac.user
    tp = Item.get_by_key_name(type_name)
    if tp is None:
        logging.warn("No category %s" %type_name)
        response = HttpResponse('404!! Broken url')
        response.status_code = 404
        return response
    feed = UserFeed.all().filter('type = ', tp.key()).filter('user = ', user)
    try:
        url = feed[0].feed_url
    except:
        logging.warn("No feed url")
        response = HttpResponse('404!! Broken url')
        response.status_code = 404
        return response
    if "?" in url:
        url += "&_nc=%s" % _random_string(10)
    else:
        url += "?_nc=%s" % _random_string(10)
    if url.startswith("http://"):
        domain_array = (url.replace('http://', '').split('/')[0]).split('.')
    else:
        domain_array = (url.replace('https://', '').split('/')[0]).split('.')
    domain_name = ""
    if domain_array[0] == "www":
        domain_name = url.replace('http://', '').split('/')[0]
    else:
        domain_name = domain_array[-2] + '.' + domain_array[-1]
        
    favicon_url = 'http://' + domain_name + '/favicon.ico'
    result = urlfetch.fetch(url)
    icon_result = urlfetch.fetch(favicon_url)
    if icon_result.status_code == 200:
        icon = icon_result.content
    else:
        icon = None
    if result.status_code == 200:
       encoded = unicode(result.content, errors="ignore") 
       feed = feedparser.parse(encoded)
    else:
        logging.warn("invalid satus code %s %s " %(str(result.status_code), url))
        return HttpResponse('Failed')
    parsed_items = []
    render_dict = {}
    for entry in feed['entries']:
        if entry.link == "" or entry.link is None:
            continue
        key_fav_icon = "iMypicon" + sha.new(favicon_url).hexdigest()
        if entry.title == '':
            entry.title = '(None)'
        if not hasattr(entry, "author"):
            entry.author = 'none'
        if not hasattr(entry, 'updated_parsed'):
            now = datetime.datetime.now()
            entry.updated_parsed = [now.year, now.month, now.day, now.hour, now.minute, now.second]
        d = IconItem.get_or_insert(key_fav_icon, icon_src=db.Blob(icon))
        key = "iMyp" + sha.new(unicode(user) + entry.link + type_name).hexdigest()
        c = UserItem.get_or_insert(key, type=tp, user=user, title=entry.title, \
                     link=entry.link, media_src=truncate_words(entry.description, 100), author=entry.author, \
                     icon=d, is_featured=False, \
                     item_date=datetime.datetime(entry.updated_parsed[0], entry.updated_parsed[1], entry.updated_parsed[2], entry.updated_parsed[3], entry.updated_parsed[4]))
        
        mingled_item = {}
        mingled_item['user'] = str(c.user)
        mingled_item['title'] = c.title
        mingled_item['link'] = c.link
        mingled_item['icon'] = '/icon/%s/' %key
        mingled_item['src'] = c.media_src
        mingled_item['date'] = timesince(c.item_date)
        
        parsed_items.append(mingled_item)
    
    render_dict['items'] = parsed_items
        
    return HttpResponse(simplejson.dumps(render_dict), mimetype='application/javascript')

@login_required
def fetch_parse_insert(request, type_name):
    "fetch, parse and insert into DB"
    tp = Item.get_by_key_name(type_name)
    if tp is None:
        return Http404
    #a = Item.get_by_insert("writing", title="writing", tab_title="Writing", verbose_title="writing")
    #a = Item.get_or_insert("listening", title="listening", tab_title="Listening", verbose_title="listening")
    #a = Item.get_or_insert("viewing", title="viewing", tab_title="Viewing", verbose_title="viewing")
    #a = Item.get_or_insert("reading", title="reading", tab_title="Reading", verbose_title="reading")
    url = request.POST.get('url', None)
    if url is None:
        return HttpResponse("Error")
    else:
        key = "iMypfeed" + sha.new(str(users.get_current_user()) + url).hexdigest()
        b = UserFeed.all().filter('type = ', tp.key()).filter('user = ', users.get_current_user())
        for r in b:
            r.delete()
        b = UserFeed.get_or_insert(key, type=tp, user=users.get_current_user(), feed_url=url)
    #url = "http://api.flickr.com/services/feeds/photos_public.gne?id=65645030@N00&lang=en-us&format=rss_200"
    if url.startswith("http://"):
        domain_array = (url.replace('http://', '').split('/')[0]).split('.')
    else:
        domain_array = (url.replace('https://', '').split('/')[0]).split('.')
    domain_name = ""
    if domain_array[0] == "www":
        domain_name = url.replace('http://', '').split('/')[0]
    else:
        domain_name = domain_array[-2] + '.' + domain_array[-1]
        
    favicon_url = 'http://' + domain_name + '/favicon.ico'
    result = urlfetch.fetch(url)
    icon_result = urlfetch.fetch(favicon_url)
    if icon_result.status_code == 200:
        icon = icon_result.content
    else:
        icon = None
    if result.status_code == 200:
       encoded = unicode(result.content, errors="ignore") 
       feed = feedparser.parse(encoded)
    else:
        logging.warn("invalid satus code %s " %url)
        return HttpResponse('Failed')
        
    parsed_items = []
    render_dict = {}
    for entry in feed['entries']:
        if entry.link == "" or entry.link is None:
            continue
        key_fav_icon = "iMypicon" + sha.new(favicon_url).hexdigest()
        if entry.title == '':
            entry.title = '(None)'
        if not hasattr(entry, "author"):
            entry.author = 'none'
        if not hasattr(entry, 'updated_parsed'):
            now = datetime.datetime.now()
            entry.updated_parsed = [now.year, now.month, now.day, now.hour, now.minute, now.second]
       
        d = IconItem.get_or_insert(key_fav_icon, icon_src=db.Blob(icon))
        key = "iMyp" + sha.new(unicode(users.get_current_user()) + entry.link + type_name).hexdigest()
        c = UserItem.get_or_insert(key, type=tp, user=users.get_current_user(), title=entry.title, \
                     link=entry.link, media_src=truncate_words(entry.description, 100), author=entry.author, \
                     icon=d, is_featured=False, \
                     item_date=datetime.datetime(entry.updated_parsed[0], entry.updated_parsed[1], entry.updated_parsed[2], entry.updated_parsed[3], entry.updated_parsed[4]))
        
        mingled_item = {}
        mingled_item['user'] = str(c.user)
        mingled_item['title'] = c.title
        mingled_item['link'] = c.link
        mingled_item['icon'] = '/icon/%s/' %key
        mingled_item['src'] = c.media_src
        mingled_item['date'] = timesince(c.item_date)
        
        parsed_items.append(mingled_item)
    
    render_dict['items'] = parsed_items
        
    return HttpResponse(simplejson.dumps(render_dict), mimetype='application/javascript')


def search(request, template="search.html"):
    """Searches the data feeds"""
    q = request.GET.get('q', '')
    words= q.split(' ')
    words = set(words)
    words -= STOP_WORDS
    
    start = request.GET.get('start', 0)
    try:
        start = int(start)
    except:
        return respond(request, template, {'q':q})
    
    items = UserItem.all().order('-item_date')
    results = []
    if not q == "":
        for item in items:
            it = item.title.lower().split(' ')
            fnd = True
            for word in words:
                if not word in it:
                    fnd = False
                    break
            if fnd:
                results.append(item)
                
    else:
        results = list(items)
            
    tot = len(results)
    items = results[start:min(start+10, tot)]
    has_prev = False
    if tot > start + 10:
        has_next = True
    else:
        has_next = False
    if 10 < min(start + 10, tot)<= tot:
        has_prev = True
    else:
        has_prev = False
    params = {'items': items, 'q': q, 'start': start, 'prev':min(start-10, tot), 'end': min(start+10, tot), 'total':tot, 'has_next':has_next, 'has_prev':has_prev}
    return respond(request, template, params)
    


def generate_rss(request, user):
    if not '@' in user:
            user += "@gmail.com"
    user = Account.get_account_for_email(user)
    tp = Item.get_by_key_name("reading")
    if user is None:
        raise Http404
    rss = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
        xmlns:dc="http://purl.org/dc/elements/1.1/" >
        
        <title>Invade %(user)s privacy - Atom Feed</title>
        <link rel="self" href="http://imyp.appspot.com/feeds/%(user)s/" />
        <link rel="alternate" type="text/html" href="http://imyp.appspot.com/~%(user)s/"/>
        <id>tag:inmy.appspot.com,2008:/~%(user)s/</id>
        <subtitle>Invade My Privacy</subtitle>
        <updated>2008-06-25T07:16:20Z</updated>
        <generator uri="http://imyp.appspot.com">imyp-atomizer</generator>
""" % {'user':user.user, 'useremail':user.email}
    data = UserItem.all().filter('user = ', user.user).order('-item_date')[:100]
    for item in data:
        rss += '    <entry>\n'
        rss += '        <title>%s</title>\n' % no_ugly_tags(item.title)
        rss += '        <link rel="alternate" type="text/html"  href="%s" />\n' % item.link
        rss += '        <id>tag:inmy.appspot.com,2008:/read/%(key)s/%(user)s/</id>\n' % {'user':item.user, 'key':item.key()}
        rss += '        <content type="html">%s</content>\n' % no_ugly_tags(item.media_src[:500])
        rss += '        <category term="%s" scheme="http://imyp.appspot.com/schema/" />\n' % item.type.verbose_title
        rss += '        <author><name>%(user)s</name><uri>http://imyp.appspot.com/~%(user)s/</uri></author>\n' % {'user':item.user}
        rss += '        <published>%s</published>\n' % item.item_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        rss += '        <updated>%s</updated>\n' % item.created_on.strftime("%Y-%m-%dT%H:%M:%SZ")
        rss += '    </entry>\n\n'
    rss += """</feed>"""
    return HttpResponse(rss, 'application/atom+xml')

def news(request, template="news.html"):
    news = NewsItem.all()
    return respond(request, template, {'newsitems':news})


def no_ugly_tags(text):
    return text.replace('&', 'amp;').replace('<', '&lt;').replace('>', '&gt;')
'''
class UserRSSFeed(Feed):
    def get_object(self, bits):
        if len(bits) != 1:
            logging.warn("RSS bits are more than one")
            return None
        if not '@' in bits[0]:
            bits[0] += "@gmail.com"
        user = Account.get_account_for_email(bits[0])
        return user
    
    def title(self, obj):
        return u'Invade %s privacy - RSS Feed' % obj.user
    
    def link(self, obj):
        return u'http://google.com'
    
    def description(self, obj):
        return "%s's recent activity on internet" % obj.user

    def items(self, obj):
        return UserItem.all().filer("user=" + user).order_by('-submit_date')[:100]

class UserATOMFeed(UserRSSFeed):
    feed_type = Atom1Feed

'''

