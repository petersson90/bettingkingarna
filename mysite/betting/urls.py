from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    # ex: /betting/
    path('', views.index, name='index'),
    # ex: /betting/game/5/
    path('game/<int:game_id>/', views.detail, name='detail'),
]
