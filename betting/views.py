from django.views import generic
from django.shortcuts import render, redirect
from .models import Game, Bet
from .forms import BetForm
from datetime import datetime, timezone

# Create your views here.
class IndexView(generic.ListView):
    template_name = 'betting/index.html'
    context_object_name = 'data'

    def get_queryset(self):
        ''' Return two sets of games, past & upcoming '''
        queryset = {
            'past_games': Game.objects.filter(start_time__lt=datetime.now(timezone.utc)).order_by('-start_time'), 
            'upcoming_games': Game.objects.filter(start_time__gte=datetime.now(timezone.utc)).order_by('start_time')
        }
        return queryset
    
class DetailView(generic.DetailView):
    model = Game
    template_name = 'betting/detail.html'

def createBet(request):
    form = BetForm()
    if request.method == 'POST':
        form = BetForm(request.POST)
        if form.is_valid:
            form.save()
            return redirect('betting:detail', pk=request.POST.get('game'))
    
    context = {'form': form}
    return render(request, 'betting/bet_form.html', context)


def updateBet(request, pk):
    bet = Bet.objects.get(id=pk)
    form = BetForm(instance=bet)
    
    if request.method == 'POST':
        form = BetForm(request.POST, instance=bet)
        if form.is_valid():
            form.save()
            return redirect('betting:detail', pk=request.POST.get('game'))
    
    context = {'form': form}
    return render(request, 'betting/bet_form.html', context)


def deleteBet(request, pk):
    bet = Bet.objects.get(id=pk)
    
    if request.method == 'POST':
        bet.delete()
        return redirect('betting:detail', pk=bet.game.id)
    
    context = {'obj': bet}
    return render(request, 'betting/delete.html', context)
