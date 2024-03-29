# Generated by Django 4.2.6 on 2023-10-31 10:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0005_alter_bet_updated'),
    ]

    operations = [
        migrations.CreateModel(
            name='StandingPredictionTeam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField()),
                ('standing_prediction', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='betting.standingprediction')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='betting.team')),
            ],
        ),
        migrations.AddConstraint(
            model_name='standingpredictionteam',
            constraint=models.UniqueConstraint(fields=('standing_prediction', 'position'), name='unique_position_per_prediction'),
        ),
        migrations.AddConstraint(
            model_name='standingpredictionteam',
            constraint=models.UniqueConstraint(fields=('standing_prediction', 'team'), name='unique_team_per_prediction'),
        ),
    ]
