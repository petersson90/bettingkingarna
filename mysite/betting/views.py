from django.views import generic
from .models import Game

# Create your views here.
class IndexView(generic.ListView):
    template_name = 'betting/index.html'

    def get_queryset(self):
        ''' Return all games ordered by start date/time. '''
        return Game.objects.order_by('start_time')
    
class DetailView(generic.DetailView):
    model = Game
    template_name = 'betting/detail.html'
