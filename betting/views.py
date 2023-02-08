from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views import generic
from .models import Game, Bet
from accounts.models import CustomUser
from .forms import BetForm
from datetime import datetime, timezone

# Create your views here.    
def loginPage(request):
    if request.user.is_authenticated:
        return redirect('betting:index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user = CustomUser.objects.get(username=username)
        except:
            messages.error(request, 'User does not exist.')
            
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'betting:index')
            return redirect(next_url)
        else:
            messages.error(request, 'Username or password does not exist')
        
    context = {}
    return render(request, 'betting/login.html', context)

def logoutUser(request):
    logout(request)
    return redirect('betting:index')

def gameList(request):
    context = {
        'past_games': Game.objects.filter(start_time__lt=datetime.now(timezone.utc)).order_by('-start_time'), 
        'upcoming_games': Game.objects.filter(start_time__gte=datetime.now(timezone.utc)).order_by('start_time')
    }
    
    return render(request, 'betting/index.html', context)


@login_required(login_url='betting:login')
def gameDetails(request, pk):
    game = Game.objects.get(pk=pk)
    try:
        bet = Bet.objects.get(user=request.user, game=game)
    except:
        bet = Bet(user=request.user, game=game)
    form = BetForm(instance=bet)
    
    if request.method == 'POST':
        form = BetForm(request.POST, instance=bet)
        if form.is_valid:
            form.save()
            return redirect('betting:detail', pk=pk)
        
    context = {'game': game, 'form': form}
    return render(request, 'betting/detail.html', context)


@login_required(login_url='betting:login')
def deleteBet(request, game, pk):
    bet = Bet.objects.get(id=pk)
    
    if request.user != bet.user:
        return HttpResponse('Nice try!')
    
    if request.method == 'POST':
        bet.delete()
        return redirect('betting:detail', pk=bet.game.id)
    
    context = {'obj': bet}
    return render(request, 'betting/delete.html', context)
