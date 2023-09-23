from datetime import datetime, timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.shortcuts import render, redirect
from django.forms import ValidationError
from accounts.models import CustomUser
from .forms import TeamForm, GameForm, BetForm, StandingPredictionForm
from .models import Team, Competition, Game, Bet, StandingPrediction

ALLSVENSKAN_2023 = '1,18,23,3,6,11,15,4,5,29,22,30,7,13,8,24'
TOP_SCORER_2023 = 'Isaac Kiese Thelin'
MOST_ASSISTS_2023 = 'Mikkel Rygaard Jensen'

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
    current_datetime = datetime.now(timezone.utc)
    
    context = {
        'past_games': Game.objects.filter(start_time__lt=current_datetime, start_time__year=current_datetime.year).order_by('-start_time'), 
        'upcoming_games': Game.objects.filter(start_time__gte=current_datetime, start_time__year=current_datetime.year).order_by('start_time')
    }
    
    return render(request, 'betting/game_list.html', context)


@login_required(login_url='betting:login')
def gameDetails(request, game_id):
    game = Game.objects.get(pk=game_id)
    try:
        bet = Bet.objects.get(user=request.user, game_id=game_id)
    except:
        bet = Bet(user=request.user, game_id=game_id)
    form = BetForm(instance=bet)
    
    if request.method == 'POST':
        form = BetForm(request.POST, instance=bet)
        if form.is_valid:
            form.save()
            return redirect('betting:detail', game_id=game_id)
        
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
def updateGame(request, game_id):
    game = Game.objects.get(pk=game_id)
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
def updateTeam(request, team_id):
    team = Team.objects.get(pk=team_id)
    form = TeamForm(instance=team)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid:
            form.save()
            return redirect('betting:index')
    
    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
def deleteBet(request, game_id, bet_id):
    bet = Bet.objects.get(id=bet_id)
    
    if bet.game.id != game_id:
        messages.error(request, 'The bet is not related to this game.')
        return redirect('betting:detail', game_id=game_id)
    
    if request.user != bet.user:
        messages.error(request, 'Your are not authorized to delete someone else\'s bet.')
        return redirect('betting:detail', game_id=game_id)
    
    if request.method == 'POST':
        bet.delete()
        return redirect('betting:detail', game_id=game_id)
    
    context = {'obj': bet}
    return render(request, 'betting/delete.html', context)


