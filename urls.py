from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.views.generic.list_detail import object_list
import settings
from metrics.models import ProgramCorrection
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
#    (r'^scorecard/agency/(?P<agency_id>\d+)/', 'metrics.views.get_agency_detail'),
#    (r'^scorecard/program/(?P<program_id>\d+)/', 'metrics.views.get_program_detail'),
    url(r'^scorecard/$', 'metrics.views.index', name='scorecard-index'),
    url(r'^scorecard/(?P<unit>\w+)/(?P<fiscal_year>\d{4})/', 'metrics.views.index', name='scorecard-index-extra'),
    url(r'^analysis/', direct_to_template, {'template': 'analysis.html'}, name='analysis' ),
    url(r'^methodology/', direct_to_template, {'template': 'methodology,html'}, name='methodology'),
    url(r'^background/', direct_to_template, {'template': 'background.html'}, name='background'),
    url(r'^resources/', direct_to_template, {'template': 'resources.html'}, name='resources'),
    url(r'^feedback/$', direct_to_template, {'template':'feedback.html'}, name='feedback'),
    url(r'^corrections/', object_list, {'template': 'corrections.html', 'queryset': ProgramCorrection.objects.all().order_by('program')}, name='corrections'),
    url(r'^animation/$', direct_to_template, {'template': 'animation/index.html'}),
    url(r'^admin/(.*)', admin.site.root),
    url(r'^agency/(?P<agency_id>\d+)/(?P<fiscal_year>\d{4})/(?P<unit>\w+)/', 'metrics.views.agencyDetail', name="agency_detail"),
    url(r'^program/(?P<program_id>\d+)/(?P<unit>\w+)/', 'metrics.views.programDetail'), 
    url(r'^$', direct_to_template, {'template':'index.html'}, name='clearspending-index'),
    url(r'^', include('mediasync.urls')),    
)


#if settings.DEBUG:
#    from django.views.static import serve
#    _media_url = settings.MEDIA_URL
#    if _media_url.startswith('/'):
#        _media_url = _media_url[1:]    
#    urlpatterns += patterns('', (r'^%s(?P<path>.*)$' % _media_url, serve, { 'document_root': settings.MEDIA_ROOT }))
   




