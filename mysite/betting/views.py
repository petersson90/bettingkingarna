from django.shortcuts import get_object_or_404, render
from .models import Game

# Create your views here.
def index(request):
    games_list = Game.objects.order_by('start_time')
    context = {'games_list': games_list}
    return render(request, 'betting/index.html', context)

def detail(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return render(request, 'betting/detail.html', {'game': game})
