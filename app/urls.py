from django.urls import include, path, re_path

from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),  # root page
    path('headquarters', views.headquarters, name='headquarters'),
    path('council', views.council, name='council'),
    path('map', views.map, name='map'),
    path('smap', views.smap, name='smap'),
    path('planets', views.planets, name='planets'),
    re_path(r'^planet(?P<planet_id>[0-9]+)/$', views.planet, name='planet'),
    re_path(r'^system(?P<system_id>[0-9]+)/$', views.system, name='system'),
    re_path(r'^raze(?P<planet_id>[0-9]+)/$', views.raze, name='raze'),
    re_path(r'^razeall(?P<planet_id>[0-9]+)/$', views.razeall, name='razeall'),
    re_path(r'^build(?P<planet_id>[0-9]+)/$', views.build, name='build'),
    path('ranking', views.ranking, name='ranking'),
    path('empire_ranking', views.empire_ranking, name='empire_ranking'),
    re_path(r'^password/$', views.change_password, name='change_password'),
    path('units', views.units, name='units'),
    path('fleets', views.fleets, name='fleets'),
    path('fleetsend', views.fleetsend, name='fleetsend'),
    re_path(r'^empire(?P<empire_id>[0-9]+)/$', views.empire, name='empire'),
    path('vote', views.vote, name='vote'),
    path('vote_results', views.vote, name='voteresults'),
    path('pm_options', views.pm_options, name='prime_minister_options'),
    path('relations', views.relations, name='relations'),
    path('results', views.results, name='results'),
    path('research', views.research, name='research'),
    path('famaid', views.famaid, name='famaid'),
    path('famgetaid', views.famgetaid, name='famgetaid'),
    path('messages', views.game_messages, name='messages'),
    path('outbox', views.outbox, name='outbox'),
    re_path(r'^compose_message(?P<user_id>[0-9]*)/$', views.compose_message, name='compose_message'),
    re_path(r'^delete_message_inbox(?P<message_id>[0-9]+)/$', views.del_message_in, name='del_inbox'),
    re_path(r'^delete_message_outbox(?P<message_id>[0-9]+)/$', views.del_message_out, name='del_outbox'),
    path('delete_all_messages_inbox', views.bulk_del_message_in, name='delete_all_messages_inbox'),
    path('delete_all_messages_outbox', views.bulk_del_message_out, name='delete_all_messages_outbox'),
    path('guide', views.guide, name='guide'),
    path('faq', views.faq, name='faq'),
    path("registration/register", views.register, name="register"),
    path('logout', views.custom_logout, name='logout'),
    path('login', views.custom_login, name='login'),
    path('choose_empire_race', views.choose_empire_race, name='choose_empire_race'),
    path('fleets_orders', views.fleets_orders, name='fleets_orders'),
    path('fleets_orders_process', views.fleets_orders_process, name='fleets_orders_process'),
    path('fleets_disband', views.fleets_disband, name='fleets_disband'),
    path('fleets_disband', views.fleets_disband, name='fleets_disband'),
    path('famnews', views.famnews, name='famnews'),
    path('specops', views.specops, name='specops'),
    path('btn', views.btn, name='btn'),
	re_path(r'^battle(?P<fleet_id>[0-9]+)/$', views.battle, name='battle'),
    path('map_settings', views.map_settings, name='map_settings'),
    path('scouting', views.scouting, name='scouting'),
    path('halloffame', views.hall_of_fame, name='hall_of_fame'),
    re_path(r'^specop_show(?P<specop_id>[0-9]+)/$', views.specop_show, name='specop_show'),
    re_path(r'^account(?P<player_id>[0-9]+)/$', views.account, name='account'),
    path('mass_build', views.mass_build, name='mass_build'),
    path('races', views.races, name='races'),
    path('feedback', views.feedback, name='feedback'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
