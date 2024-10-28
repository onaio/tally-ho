# Generated by Django 4.2.2 on 2024-10-26 15:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0056_reconciliationform_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reconciliationform',
            name='ballot_number_from',
            field=models.CharField(max_length=256, null=True, verbose_name='from:'),
        ),
        migrations.AlterField(
            model_name='reconciliationform',
            name='ballot_number_to',
            field=models.CharField(max_length=256, null=True, verbose_name='to:'),
        ),
    ]