def standingsList(request):
    current_datetime = datetime.now(timezone.utc)
     
    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1).annotate(total_bets=Count('game'))
    # filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1)
    # print(all_users)
    
    result_2022 = []   
    for row in all_users:
        # print(bet.user, bet.game, bet.points())
        user = CustomUser.objects.get(pk=row['user'])
        
        user_bets = Bet.objects.exclude(game__home_goals__isnull=True).filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1)
        # print(user_bets)
        points = 0
        goal_diff = 0
        goals_scored_diff = 0
        for bet in user_bets:
            points += bet.points()
            if bet.game.home_team.id == 1:
                goal_diff += (bet.home_goals - bet.away_goals) - (bet.game.home_goals - bet.game.away_goals)
                goals_scored_diff += bet.home_goals - bet.game.home_goals
            else:
                goal_diff += (bet.away_goals - bet.home_goals) - (bet.game.away_goals - bet.game.home_goals)
                goals_scored_diff += bet.away_goals - bet.game.away_goals
        
        table_points = {
            1: 12,
            2: 12,
            3: 12,
            4: 14,
            5: 12,
            6: 18,
            7: 14,
            8: 14,
        }
        
        result_2022.append({
            'user': user,
            'total_bets': row['total_bets'],
            'points': points,
            'table_points': table_points[user.id],
            'goal_diff': goal_diff,
            'goals_scored_diff': goals_scored_diff,
        })
    
    max_total = 0
    for row in result_2022:
        total_points = row['points'] + row['table_points']
        row['total_points'] = total_points
        if total_points > max_total:
            max_total = total_points
            
    for row in result_2022:
        row['order'] = ((max_total - row['total_points']) * 100 + abs(row['goal_diff'])) * 100 + abs(row['goals_scored_diff'])
    
    result_2022.sort(key=lambda x: x['order'])
    
    prizes_8 = {
        '1': 'Matchtröja',
        '2': '',
        '3-6': 'Betala för ovanstående',
        '7-8': 'Betala för ovanstående och arrangera fest',
    }
    
    count, rank = 0, 0
    previous = None
    for row in result_2022:
        current_value = row['order']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank
            
    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year).annotate(total_bets=Count('game'))
    
    current_standings = []
    for row in all_users:
        user = CustomUser.objects.get(pk=row['user'])
        
        user_bets = Bet.objects.exclude(game__home_goals__isnull=True).filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year)
        
        points = 0
        goal_diff = 0
        goals_scored_diff = 0
        for bet in user_bets:
            points += bet.points()
            if bet.game.home_team.id == 1:
                goal_diff += (bet.home_goals - bet.away_goals) - (bet.game.home_goals - bet.game.away_goals)
                goals_scored_diff += bet.home_goals - bet.game.home_goals
            else:
                goal_diff += (bet.away_goals - bet.home_goals) - (bet.game.away_goals - bet.game.home_goals)
                goals_scored_diff += bet.away_goals - bet.game.away_goals
                
        user_standing_prediction = StandingPrediction.objects.get(user=user.id, competition=3)
        teams = [Team.objects.get(id=team_id) for team_id in user_standing_prediction.standing.split(',')]
        user_top_scorer = user_standing_prediction.top_scorer
        user_most_assists = user_standing_prediction.most_assists
        
        competition_standings = [Team.objects.get(id=team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        
        bet_points = []
        for position, team in enumerate(teams):
            diff = position - competition_standings.index(team)
            bet_points.append(-abs(diff))
        table_points = sum(bet_points)
        
        current_standings.append({
            'user': user,
            'total_bets': row['total_bets'],
            'points': points,
            'table_points': table_points,
            'top_scorer': user_top_scorer,
            'most_assists': user_most_assists,
            'goal_diff': goal_diff,
            'goals_scored_diff': goals_scored_diff,
        })
    
    max_total = 0
    for row in current_standings:
        row['extra_bet'] = 0
        if row['top_scorer'] in TOP_SCORER_2023:
            row['extra_bet'] += 6
        if row['most_assists'] in MOST_ASSISTS_2023:
            row['extra_bet'] += 6
        total_points = row['points'] + row['table_points'] + row['extra_bet']
        row['total_points'] = total_points
        if total_points > max_total:
            max_total = total_points
            
    for row in current_standings:
        row['order'] = ((max_total - row['total_points']) * 100 + abs(row['goal_diff'])) * 100 + abs(row['goals_scored_diff'])
    
    current_standings.sort(key=lambda x: x['order'])
    
    prizes_10 = {
        '1': 'Årskort',
        '2': 'Halsduk (eller motsvarande belopp i MFF-shopen)',
        '3': '',
        '4-7': 'Betala för ovanstående',
        '8-10': 'Betala för ovanstående och arrangera fest',
    }
    
    count, rank = 0, 0
    previous = None
    for row in current_standings:
        current_value = row['order']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank
    
        
    context = {'result_2022': result_2022, 'current_standings': current_standings, 'prizes_8': prizes_8, 'prizes_10': prizes_10}
    return render(request, 'betting/standings.html', context)


@login_required(login_url='betting:login')
def standing_prediction(request, competition_id):
    competition = Competition.objects.get(id=competition_id)
    teams = []
    top_scorer = ''
    most_assists = ''
    
    try:
        standing_prediction = StandingPrediction.objects.get(user=request.user, competition=competition)
        form_data = {'user': request.user, 'competition': competition}
        for i, team_id in enumerate(standing_prediction.standing.split(',')):
            form_data[f'position_{i+1}'] = Team.objects.get(pk=team_id)
        # print(form_data)
        teams = [Team.objects.get(id=team_id) for team_id in standing_prediction.standing.split(',')]
        if competition_id == 3:
            current_standings = [Team.objects.get(id=team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        else:
            current_standings = []
        
        bet_results = []
        total_points = 0
        for position, team in enumerate(teams):
            actual_pos = current_standings.index(team)
            diff = position - actual_pos
            points = -abs(diff)
            bet_results.append({
                'team': team,
                'prediction': position,
                'actual_pos': actual_pos + 1,
                'diff': diff,
                'points': points
            })
            total_points += points
        
        top_scorer = standing_prediction.top_scorer
        most_assists = standing_prediction.most_assists
        
    except:
        standing_prediction = StandingPrediction(user=request.user, competition=competition)
    
    if request.method == 'POST':
        form = StandingPredictionForm(request.POST, competition=competition)
        if form.is_valid():
            standing_prediction = form.save(commit=False)
            standing_prediction.user = request.user
            standing_prediction.competition = competition
            standings_list = [form.cleaned_data[f'position_{i}'] for i in range(1, competition.teams.count() + 1)]
            selected_teams = []
            for team in standings_list:
                if team not in selected_teams:
                    selected_teams.append(team)
            if len(standings_list) != len(selected_teams):
                # print('Wrong number of unique teams')
                raise ValidationError('Standing prediction must include all teams in the competition.')
            if len(standings_list) != competition.teams.count():
                # print('Wrong number of teams in competition')
                raise ValidationError('Each team must be selected only once in the standing prediction.')
            standing_prediction.standing = ','.join(standings_list)
            standing_prediction.save()
            return redirect('betting:standing-prediction', competition_id)
    else:
        form = StandingPredictionForm(competition=competition)
    return render(request, 'betting/standing_prediction.html', {'form': form, 'competition': competition, 'teams': teams, 'bet_results': bet_results, 'top_scorer': top_scorer, 'most_assists': most_assists})


def standingPredictionsList(request, competition_id):
    # current_datetime = datetime.now(timezone.utc)
    
    competition = Competition.objects.get(id=competition_id)
    all_users = StandingPrediction.objects.values('user').filter(competition=competition_id).order_by('user__first_name')
    
    if competition_id == 3:
        current_standings = [Team.objects.get(id=team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        top_scorer = TOP_SCORER_2023
        most_assists = MOST_ASSISTS_2023
    else:
        current_standings = []
        top_scorer = '',
        most_assists = ''
    
    standing_predictions = []
    for row in all_users:
        user = CustomUser.objects.get(pk=row['user'])
        
        user_standing_prediction = StandingPrediction.objects.get(user=user.id, competition=competition_id)
        teams = [Team.objects.get(id=team_id) for team_id in user_standing_prediction.standing.split(',')]
        user_top_scorer = user_standing_prediction.top_scorer
        user_most_assists = user_standing_prediction.most_assists
        
        bet_points = []
        for position, team in enumerate(teams):
            diff = position - current_standings.index(team)
            bet_points.append(-abs(diff))
        points = sum(bet_points)
                
        standing_predictions.append({
            'user': user,
            'teams': teams,
            'bet_points': bet_points,
            'points': points,
            'top_scorer': user_top_scorer,
            'most_assists': user_most_assists
        })
    
    teams = []
    for i, team in enumerate(current_standings):
        teams.append([(team, 0)])
        for row in standing_predictions:
            teams[i].append((row['teams'][i], row['bet_points'][i]))
        
    # context = {'result_2022': result_2022, 'current_standings': current_standings, 'prizes_8': prizes_8, 'prizes_10': prizes_10}
    context = {'competition': competition, 'standing_predictions': standing_predictions, 'teams': teams, 'top_scorer': top_scorer, 'most_assists': most_assists}
    return render(request, 'betting/standing_prediction_list.html', context)
