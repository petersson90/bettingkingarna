from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('', views.gameList, name='index'),
    path('team/', views.teamList, name='list-team'),
    path('team/create/', views.createTeam, name='create-team'),
    path('team/<int:team_id>/update/', views.updateTeam, name='update-team'),
    path('game/create/', views.createGame, name='create-game'),
    path('game/<int:game_id>/update/', views.updateGame, name='update-game'),
    path('game/<int:game_id>/', views.gameDetails, name='detail'),
    path('game/<int:game_id>/delete-bet/<int:bet_id>/', views.deleteBet, name='delete-bet'),
    path('standings/', views.standingsList, name='list-standings'),
    path('standing-prediction/create/<int:competition_id>/', views.standing_prediction, name='standing-prediction'),
    path('standing-prediction/<int:competition_id>/', views.standingPredictionsList, name='list-standing-prediction')
]
