# Generated by Django 4.0 on 2023-05-16 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0039_auto_20211230_1449'),
    ]

    operations = [
        migrations.AlterField(
            model_name='qualitycontrol',
            name='passed_general',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='qualitycontrol',
            name='passed_presidential',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='qualitycontrol',
            name='passed_reconciliation',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='qualitycontrol',
            name='passed_women',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='resultform',
            name='form_stamped',
            field=models.BooleanField(null=True),
        ),
    ]