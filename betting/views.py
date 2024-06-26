from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg, Window
from django.db.models.functions import Round
from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django_ical.views import ICalFeed
from accounts.models import CustomUser
from .forms import TeamForm, GameForm, BetForm, StandingPredictionForm, TableBetForm
from .models import Team, Competition, Game, Bet, StandingPrediction, StandingPredictionTeam, Standing, TeamPosition

DEADLINE_2024 = timezone.make_aware(timezone.datetime(2024, 4, 7, 11))
ALLSVENSKAN_2023 = '1,18,23,3,5,4,6,13,11,15,7,29,22,30,8,24'
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
        'past_games': Game.objects.select_related('home_team', 'away_team').filter(start_time__lt=current_datetime, start_time__year=current_datetime.year, competition__excluded=False).order_by('-start_time'),
        'upcoming_games': Game.objects.select_related('home_team', 'away_team').filter(start_time__gte=current_datetime, start_time__year=current_datetime.year, competition__excluded=False).order_by('start_time')
    }

    return render(request, 'betting/game_list.html', context)


@login_required(login_url='betting:login')
def game_details(request, game_id):
    ''' Shows details about a specific game '''
    game = get_object_or_404(Game.objects.select_related('home_team', 'away_team').prefetch_related('bets', 'bets__user'), pk=game_id)
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
            return redirect('betting:detail', game_id=game_id)

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
            return redirect('betting:list-team')

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
            return redirect('betting:list-team')

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
    # Access the selected_year from the request object
    # selected_year = request.selected_year
    current_datetime = timezone.now()
    selected_year = str(current_datetime.year)

    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=selected_year, game__competition__excluded=False).annotate(total_bets=Count('game'))

    if selected_year == '2022':
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
    elif selected_year == '2023':
        competition = Competition.objects.get(pk=3)
        sort_order_list = [int(team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        competition_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
    elif selected_year == '2024':
        competition = Competition.objects.get(pk=8)
        standings = Standing.objects.filter(competition=competition).prefetch_related('team_positions').latest('round')
        sort_order_list = list(standings.team_positions.values_list('team_id', flat=True).order_by('position'))
        competition_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))


    result = []
    for row in all_users:
        # print(bet.user, bet.game, bet.points)
        user = CustomUser.objects.get(pk=row['user'])

        user_bets = Bet.objects.select_related('game', 'game__home_team', 'game__away_team').exclude(game__home_goals__isnull=True).filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=selected_year, game__competition__excluded=False)
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

        if selected_year == '2022':
            user_table_points = table_points.get(user.id, 0)
            user_top_scorer = 'N/A'
            user_most_assists = 'N/A'
        elif selected_year == '2024':
            user_table_points = 0
            user_top_scorer = 'N/A'
            user_most_assists = 'N/A'
        else:
            user_table_points = 0
            try:
                user_standing_prediction = StandingPrediction.objects.select_related('user').prefetch_related('team_positions__team').get(user=user.id, competition=competition)
                teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in user_standing_prediction.team_positions.all()]
                user_top_scorer = user_standing_prediction.top_scorer
                user_most_assists = user_standing_prediction.most_assists
                bet_points = []
                for position, team in teams:
                    diff = position - competition_standings.index(team) - 1
                    bet_points.append(-abs(diff))
                user_table_points = sum(bet_points)
            except StandingPrediction.DoesNotExist:
                user_top_scorer = 'N/A'
                user_most_assists = 'N/A'

        result.append({
            'user': user,
            'total_bets': row['total_bets'],
            'points': points,
            'table_points': user_table_points,
            'top_scorer': user_top_scorer,
            'most_assists': user_most_assists,
            'goal_diff': goal_diff,
            'goals_scored_diff': goals_scored_diff,
        })

    max_total = 0
    top_scorer_list = []
    most_assists_list = []
    if selected_year == '2023':
        top_scorer_list = TOP_SCORER_2023
        most_assists_list = MOST_ASSISTS_2023
    elif selected_year == '2024':
        top_scorer_list = standings.top_scorer
        most_assists_list = standings.most_assists

    for row in result:
        row['extra_bet'] = 0

        if row['top_scorer'] in top_scorer_list:
            row['extra_bet'] += 6
        if row['most_assists'] in most_assists_list:
            row['extra_bet'] += 6

        total_points = row['points'] + row['table_points'] + row['extra_bet']
        row['total_points'] = total_points
        if total_points > max_total:
            max_total = total_points

    for row in result:
        row['order'] = ((max_total - row['total_points']) * 100 + abs(row['goal_diff'])) * 100 + abs(row['goals_scored_diff'])

    result.sort(key=lambda x: x['order'])

    if selected_year == '2022':
        prizes = {
            '1': 'Matchtröja',
            '2': '',
            '3-6': 'Betala för ovanstående',
            '7-8': 'Betala för ovanstående och arrangera fest',
        }
    else:
        prizes = {
            '1': 'Årskort',
            '2': 'Halsduk (eller motsvarande belopp i MFF-shopen)',
            '3': '',
            '4-7': 'Betala för ovanstående',
            '8-10': 'Betala för ovanstående och arrangera fest',
        }

    count, rank = 0, 0
    previous = None
    for row in result:
        current_value = row['order']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank


    context = {'result': result, 'prizes': prizes}
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

    all_standing_predictions = StandingPrediction.objects.select_related('user').prefetch_related('team_positions__team').filter(competition=competition).order_by('user__first_name')

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
        teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in standing_prediction.team_positions.all()]
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


