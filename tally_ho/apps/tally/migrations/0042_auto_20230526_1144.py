# Generated by Django 2.1.1 on 2023-05-26 11:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0041_auto_20230524_1145'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='electrolrace',
            unique_together={('election_level', 'ballot_name', 'tally')},
        ),
    ]
