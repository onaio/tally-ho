# Generated by Django 2.1.1 on 2023-05-08 07:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0044_subconstituency_ballots'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subconstituency',
            name='constituency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='constituency', to='tally.Constituency'),
        ),
        migrations.AlterField(
            model_name='subconstituency',
            name='tally',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tally', to='tally.Tally'),
        ),
    ]
