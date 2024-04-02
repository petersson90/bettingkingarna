from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('', views.game_list, name='index'),
    path('team/', views.team_list, name='list-team'),
    path('team/create/', views.create_team, name='create-team'),
    path('team/<int:team_id>/update/', views.update_team, name='update-team'),
    path('game/create/', views.create_game, name='create-game'),
    path('game/<int:game_id>/update/', views.update_game, name='update-game'),
    path('game/<int:game_id>/', views.game_details, name='detail'),
    path('game/<int:game_id>/delete-bet/<int:bet_id>/', views.delete_bet, name='delete-bet'),
    path('standings/', views.standings_list, name='list-standings'),
    path('standing-prediction/create/<int:competition_id>/', views.standing_prediction, name='standing-prediction'),
    path('standing-prediction/<int:competition_id>/', views.standing_predictions_list, name='list-standing-prediction'),
    path('standing-prediction/suggestion/<int:competition_id>/', views.standing_predictions_suggestion, name='list-standing-suggestion'),
    path('statistics/<int:year>/', views.statistics, name='statistics'),
    path('game/feed.ics', views.calendar_subscription(), name='calendar'),
    path('table-bet/<int:competition_id>/', views.table_bet, name='table-bet'),
    path('table-bet/<int:competition_id>/summary/', views.table_bet_summary, name='table-bet-summary'),
]
