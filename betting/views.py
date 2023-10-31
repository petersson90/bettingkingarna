from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import ValidationError
from accounts.models import CustomUser
from .forms import TeamForm, GameForm, BetForm, StandingPredictionForm
from .models import Team, Competition, Game, Bet, StandingPrediction, StandingPredictionTeam

ALLSVENSKAN_2023 = '18,1,23,3,5,6,4,11,15,13,7,29,22,30,8,24'
TOP_SCORER_2023 = 'Isaac Kiese Thelin'
MOST_ASSISTS_2023 = 'Mikkel Rygaard Jensen'

# Create your views here.

def login_page(request):
    ''' Login page for users '''
    if request.user.is_authenticated:
        return redirect('betting:index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            messages.error(request, 'User does not exist.')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'betting:index')
            return redirect(next_url)

        messages.error(request, 'Username or password does not exist')

    context = {}
    return render(request, 'betting/login.html', context)


def logout_user(request):
    ''' Logging out a user '''
    logout(request)
    return redirect('betting:index')


def team_list(request):
    ''' Listing all available teams '''
    context = {
        'team_list': Team.objects.all(),
    }

    return render(request, 'betting/team_list.html', context)


def game_list(request):
    ''' Listing all past and upcoming games in the current year '''
    current_datetime = timezone.now()

    context = {
        'past_games': Game.objects.filter(start_time__lt=current_datetime, start_time__year=current_datetime.year).order_by('-start_time'),
        'upcoming_games': Game.objects.filter(start_time__gte=current_datetime, start_time__year=current_datetime.year).order_by('start_time')
    }

    return render(request, 'betting/game_list.html', context)


@login_required(login_url='betting:login')
def game_details(request, game_id):
    ''' Shows details about a specific game '''
    game = get_object_or_404(Game, pk=game_id)
    try:
        bet = Bet.objects.get(user=request.user, game_id=game_id)
    except Bet.DoesNotExist:
        bet = Bet(user=request.user, game_id=game_id)
    form = BetForm(instance=bet)

    if request.method == 'POST':
        form = BetForm(request.POST, instance=bet)
        if form.is_valid():
            form.save()
            return redirect('betting:detail', game_id=game_id)

    context = {'game': game, 'form': form}
    return render(request, 'betting/game_detail.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.add_game', login_url='betting:login')
def create_game(request):
    ''' Creating a game from scratch '''
    form = GameForm()

    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('betting:index')

    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.change_game', login_url='betting:login')
def update_game(request, game_id):
    ''' Update details about a specific game '''
    game = get_object_or_404(Game, pk=game_id)
    form = GameForm(instance=game)

    if request.method == 'POST':
        form = GameForm(request.POST, instance=game)
        if form.is_valid():
            form.save()
            return redirect('betting:index')

    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.add_team', login_url='betting:login')
def create_team(request):
    ''' Create a team from scratch '''
    form = TeamForm()

    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('betting:index')

    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
@permission_required('betting.change_team', login_url='betting:login')
def update_team(request, team_id):
    ''' Update details about a specific team '''
    team = get_object_or_404(Team, pk=team_id)
    form = TeamForm(instance=team)

    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            return redirect('betting:index')

    context = {'form': form}
    return render(request, 'betting/base_form.html', context)


@login_required(login_url='betting:login')
def delete_bet(request, game_id, bet_id):
    ''' Delete a placed bet for a game '''
    bet = get_object_or_404(Bet, pk=bet_id)

    if bet.game.id != game_id:
        messages.error(request, 'The bet is not related to this game.')
        return redirect('betting:detail', game_id=game_id)

    if request.user != bet.user:
        messages.error(request, 'You are not authorized to delete someone else\'s bet.')
        return redirect('betting:detail', game_id=game_id)

    if request.method == 'POST':
        bet.delete()
        return redirect('betting:detail', game_id=game_id)

    context = {'obj': bet}
    return render(request, 'betting/delete.html', context)


def standings_list(request):
    ''' Summary of current standings in the bet '''
    current_datetime = timezone.now()

    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1).annotate(total_bets=Count('game'))
    # filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1)
    # print(all_users)

    result_2022 = []
    for row in all_users:
        # print(bet.user, bet.game, bet.points)
        user = CustomUser.objects.get(pk=row['user'])

        user_bets = Bet.objects.exclude(game__home_goals__isnull=True).filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year-1)
        # print(user_bets)
        points = 0
        goal_diff = 0
        goals_scored_diff = 0
        for bet in user_bets:
            points += bet.points
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
            points += bet.points
            if bet.game.home_team.id == 1:
                goal_diff += (bet.home_goals - bet.away_goals) - (bet.game.home_goals - bet.game.away_goals)
                goals_scored_diff += bet.home_goals - bet.game.home_goals
            else:
                goal_diff += (bet.away_goals - bet.home_goals) - (bet.game.away_goals - bet.game.home_goals)
                goals_scored_diff += bet.away_goals - bet.game.away_goals

        user_standing_prediction = StandingPrediction.objects.get(user=user.id, competition=3)
        teams = [Team.objects.get(pk=team_id) for team_id in user_standing_prediction.standing.split(',')]
        user_top_scorer = user_standing_prediction.top_scorer
        user_most_assists = user_standing_prediction.most_assists

        competition_standings = [Team.objects.get(pk=team_id) for team_id in ALLSVENSKAN_2023.split(',')]

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
    ''' Show bet for current user for a specific competition standings '''
    competition = get_object_or_404(Competition, pk=competition_id)
    teams = []
    top_scorer = ''
    most_assists = ''

    try:
        standing_predictions = StandingPrediction.objects.get(user=request.user, competition=competition)
        form_data = {'user': request.user, 'competition': competition}
        for i, team_id in enumerate(standing_predictions.standing.split(',')):
            form_data[f'position_{i+1}'] = Team.objects.get(pk=team_id)
        # print(form_data)
        teams = [Team.objects.get(pk=team_id) for team_id in standing_predictions.standing.split(',')]
        if competition_id == 3:
            current_standings = [Team.objects.get(pk=team_id) for team_id in ALLSVENSKAN_2023.split(',')]
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

        top_scorer = standing_predictions.top_scorer
        most_assists = standing_predictions.most_assists

    except StandingPrediction.DoesNotExist:
        standing_predictions = StandingPrediction(user=request.user, competition=competition)

    if request.method == 'POST':
        form = StandingPredictionForm(request.POST, competition=competition)
        if form.is_valid():
            prediction = form.save(commit=False)
            prediction.user = request.user
            prediction.competition = competition
            position_list = [form.cleaned_data[f'position_{i}'] for i in range(1, competition.teams.count() + 1)]
            selected_teams = []
            for team in position_list:
                if team not in selected_teams:
                    selected_teams.append(team)
            if len(position_list) != len(selected_teams):
                # print('Wrong number of unique teams')
                raise ValidationError('Standing prediction must include all teams in the competition.')
            if len(position_list) != competition.teams.count():
                # print('Wrong number of teams in competition')
                raise ValidationError('Each team must be selected only once in the standing prediction.')
            prediction.standing = ','.join(position_list)
            prediction.save()
            return redirect('betting:standing-prediction', competition_id)
    else:
        form = StandingPredictionForm(competition=competition)
    return render(request, 'betting/standing_prediction.html', {'form': form, 'competition': competition, 'teams': teams, 'bet_results': bet_results, 'top_scorer': top_scorer, 'most_assists': most_assists})


