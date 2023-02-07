from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('game/<int:pk>/', views.DetailView.as_view(), name='detail'),
    path('create-bet/', views.createBet, name='create-bet'),
    path('update-bet/<int:pk>/', views.updateBet, name='update-bet'),
    path('delete-bet/<int:pk>/', views.deleteBet, name='delete-bet'),
]
