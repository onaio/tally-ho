# Generated by Django 2.1.1 on 2023-05-23 13:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0050_auto_20230523_1320'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='electrolrace',
            options={'ordering': ['ballot_name']},
        ),
        migrations.AlterUniqueTogether(
            name='electrolrace',
            unique_together={('election_level', 'ballot_name')},
        ),
    ]