def standing_predictions_list(request, competition_id):
    ''' Show all bets regarding the current standings for a specific competition '''
    competition = get_object_or_404(Competition.objects.prefetch_related('teams'), pk=competition_id)

    all_standing_predictions = StandingPrediction.objects.select_related('user').prefetch_related('standingpredictionteam_set__team').filter(competition=competition).order_by('user__first_name')

    if competition_id == 3:
        sort_order_list = [int(team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        current_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
        top_scorer = TOP_SCORER_2023
        most_assists = MOST_ASSISTS_2023
    else:
        current_standings = []
        top_scorer = ''
        most_assists = ''

    standing_predictions = []
    for standing_prediction in all_standing_predictions:
        teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in standing_prediction.standingpredictionteam_set.all()]
        user_top_scorer = standing_prediction.top_scorer
        user_most_assists = standing_prediction.most_assists

        bet_points = []
        for position, team in teams:
            diff = position - current_standings.index(team) - 1
            bet_points.append(-abs(diff))
        points = sum(bet_points)

        standing_predictions.append({
            'user': standing_prediction.user,
            'teams': teams,
            'bet_points': bet_points,
            'points': points,
            'top_scorer': user_top_scorer,
            'most_assists': user_most_assists
        })

    teams = []
    for i, team in enumerate(current_standings):
        teams.append([((i+1, team), 0)])
        for row in standing_predictions:
            teams[i].append((row['teams'][i], row['bet_points'][i]))

    # context = {'result_2022': result_2022, 'current_standings': current_standings, 'prizes_8': prizes_8, 'prizes_10': prizes_10}
    context = {'competition': competition, 'standing_predictions': standing_predictions, 'teams': teams, 'top_scorer': top_scorer, 'most_assists': most_assists}
    return render(request, 'betting/standing_prediction_list.html', context)
