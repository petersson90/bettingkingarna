from django.forms import ModelForm
from .models import Team, Game, Bet

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
