from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('', views.gameList, name='index'),
    path('team/', views.teamList, name='list-team'),
    path('team/create/', views.createTeam, name='create-team'),
    path('team/<int:pk>/update/', views.updateTeam, name='update-team'),
    path('game/create/', views.createGame, name='create-game'),
    path('game/<int:pk>/update/', views.updateGame, name='update-game'),
    path('game/<int:pk>/', views.gameDetails, name='detail'),
    path('game/<int:game>/delete-bet/<int:pk>/', views.deleteBet, name='delete-bet'),
    path('standings/', views.standingsList, name='list-standings'),
    path('create-standing-prediction/<int:competition_id>/', views.create_standing_prediction, name='create_standing_prediction'),
]
