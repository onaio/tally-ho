# Generated by Django 2.1.1 on 2020-07-13 11:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0032_auto_20200713_0915'),
    ]

    operations = [
        migrations.CreateModel(
            name='Constituency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('center', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='constituency', to='tally.Center')),
                ('tally', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='constituency', to='tally.Tally')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='constituency',
            unique_together={('name', 'tally')},
        ),
    ]
