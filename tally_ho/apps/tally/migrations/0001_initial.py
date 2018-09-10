# Generated by Django 2.1.1 on 2018-09-10 13:11

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields
import tally_ho.libs.models.enums.actions_prior
import tally_ho.libs.models.enums.audit_resolution
import tally_ho.libs.models.enums.center_type
import tally_ho.libs.models.enums.clearance_resolution
import tally_ho.libs.models.enums.entry_version
import tally_ho.libs.models.enums.form_state
import tally_ho.libs.models.enums.gender
import tally_ho.libs.models.enums.race_type


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Archive',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Audit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('for_superadmin', models.BooleanField(default=False)),
                ('reviewed_supervisor', models.BooleanField(default=False)),
                ('reviewed_team', models.BooleanField(default=False)),
                ('blank_reconciliation', models.BooleanField(default=False)),
                ('blank_results', models.BooleanField(default=False)),
                ('damaged_form', models.BooleanField(default=False)),
                ('unclear_figures', models.BooleanField(default=False)),
                ('other', models.TextField(blank=True, null=True)),
                ('action_prior_to_recommendation', enumfields.fields.EnumIntegerField(blank=True, default=4, enum=tally_ho.libs.models.enums.actions_prior.ActionsPrior, null=True)),
                ('resolution_recommendation', enumfields.fields.EnumIntegerField(blank=True, default=0, enum=tally_ho.libs.models.enums.audit_resolution.AuditResolution, null=True)),
                ('team_comment', models.TextField(blank=True, null=True)),
                ('supervisor_comment', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('number', models.PositiveSmallIntegerField()),
                ('race_type', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.race_type.RaceType)),
            ],
            options={
                'ordering': ['number'],
            },
        ),
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('candidate_id', models.PositiveIntegerField()),
                ('full_name', models.TextField()),
                ('order', models.PositiveSmallIntegerField()),
                ('race_type', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.race_type.RaceType)),
                ('ballot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='candidates', to='tally.Ballot')),
            ],
        ),
        migrations.CreateModel(
            name='Center',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('center_type', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.center_type.CenterType)),
                ('code', models.PositiveIntegerField(unique=True)),
                ('latitude', models.FloatField(null=True)),
                ('longitude', models.FloatField(null=True)),
                ('mahalla', models.TextField()),
                ('name', models.TextField()),
                ('region', models.TextField()),
                ('village', models.TextField()),
            ],
            options={
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='Clearance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('reviewed_supervisor', models.BooleanField(default=False)),
                ('reviewed_team', models.BooleanField(default=False)),
                ('date_supervisor_modified', models.DateTimeField(null=True)),
                ('date_team_modified', models.DateTimeField(null=True)),
                ('center_name_missing', models.BooleanField(default=False)),
                ('center_name_mismatching', models.BooleanField(default=False)),
                ('center_code_missing', models.BooleanField(default=False)),
                ('center_code_mismatching', models.BooleanField(default=False)),
                ('form_already_in_system', models.BooleanField(default=False)),
                ('form_incorrectly_entered_into_system', models.BooleanField(default=False)),
                ('other', models.TextField(blank=True, null=True)),
                ('action_prior_to_recommendation', enumfields.fields.EnumIntegerField(blank=True, default=4, enum=tally_ho.libs.models.enums.actions_prior.ActionsPrior, null=True)),
                ('resolution_recommendation', enumfields.fields.EnumIntegerField(blank=True, default=0, enum=tally_ho.libs.models.enums.clearance_resolution.ClearanceResolution, null=True)),
                ('team_comment', models.TextField(blank=True, null=True)),
                ('supervisor_comment', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256, unique=True)),
                ('number', models.IntegerField(null=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='QualityControl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('passed_general', models.NullBooleanField()),
                ('passed_reconciliation', models.NullBooleanField()),
                ('passed_women', models.NullBooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='QuarantineCheck',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256, unique=True)),
                ('method', models.CharField(max_length=256, unique=True)),
                ('value', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='ReconciliationForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('entry_version', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.entry_version.EntryVersion)),
                ('ballot_number_from', models.CharField(max_length=256, verbose_name='from:')),
                ('ballot_number_to', models.CharField(max_length=256, verbose_name='to:')),
                ('is_stamped', models.BooleanField(verbose_name='Is the form stamped?')),
                ('number_ballots_received', models.PositiveIntegerField(verbose_name='Total number of ballots received by the polling station')),
                ('number_signatures_in_vr', models.PositiveIntegerField(verbose_name='Number of signatures in the VR')),
                ('number_unused_ballots', models.PositiveIntegerField(verbose_name='Number of unused ballots')),
                ('number_spoiled_ballots', models.PositiveIntegerField(verbose_name='Number of spoiled ballots')),
                ('number_cancelled_ballots', models.PositiveIntegerField(verbose_name='Number of cancelled ballots')),
                ('number_ballots_outside_box', models.PositiveIntegerField(verbose_name='Total number of ballots remaining outside the ballot box')),
                ('number_ballots_inside_box', models.PositiveIntegerField(verbose_name='Number of ballots found inside the ballot box')),
                ('number_ballots_inside_and_outside_box', models.PositiveIntegerField(verbose_name='Total number of ballots found inside and outside the ballot box')),
                ('number_unstamped_ballots', models.PositiveIntegerField(verbose_name='Number of unstamped ballots')),
                ('number_invalid_votes', models.PositiveIntegerField(verbose_name='Number of invalid votes (including the blanks)')),
                ('number_valid_votes', models.PositiveIntegerField(verbose_name='Number of valid votes')),
                ('number_sorted_and_counted', models.PositiveIntegerField(verbose_name='Total number of the sorted and counted ballots')),
                ('signature_polling_officer_1', models.BooleanField(verbose_name='Is the form signed by polling officer 1?')),
                ('signature_polling_officer_2', models.BooleanField(verbose_name='Is the form signed by polling officer 2?')),
                ('signature_polling_station_chair', models.BooleanField(verbose_name='Is the form signed by the polling station chair?')),
                ('signature_dated', models.BooleanField(verbose_name='Is the form dated?')),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('entry_version', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.entry_version.EntryVersion)),
                ('votes', models.PositiveIntegerField()),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='results', to='tally.Candidate')),
            ],
        ),
        migrations.CreateModel(
            name='ResultForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('audited_count', models.PositiveIntegerField(default=0)),
                ('barcode', models.CharField(max_length=9, unique=True)),
                ('date_seen', models.DateTimeField(null=True)),
                ('form_stamped', models.NullBooleanField()),
                ('form_state', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.form_state.FormState)),
                ('gender', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.gender.Gender, null=True)),
                ('name', models.CharField(max_length=256, null=True)),
                ('rejected_count', models.PositiveIntegerField(default=0)),
                ('serial_number', models.PositiveIntegerField(null=True, unique=True)),
                ('skip_quarantine_checks', models.BooleanField(default=False)),
                ('station_number', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('is_replacement', models.BooleanField(default=False)),
                ('ballot', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='tally.Ballot')),
                ('center', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='tally.Center')),
            ],
        ),
        migrations.CreateModel(
            name='Station',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('gender', enumfields.fields.EnumIntegerField(enum=tally_ho.libs.models.enums.gender.Gender)),
                ('percent_archived', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('percent_received', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('registrants', models.PositiveIntegerField(null=True)),
                ('station_number', models.PositiveSmallIntegerField()),
                ('center', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stations', to='tally.Center')),
            ],
        ),
        migrations.CreateModel(
            name='SubConstituency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('code', models.PositiveSmallIntegerField()),
                ('field_office', models.CharField(max_length=256)),
                ('number_of_ballots', models.PositiveSmallIntegerField(null=True)),
                ('races', models.PositiveSmallIntegerField(null=True)),
                ('ballot_component', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sc_component', to='tally.Ballot')),
                ('ballot_general', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sc_general', to='tally.Ballot')),
                ('ballot_women', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sc_women', to='tally.Ballot')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('reset_password', models.BooleanField(default=True)),
            ],
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AddField(
            model_name='station',
            name='sub_constituency',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='stations', to='tally.SubConstituency'),
        ),
        migrations.AddField(
            model_name='resultform',
            name='created_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='created_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='resultform',
            name='office',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='tally.Office'),
        ),
        migrations.AddField(
            model_name='resultform',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='result',
            name='result_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='results', to='tally.ResultForm'),
        ),
        migrations.AddField(
            model_name='result',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='reconciliationform',
            name='result_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tally.ResultForm'),
        ),
        migrations.AddField(
            model_name='reconciliationform',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='quarantinecheck',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='qualitycontrol',
            name='result_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tally.ResultForm'),
        ),
        migrations.AddField(
            model_name='qualitycontrol',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='clearance',
            name='result_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='clearances', to='tally.ResultForm'),
        ),
        migrations.AddField(
            model_name='clearance',
            name='supervisor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='clearance_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='clearance',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='center',
            name='office',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='tally.Office'),
        ),
        migrations.AddField(
            model_name='center',
            name='sub_constituency',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='centers', to='tally.SubConstituency'),
        ),
        migrations.AddField(
            model_name='audit',
            name='quarantine_checks',
            field=models.ManyToManyField(to='tally.QuarantineCheck'),
        ),
        migrations.AddField(
            model_name='audit',
            name='result_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tally.ResultForm'),
        ),
        migrations.AddField(
            model_name='audit',
            name='supervisor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='audit_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='audit',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='archive',
            name='result_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tally.ResultForm'),
        ),
        migrations.AddField(
            model_name='archive',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
    ]
