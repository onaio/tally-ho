# Generated by Django 2.1.1 on 2023-05-08 09:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0045_auto_20230508_0741'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ballot',
            name='electrol_race',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='electrol_races', to='tally.ElectrolRace'),
        ),
        migrations.AlterField(
            model_name='ballot',
            name='tally',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tallies', to='tally.Tally'),
        ),
    ]