def standing_predictions_suggestion(request, competition_id):
    ''' Suggested rules for the 2024 bet '''
    current_datetime = timezone.now()

    competition = get_object_or_404(Competition.objects.prefetch_related('teams'), pk=competition_id)

    all_standing_predictions = StandingPrediction.objects.select_related('user').prefetch_related('team_positions').filter(competition=competition).order_by('user__first_name')

    TOP_BOTTOM = 4
    POINTS_CORRECT = 6
    POINTS_ALMOST = 2

    if competition_id == 3:
        sort_order_list = [int(team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        current_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
        top_scorer = TOP_SCORER_2023
        most_assists = MOST_ASSISTS_2023
    else:
        current_standings = []
        top_scorer = ''
        most_assists = ''

    current_standings = [(pos, team) for pos, team in enumerate(current_standings, 1)]
    current_top_teams = current_standings[:TOP_BOTTOM]
    current_bottom_teams = current_standings[-TOP_BOTTOM:]

    standing_predictions = []
    for standing_prediction in all_standing_predictions:
        teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in standing_prediction.team_positions.all()]
        user_top_scorer = standing_prediction.top_scorer
        user_most_assists = standing_prediction.most_assists

        top_teams = teams[:TOP_BOTTOM]
        bottom_teams = teams[-TOP_BOTTOM:]

        teams = top_teams + bottom_teams

        bet_points = []
        for position, team in top_teams:
            points = 0
            if (position, team) in current_top_teams:
                points = POINTS_CORRECT
            elif team in [tup[1] for tup in current_top_teams]:
                points = POINTS_ALMOST
            bet_points.append(points)

        for position, team in bottom_teams:
            points = 0
            if (position, team) in current_bottom_teams:
                points = POINTS_CORRECT
            elif team in [tup[1] for tup in current_bottom_teams]:
                points = POINTS_ALMOST
            bet_points.append(points)
        points = sum(bet_points)

        standing_predictions.append({
            'user': standing_prediction.user,
            'teams': teams,
            'top_teams': top_teams,
            'bottom_teams': bottom_teams,
            'bet_points': bet_points,
            'points': points,
            'top_scorer': user_top_scorer,
            'most_assists': user_most_assists
        })

    teams = []

    current_standings = current_standings[:TOP_BOTTOM] + current_standings[-TOP_BOTTOM:]
    current_standings = [[((position, team), 0)] for position, team in current_standings]

    for i, _ in enumerate(current_standings):
        for row in standing_predictions:
            current_standings[i].append((row['teams'][i], row['bet_points'][i]))

    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year, game__competition__excluded=False).annotate(total_bets=Count('game'))

    competition = Competition.objects.get(pk=3)
    sort_order_list = [int(team_id) for team_id in ALLSVENSKAN_2023.split(',')]
    competition_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
    result_2023 = []
    for row in all_users:
        user = CustomUser.objects.get(pk=row['user'])

        user_bets = Bet.objects.select_related('game', 'game__home_team', 'game__away_team').exclude(game__home_goals__isnull=True).filter(user=user.id, game__start_time__lt=current_datetime, game__start_time__year=current_datetime.year, game__competition_exclude=False)

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

        user_standing_prediction = StandingPrediction.objects.select_related('user').prefetch_related('team_positions').get(user=user.id, competition=competition)
        teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in user_standing_prediction.team_positions.all()]
        user_top_scorer = user_standing_prediction.top_scorer
        user_most_assists = user_standing_prediction.most_assists

        top_teams = teams[:TOP_BOTTOM]
        bottom_teams = teams[-TOP_BOTTOM:]

        bet_points = []
        for position, team in top_teams:
            points_temp = 0
            if (position, team) in current_top_teams:
                points_temp = POINTS_CORRECT
            elif team in [tup[1] for tup in current_top_teams]:
                points_temp = POINTS_ALMOST
            bet_points.append(points_temp)

        for position, team in bottom_teams:
            points_temp = 0
            if (position, team) in current_bottom_teams:
                points_temp = POINTS_CORRECT
            elif team in [tup[1] for tup in current_bottom_teams]:
                points_temp = POINTS_ALMOST
            bet_points.append(points_temp)
        table_points = sum(bet_points)

        result_2023.append({
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
    for row in result_2023:
        row['extra_bet'] = 0
        if row['top_scorer'] in TOP_SCORER_2023:
            row['extra_bet'] += 6
        if row['most_assists'] in MOST_ASSISTS_2023:
            row['extra_bet'] += 6
        total_points = row['points'] + row['table_points'] + row['extra_bet']
        row['total_points'] = total_points
        if total_points > max_total:
            max_total = total_points

    for row in result_2023:
        row['order'] = ((max_total - row['total_points']) * 100 + abs(row['goal_diff'])) * 100 + abs(row['goals_scored_diff'])

    result_2023.sort(key=lambda x: x['order'])

    prizes_10 = {
        '1': 'Årskort',
        '2': 'Halsduk (eller motsvarande belopp i MFF-shopen)',
        '3': '',
        '4-7': 'Betala för ovanstående',
        '8-10': 'Betala för ovanstående och arrangera fest',
    }

    count, rank = 0, 0
    previous = None
    for row in result_2023:
        current_value = row['order']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank

    context = {
        'competition': competition,
        'standing_predictions': standing_predictions,
        'teams': current_standings,
        'top_scorer': top_scorer,
        'most_assists': most_assists,
        'result_2023': result_2023,
        'prizes_10': prizes_10,
        'TOP_BOTTOM': TOP_BOTTOM,
        'POINTS_CORRECT': POINTS_CORRECT,
        'POINTS_ALMOST': POINTS_ALMOST
    }
    return render(request, 'betting/standing_prediction_suggestion.html', context)


def statistics(request, year):
    ''' Calculates statistics regarding the bet '''
    current_datetime = timezone.now()

    def recent_games(number_of_games):
        return Game.objects.filter(start_time__lt=current_datetime, start_time__year=year, competition__excluded=False).order_by('-start_time')[:number_of_games].values('id')

    stats_table = Bet.objects.values('user__first_name').filter(game__start_time__lt=current_datetime, game__start_time__year=year, game__competition__excluded=False).annotate(
        total_bets=Count('user'),
        total_points=Sum('points'),
        average_points=Round(Avg('points'), 2),
        total_points_last_5=Sum('points', filter=Q(game__in=recent_games(5))),
        average_points_last_5=Round(Avg('points', filter=Q(game__in=recent_games(5))), 2),
        total_points_last_10=Sum('points', filter=Q(game__in=recent_games(10))),
        average_points_last_10=Round(Avg('points', filter=Q(game__in=recent_games(10))), 2),
        total_points_last_15=Sum('points', filter=Q(game__in=recent_games(15))),
        average_points_last_15=Round(Avg('points', filter=Q(game__in=recent_games(15))), 2)
    ).order_by('-total_points')

    # Assuming you have a predefined list of user names or IDs
    user_list = Bet.objects.values('user__id').filter(game__start_time__lt=current_datetime, game__start_time__year=year, game__competition__excluded=False).annotate().distinct()

    # Dynamically generate the fields for each user's cumulative points
    user_cumulative_points = {f'user_{user["user__id"]}_cumulative_points': Window(Sum('bets__points', filter=Q(bets__user__id=user['user__id'])), order_by='start_time') for user in user_list}

    # Create the queryset
    game_stats = (
        Game.objects
        .filter(start_time__lt=current_datetime, start_time__year=year, competition__excluded=False)
        .prefetch_related('bets', 'bets__user')
        .select_related('home_team', 'away_team')
        .annotate(
            **user_cumulative_points
        )
        .values('id', 'start_time', 'home_team__name', 'away_team__name', *user_cumulative_points.keys())
        .distinct()
        .order_by('start_time')
    )

    context = {'stats_table': stats_table, 'game_stats': game_stats}
    return render(request, 'betting/statistics.html', context)


class calendar_subscription(ICalFeed):
    ''' A calendar feed with all the games '''
    product_id = '-//Bettingkingarna//All games//SV'
    timezone = 'Europe/Stockholm'
    file_name = "feed.ics"

    def items(self):
        ''' Return all games '''
        return Game.objects.filter(competition__excluded=False)

    def item_guid(self, item):
        ''' Setting a UID for each item '''
        return f'Game-{item.id}@Bettingkingarna'

    def item_title(self, item):
        return f'{item}'

    def item_description(self, item):
        return f'{item.competition}'

    def item_start_datetime(self, item):
        ''' Define the start time for each event '''
        return item.start_time

    def item_end_datetime(self, item):
        ''' Define the end time for each event '''
        return item.start_time + timezone.timedelta(hours=2)


@login_required(login_url='betting:login')
def table_bet(request, competition_id):
    ''' Show bet for current user for a specific competition standings '''
    competition = get_object_or_404(Competition, pk=competition_id)
    teams = []
    top_scorer = None
    most_assists = None
    bet_positions = None
    if competition_id == 1:
        bet_positions = [1, 2, 3, 14, 15, 16]
    if competition_id == 8:
        bet_positions = [1, 2, 3, 4, 13, 14, 15, 16]

    try:
        user_bet = StandingPrediction.objects.get(user=request.user, competition=competition)
        teams = StandingPredictionTeam.objects.filter(standing_prediction=user_bet).order_by('position')
        top_scorer = user_bet.top_scorer
        most_assists = user_bet.most_assists

    except StandingPrediction.DoesNotExist:
        user_bet = StandingPrediction(user=request.user, competition=competition)

    if request.method == 'POST':
        if competition_id == 8 and timezone.now() >= DEADLINE_2024:
            messages.error(request, 'Deadline har passerat och inga nya eller ändrade bet kan läggas.')
            return redirect('betting:table-bet', competition_id)

        form = TableBetForm(competition=competition, bet_positions=bet_positions, data=request.POST, instance=user_bet)
        if form.is_valid():
            user_bet = form.save(commit=False)
            user_bet.user = request.user
            user_bet.competition = competition
            user_bet.save()

            with transaction.atomic():
                StandingPredictionTeam.objects.filter(standing_prediction=user_bet).delete()

                for i in bet_positions:
                    team = form.cleaned_data[f'position_{i}']
                    StandingPredictionTeam.objects.update_or_create(standing_prediction=user_bet, position=i, defaults={'team': team})

            return redirect('betting:table-bet', competition_id)
    else:
        form = TableBetForm(competition=competition, bet_positions=bet_positions, instance=user_bet)


    if competition_id == 8 and timezone.now() >= DEADLINE_2024:
        form = None

    context = {
        'form': form,
        'competition': competition,
        'teams': teams,
        'top_scorer': top_scorer,
        'most_assists': most_assists
    }

    return render(request, 'betting/table_bet.html', context)


def table_bet_summary(request, competition_id):
    ''' Show all bets regarding the current standings for a specific competition '''
    competition = get_object_or_404(Competition.objects.prefetch_related('teams'), pk=competition_id)

    all_standing_predictions = StandingPrediction.objects.select_related('user').prefetch_related('team_positions__team').filter(competition=competition).order_by('user__first_name')

    TOP_BOTTOM = 0
    POINTS_CORRECT = 0
    POINTS_ALMOST = 0

    if competition_id == 1 or competition_id == 8:
        if competition_id == 1: # Allsvenskan 2022
            sort_order_list = [23,3,6,4,7,18,1,22,15,5,13,11,8,24,20,9]
            top_scorer = ''
            most_assists = ''
            TOP_BOTTOM = 3
            POINTS_CORRECT = 6
            POINTS_ALMOST = 4
        elif competition_id == 8: # Allsvenskan 2024
            standings = Standing.objects.filter(competition=competition).prefetch_related('team_positions').latest('round')
            sort_order_list = list(standings.team_positions.values_list('team_id', flat=True).order_by('position'))
            top_scorer = standings.top_scorer
            most_assists = standings.most_assists
            TOP_BOTTOM = 4
            POINTS_CORRECT = 6
            POINTS_ALMOST = 2

        current_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
        current_standings = [(pos, team) for pos, team in enumerate(current_standings, 1)]
        current_top_teams = current_standings[:TOP_BOTTOM]
        current_bottom_teams = current_standings[-TOP_BOTTOM:]

        standing_predictions = []
        for standing_prediction in all_standing_predictions:
            teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in standing_prediction.team_positions.all()]
            user_top_scorer = standing_prediction.top_scorer
            user_most_assists = standing_prediction.most_assists

            top_teams = teams[:TOP_BOTTOM]
            bottom_teams = teams[-TOP_BOTTOM:]

            teams = top_teams + bottom_teams

            bet_points = []
            for position, team in top_teams:
                points = 0
                if (position, team) in current_top_teams:
                    points = POINTS_CORRECT
                elif team in [tup[1] for tup in current_top_teams]:
                    points = POINTS_ALMOST
                bet_points.append(points)

            for position, team in bottom_teams:
                points = 0
                if (position, team) in current_bottom_teams:
                    points = POINTS_CORRECT
                elif team in [tup[1] for tup in current_bottom_teams]:
                    points = POINTS_ALMOST
                bet_points.append(points)
            points = sum(bet_points)

            standing_predictions.append({
                'user': standing_prediction.user,
                'teams': teams,
                'top_teams': top_teams,
                'bottom_teams': bottom_teams,
                'bet_points': bet_points,
                'points': points,
                'top_scorer': user_top_scorer,
                'most_assists': user_most_assists
            })

        # Hide all standing predictions if the competition has not started yet
        if competition_id == 8 and timezone.now() < DEADLINE_2024:
            standing_predictions = []

        teams = []

        current_standings = current_standings[:TOP_BOTTOM] + current_standings[-TOP_BOTTOM:]
        current_standings = [[((position, team), 0)] for position, team in current_standings]

        for i, _ in enumerate(current_standings):
            for row in standing_predictions:
                current_standings[i].append((row['teams'][i], row['bet_points'][i]))

    elif competition_id == 3: # Allsvenskan 2023
        sort_order_list = [int(team_id) for team_id in ALLSVENSKAN_2023.split(',')]
        current_standings = sorted(competition.teams.all(), key=lambda team: sort_order_list.index(team.id))
        top_scorer = TOP_SCORER_2023
        most_assists = MOST_ASSISTS_2023

        standing_predictions = []
        for standing_prediction in all_standing_predictions:
            teams = [(standing_prediction_team.position, standing_prediction_team.team) for standing_prediction_team in standing_prediction.team_positions.all()]
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

        current_standings = teams

    else:
        current_standings = []
        top_scorer = ''
        most_assists = ''
        standing_predictions = []

    team_positions = TeamPosition.objects.filter(standing__competition=competition).values(
            'team__name',
            'position',
            'standing__round',
        ).order_by('team__name', 'standing__round')

    chart_data = {}
    for item in team_positions:
        team = item['team__name']
        chart_data[team] = chart_data.get(team, {})
        standing_round = item['standing__round']
        chart_data[team][standing_round] = item['position']

    context = {
        'competition': competition,
        'standing_predictions': standing_predictions,
        'teams': current_standings,
        'top_scorer': top_scorer,
        'most_assists': most_assists,
        'TOP_BOTTOM': TOP_BOTTOM,
        'POINTS_CORRECT': POINTS_CORRECT,
        'POINTS_ALMOST': POINTS_ALMOST,
        'chart_data': chart_data,
    }

    return render(request, 'betting/table_bet_summary.html', context)


def competition_overview(request, competition_id):
    ''' Show the games and bet results for a specific competition '''
    current_datetime = timezone.now()
    competition = get_object_or_404(Competition, pk=competition_id)

    all_users = Bet.objects.values('user').filter(game__start_time__lt=current_datetime, game__competition=competition).annotate(total_bets=Count('user'))
    
    result = []
    for row in all_users:
        # print(bet.user, bet.game, bet.points)
        user = CustomUser.objects.get(pk=row['user'])

        user_bets = Bet.objects.select_related('game', 'game__home_team', 'game__away_team').exclude(game__home_goals__isnull=True).filter(user=user.id, game__start_time__lt=current_datetime, game__competition=competition)
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

        result.append({
            'user': user,
            'total_bets': row['total_bets'],
            'points': points,
            'goal_diff': goal_diff,
            'goals_scored_diff': goals_scored_diff,
        })
    
    max_total = 0
    for row in result:
        total_points = row['points']
        if total_points > max_total:
            max_total = total_points
    
    for row in result:
        row['order'] = ((max_total - row['points']) * 100 + abs(row['goal_diff'])) * 100 + abs(row['goals_scored_diff'])

    result.sort(key=lambda x: x['order'])

    count, rank = 0, 0
    previous = None
    for row in result:
        current_value = row['order']
        count += 1
        if current_value != previous:
            rank += count
            previous = current_value
            count = 0
        row['rank'] = rank

    context = {
        'competition': competition,
        'result': result,
        'past_games': Game.objects.select_related('home_team', 'away_team').filter(start_time__lt=current_datetime, competition=competition).order_by('-start_time'),
        'upcoming_games': Game.objects.select_related('home_team', 'away_team').filter(start_time__gte=current_datetime, competition=competition).order_by('start_time'),
    }
    return render(request, 'betting/competition_overview.html', context)