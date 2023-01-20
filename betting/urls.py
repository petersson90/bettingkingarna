from django.urls import path

from . import views

app_name = 'betting'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('game/<int:pk>/', views.DetailView.as_view(), name='detail'),
]
