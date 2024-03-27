from django.forms import ModelForm, ChoiceField, Select, ModelChoiceField
from .models import Team, Game, Bet, StandingPrediction, StandingPredictionTeam

class CustomModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class GameForm(CustomModelForm):
    class Meta:
        model = Game
        fields = '__all__'


class TeamForm(CustomModelForm):
    class Meta:
        model = Team
        fields = '__all__'


class BetForm(CustomModelForm):
    class Meta:
        model = Bet
        fields = ['home_goals', 'away_goals']


class StandingPredictionForm(CustomModelForm):
    def __init__(self, *args, **kwargs):
        competition = kwargs.pop('competition', None)
        super().__init__(*args, **kwargs)

        teams = competition.teams.all()
        positions = range(1, len(teams) + 1)
        choices = [(team.id, team.name) for team in teams]
        for i in positions:
            self.fields[f'position_{i}'] = ChoiceField(
                label=f'{i}.',
                choices=choices,
                widget=Select(attrs={'class': 'form-control'})
            )

    class Meta:
        model = StandingPrediction
        fields = ['top_scorer', 'most_assists']


class TableBetForm(CustomModelForm):
    class Meta:
        model = StandingPrediction
        fields = ['top_scorer', 'most_assists']
        labels = {
            'top_scorer': 'Vilken spelare tror du vinner skytteligan? (Ange två alternativ)',
            'most_assists': 'Vilken spelare tror du vinner assistligan? (Ange två alternativ)',
        }

    def __init__(self, *args, competition, bet_positions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.competition = competition

        if bet_positions is None:
            bet_positions = range(1, competition.teams.count() + 1)
        else:
            self.bet_positions = bet_positions

        for position in bet_positions:
            self.fields[f'position_{position}'] = ModelChoiceField(
                queryset=Team.objects.filter(competitions=competition),
                label=f'{position}',
                required=True,
                initial=StandingPredictionTeam.objects.get(standing_prediction=self.instance, position=position).team if self.instance.id else None,
                widget=Select(attrs={'class': 'form-control'})
            )

    def clean(self):
        cleaned_data = super().clean()
        selected_teams = set()

        # Ensure no duplicate teams are selected
        for position in self.bet_positions:
            selected_team = cleaned_data.get(f'position_{position}')
            if selected_team in selected_teams:
                self.add_error(f'position_{position}', 'Varje lag får bara väljas en gång')
            selected_teams.add(selected_team)
