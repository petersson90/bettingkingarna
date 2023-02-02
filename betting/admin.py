from django.contrib import admin
from .models import Team, Game, Bet

# Register your models here.
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short', 'number_of_wins')

admin.site.register(Team, TeamAdmin)


class BetInline(admin.TabularInline):
    model = Bet
    fields = ('game', 'user', 'result')
    readonly_fields = ('game', 'user', 'result')
    extra = 0
    
class GameAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'home_team', 'away_team', 'result')
    list_filter = ['start_time', 'home_team', 'away_team']
    inlines = [BetInline]

admin.site.register(Game, GameAdmin)


class BetAdmin(admin.ModelAdmin):
    list_display = ('game', 'user', 'result', 'points')
    list_filter = ['user']

# admin.site.register(Bet, BetAdmin)
