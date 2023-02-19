from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Team, Game, Bet
from accounts.models import CustomUser
from .forms import TeamForm, GameForm, BetForm
from datetime import datetime, timezone

# Create your views here.

current_datetime = datetime.now(timezone.utc)

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
        'past_games': Game.objects.filter(start_time__lt=current_datetime, start_time__year=current_datetime.year).order_by('-start_time'), 
        'upcoming_games': Game.objects.filter(start_time__gte=current_datetime, start_time__year=current_datetime.year).order_by('start_time')
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
    
    if bet.game.id != game:
        messages.error(request, 'The bet is not related to this game.')
        return redirect('betting:detail', pk=game)
    
    if request.user != bet.user:
        messages.error(request, 'Your are not authorized to delete someone else\'s bet.')
        return redirect('betting:detail', pk=game)
    
    if request.method == 'POST':
        bet.delete()
        return redirect('betting:detail', pk=game)
    
    context = {'obj': bet}
    return render(request, 'betting/delete.html', context)

def standingsList(request):    
    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1).annotate(total_bets=Count('game'))
    # filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1)
    # print(all_users)
    
    result_2022 = []   
    for row in all_users:
        # print(bet.user, bet.game, bet.points())
        user = CustomUser.objects.get(pk=row['user'])
        
        user_bets = Bet.objects.filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1)
        # print(user_bets)
        points = 0
        for bet in user_bets:
            points += bet.points()
        
        result_2022.append({'user': user, 'total_bets': row['total_bets'], 'points': points})
    
    result_2022.sort(key=lambda x: x['points'], reverse=True)
    
    prizes_8 = {
        '1': 'Matchtröja',
        '2': '',
        '3': 'Betala för ovanstående',
        '4': 'Betala för ovanstående',
        '5': 'Betala för ovanstående',
        '6': 'Betala för ovanstående',
        '7': 'Betala för ovanstående och arrangera fest',
        '8': 'Betala för ovanstående och arrangera fest',
    }
    
    count, rank = 0, 0
    previous = None
    for row in result_2022:
        current_value = row['points']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank
        row['prize'] = prizes_8[str(rank)]
            
    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year).annotate(total_bets=Count('game'))
    
    current_standings = []
    for row in all_users:
        user = CustomUser.objects.get(pk=row['user'])
        
        user_bets = Bet.objects.filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year)
        points = 0
        for bet in user_bets:
            if bet.points():
                points += bet.points()
        
        current_standings.append({'user': user, 'total_bets': row['total_bets'], 'points': points})
    
    current_standings.sort(key=lambda x: x['points'], reverse=True)
    
    prizes_10 = {
        '1': 'Årskort',
        '2': 'Halsduk (eller motsvarande belopp i MFF-shopen)',
        '3': 'Betala för ovanstående',
        '4': 'Betala för ovanstående',
        '5': 'Betala för ovanstående',
        '6': 'Betala för ovanstående',
        '7': 'Betala för ovanstående',
        '8': 'Betala för ovanstående och arrangera fest',
        '9': 'Betala för ovanstående och arrangera fest',
        '10': 'Betala för ovanstående och arrangera fest',
    }
    
    count, rank = 0, 0
    previous = None
    for row in current_standings:
        current_value = row['points']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank
        row['prize'] = prizes_10[str(rank)]
    
        
    context = {'result_2022': result_2022, 'current_standings': current_standings}
    return render(request, 'betting/standings.html', context)
