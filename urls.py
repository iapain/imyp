from django.conf.urls.defaults import *


urlpatterns = patterns('',
    (r'^$', 'imyp.views.test'),
    (r'^parse/(?P<type_name>\w+)/$', 'imyp.views.fetch_parse_insert'),
    (r'^init/$', 'imyp.views.initial'),
    (r'^~(?P<user>.*)/$', 'imyp.views.user_handler'),
    (r'^search/$', 'imyp.views.search'),
    (r'^u/(?P<method>\w+)/(?P<user>.*)/$', 'imyp.views.dispatcher'),
    (r'^poke/(?P<type_name>\w+)/(?P<user>.*)/$', 'imyp.views.poke'),
    (r'^u/(?P<method>\w+)/$', 'imyp.views.dispatcher'),
    (r'^parse/(?P<type_name>\w+)/$', 'imyp.views.fetch_parse_insert'),
    (r'^icon/(?P<key>\w+)/$', 'imyp.views.icon'),
    (r'^feeds/(?P<user>.*)/$', 'imyp.views.generate_rss'),
    (r'^whatisnew/$', 'imyp.views.news'),

)
