from django.contrib import admin
from .models import Competition, Team, Game, Bet, StandingPrediction, StandingPredictionTeam, Standing, TeamPosition

# Register your models here.
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'season']

admin.site.register(Competition, CompetitionAdmin)


class TeamAdmin(admin.ModelAdmin):
    list_display = ['name']

admin.site.register(Team, TeamAdmin)


class BetInline(admin.TabularInline):
    model = Bet
    fields = ['game', 'user', 'result', 'created', 'updated', 'points']
    readonly_fields = fields
    extra = 0

class GameAdmin(admin.ModelAdmin):
    list_display = ['start_time', 'home_team', 'away_team', 'result']
    list_filter = ['start_time', 'competition', 'home_team', 'away_team']
    inlines = [BetInline]

admin.site.register(Game, GameAdmin)


# class BetAdmin(admin.ModelAdmin):
#     list_display = ['game', 'user', 'result', 'points']
#     list_filter = ['user']

# admin.site.register(Bet, BetAdmin)

class StandingPredictionTeamInline(admin.TabularInline):
    model = StandingPredictionTeam
    readonly_fields = ['position', 'team']
    extra = 0

class StandingPredictionAdmin(admin.ModelAdmin):
    list_display = ['competition', 'user']
    list_filter = ['user']
    inlines = [StandingPredictionTeamInline]

admin.site.register(StandingPrediction, StandingPredictionAdmin)

class TeamPositionInline(admin.TabularInline):
    model = TeamPosition
    fields = ['position', 'team']
    extra = 0

class StandingAdmin(admin.ModelAdmin):
    list_display = ['competition', 'round']
    list_filter = ['competition']
    inlines = [TeamPositionInline]

admin.site.register(Standing, StandingAdmin)
