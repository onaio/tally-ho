# Generated by Django 4.2.2 on 2024-10-24 07:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0054_remove_reconciliationform_number_signatures_in_vr'),
    ]

    operations = [
        migrations.AddField(
            model_name='reconciliationform',
            name='total_of_cancelled_ballots_and_ballots_inside_box',
            field=models.PositiveIntegerField(default=0, verbose_name='Total of fields 5+7'),
        ),
    ]
