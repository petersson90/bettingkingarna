# Generated by Django 4.1.5 on 2023-01-15 22:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('short', models.CharField(max_length=4)),
            ],
        ),
    ]
