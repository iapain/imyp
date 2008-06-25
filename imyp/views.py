from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.utils.timesince import timesince
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

#import forms
import feedparser


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
    params['request'] = request
    params['is_admin'] = users.is_current_user_admin()
    params['user'] = users.get_current_user()
    params['signin'] = users.create_login_url(request.path)
    params['signout'] = users.create_logout_url(request.path)
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

def _generic_data_adapter(type_name, user, limit=20):
    """Query Datastore"""
    tp = Item.get_by_key_name(type_name)
    if tp is None:
        return Http404
    try:
        data = UserItem.all().filter('type = ', tp.key()).filter('user = ', user).order('-item_date')[:50]
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
    return respond(request, method + ".html", {'data': data, 'user_focus': user, 'force':force_add, 'feed_url':feed_url})


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
        url += "&__nocache=%s" % _random_string(6)
    else:
        url += "?__nocache=%s" % _random_string(6)
    domain_array = (url.replace('http://', '').split('/')[0]).split('.')
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
        d = IconItem.get_or_insert(key_fav_icon, icon_src=db.Blob(icon))
        key = "iMyp" + sha.new(unicode(user) + entry.link + type_name).hexdigest()
        c = UserItem.get_or_insert(key, type=tp, user=user, title=entry.title, \
                     link=entry.link, media_src=entry.summary, author=entry.author, \
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
    domain_array = (url.replace('http://', '').split('/')[0]).split('.')
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
        d = IconItem.get_or_insert(key_fav_icon, icon_src=db.Blob(icon))
        key = "iMyp" + sha.new(unicode(users.get_current_user()) + entry.link + type_name).hexdigest()
        c = UserItem.get_or_insert(key, type=tp, user=users.get_current_user(), title=entry.title, \
                     link=entry.link, media_src=entry.summary, author=entry.author, \
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

    
    

def index(request):
    r = http.HttpResponse('<h1>Django examples</h1><ul>')
    r.write('<li><a href="hello/html/">Hello world (HTML)</a></li>')
    r.write('<li><a href="hello/text/">Hello world (text)</a></li>')
    r.write('<li><a href="hello/write/">HttpResponse objects are file-like objects</a></li>')
    r.write('<li><a href="hello/metadata/">Displaying request metadata</a></li>')
    r.write('<li><a href="hello/getdata/">Displaying GET data</a></li>')
    r.write('<li><a href="hello/postdata/">Displaying POST data</a></li>')
    r.write('</ul>')
    return r
