# Generated by Django 2.1.1 on 2023-06-09 08:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0045_auto_20230608_1343'),
    ]

    operations = [
        migrations.AddField(
            model_name='electrolrace',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='subconstituency',
            name='ballots',
            field=models.ManyToManyField(blank=True, related_name='sc_ballots', to='tally.Ballot'),
        ),
    ]
