from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('', views.gameList, name='index'),
    path('game/<int:pk>/', views.gameDetails, name='detail'),
    path('game/<int:game>/delete-bet/<int:pk>/', views.deleteBet, name='delete-bet'),
]
