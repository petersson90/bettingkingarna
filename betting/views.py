from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Team, Game, Bet
from accounts.models import CustomUser
from .forms import TeamForm, GameForm, BetForm
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


def teamList(request):
    context = {
        'team_list': Team.objects.all(),
    }
    
    return render(request, 'betting/team_list.html', context)


def gameList(request):
    context = {
        'past_games': Game.objects.filter(start_time__lt=datetime.now(timezone.utc)).order_by('-start_time'), 
        'upcoming_games': Game.objects.filter(start_time__gte=datetime.now(timezone.utc)).order_by('start_time')
    }
    
    return render(request, 'betting/game_list.html', context)


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
    return render(request, 'betting/game_detail.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.add_game', login_url='betting:login')
def createGame(request):
    form = GameForm()
    
    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid:
            form.save()
            return redirect('betting:index')
    
    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.change_game', login_url='betting:login')
def updateGame(request, pk):
    game = Game.objects.get(pk=pk)
    form = GameForm(instance=game)
    
    if request.method == 'POST':
        form = GameForm(request.POST, instance=game)
        if form.is_valid:
            form.save()
            return redirect('betting:index')
    
    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.add_team', login_url='betting:login')
def createTeam(request):
    form = TeamForm()
    
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid:
            form.save()
            return redirect('betting:index')
    
    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.change_team', login_url='betting:login')
def updateTeam(request, pk):
    team = Team.objects.get(pk=pk)
    form = TeamForm(instance=team)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid:
            form.save()
            return redirect('betting:index')
    
    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


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
