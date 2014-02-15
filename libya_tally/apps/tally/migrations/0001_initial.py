# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Ballot'
        db.create_table(u'tally_ballot', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('number', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('race_type', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
        ))
        db.send_create_signal('tally', ['Ballot'])

        # Adding model 'SubConstituency'
        db.create_table(u'tally_subconstituency', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ballot_general', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sc_general', null=True, to=orm['tally.Ballot'])),
            ('ballot_women', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sc_women', null=True, to=orm['tally.Ballot'])),
            ('code', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('component_ballot', self.gf('django.db.models.fields.BooleanField')()),
            ('field_office', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('number_of_ballots', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
            ('races', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
        ))
        db.send_create_signal('tally', ['SubConstituency'])

        # Adding model 'Center'
        db.create_table(u'tally_center', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('sub_constituency', self.gf('django.db.models.fields.related.ForeignKey')(related_name='centers', null=True, to=orm['tally.SubConstituency'])),
            ('center_type', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('code', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('latitude', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('longitude', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('mahalla', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('office', self.gf('django.db.models.fields.TextField')()),
            ('region', self.gf('django.db.models.fields.TextField')()),
            ('village', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('tally', ['Center'])

        # Adding model 'ResultForm'
        db.create_table(u'tally_resultform', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ballot', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Ballot'], null=True)),
            ('center', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Center'], null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('created_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='created_user', null=True, to=orm['auth.User'])),
            ('barcode', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('date_seen', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('form_stamped', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('form_state', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('gender', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256, null=True)),
            ('office', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('rejected_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('serial_number', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True, null=True)),
            ('skip_quarantine_checks', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('station_number', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('tally', ['ResultForm'])

        # Adding model 'Archive'
        db.create_table(u'tally_archive', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.ResultForm'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('tally', ['Archive'])

        # Adding model 'QuarantineCheck'
        db.create_table(u'tally_quarantinecheck', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=256)),
            ('method', self.gf('django.db.models.fields.CharField')(unique=True, max_length=256)),
            ('value', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('tally', ['QuarantineCheck'])

        # Adding model 'Audit'
        db.create_table(u'tally_audit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.ResultForm'])),
            ('supervisor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='audit_user', null=True, to=orm['auth.User'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('for_superadmin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('reviewed_supervisor', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('reviewed_team', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('blank_reconciliation', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('blank_results', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('damaged_form', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('unclear_figures', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('other', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('action_prior_to_recommendation', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('resolution_recommendation', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True, blank=True)),
            ('team_comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('supervisor_comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('tally', ['Audit'])

        # Adding M2M table for field quarantine_checks on 'Audit'
        m2m_table_name = db.shorten_name(u'tally_audit_quarantine_checks')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('audit', models.ForeignKey(orm['tally.audit'], null=False)),
            ('quarantinecheck', models.ForeignKey(orm['tally.quarantinecheck'], null=False))
        ))
        db.create_unique(m2m_table_name, ['audit_id', 'quarantinecheck_id'])

        # Adding model 'Candidate'
        db.create_table(u'tally_candidate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ballot', self.gf('django.db.models.fields.related.ForeignKey')(related_name='candidates', to=orm['tally.Ballot'])),
            ('candidate_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('full_name', self.gf('django.db.models.fields.TextField')()),
            ('order', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('race_type', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
        ))
        db.send_create_signal('tally', ['Candidate'])

        # Adding model 'Clearance'
        db.create_table(u'tally_clearance', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(related_name='clearances', to=orm['tally.ResultForm'])),
            ('supervisor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='clearance_user', null=True, to=orm['auth.User'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('reviewed_supervisor', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('reviewed_team', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_supervisor_modified', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('date_team_modified', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('center_name_missing', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('center_name_mismatching', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('center_code_missing', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('center_code_mismatching', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('form_already_in_system', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('form_incorrectly_entered_into_system', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('other', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('action_prior_to_recommendation', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('resolution_recommendation', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True, blank=True)),
            ('team_comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('supervisor_comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('tally', ['Clearance'])

        # Adding model 'QualityControl'
        db.create_table(u'tally_qualitycontrol', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.ResultForm'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('passed_general', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('passed_reconciliation', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('passed_women', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
        ))
        db.send_create_signal('tally', ['QualityControl'])

        # Adding model 'Race'
        db.create_table(u'tally_race', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('race_type', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
        ))
        db.send_create_signal('tally', ['Race'])

        # Adding M2M table for field sub_constituency on 'Race'
        m2m_table_name = db.shorten_name(u'tally_race_sub_constituency')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('race', models.ForeignKey(orm['tally.race'], null=False)),
            ('subconstituency', models.ForeignKey(orm['tally.subconstituency'], null=False))
        ))
        db.create_unique(m2m_table_name, ['race_id', 'subconstituency_id'])

        # Adding model 'ReconciliationForm'
        db.create_table(u'tally_reconciliationform', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.ResultForm'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('entry_version', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('ballot_number_from', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('ballot_number_to', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('is_stamped', self.gf('django.db.models.fields.BooleanField')()),
            ('number_ballots_received', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_signatures_in_vr', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_unused_ballots', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_spoiled_ballots', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_cancelled_ballots', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_ballots_outside_box', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_ballots_inside_box', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_ballots_inside_and_outside_box', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_unstamped_ballots', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_invalid_votes', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_valid_votes', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number_sorted_and_counted', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('signature_polling_officer_1', self.gf('django.db.models.fields.BooleanField')()),
            ('signature_polling_officer_2', self.gf('django.db.models.fields.BooleanField')()),
            ('signature_polling_station_chair', self.gf('django.db.models.fields.BooleanField')()),
            ('signature_dated', self.gf('django.db.models.fields.BooleanField')()),
        ))
        db.send_create_signal('tally', ['ReconciliationForm'])

        # Adding model 'Result'
        db.create_table(u'tally_result', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('candidate', self.gf('django.db.models.fields.related.ForeignKey')(related_name='candidates', to=orm['tally.Candidate'])),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(related_name='results', to=orm['tally.ResultForm'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('entry_version', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('votes', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('tally', ['Result'])

        # Adding model 'Station'
        db.create_table(u'tally_station', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('center', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stations', to=orm['tally.Center'])),
            ('sub_constituency', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stations', to=orm['tally.SubConstituency'])),
            ('gender', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('registrants', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('station_number', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('tally', ['Station'])


    def backwards(self, orm):
        # Deleting model 'Ballot'
        db.delete_table(u'tally_ballot')

        # Deleting model 'SubConstituency'
        db.delete_table(u'tally_subconstituency')

        # Deleting model 'Center'
        db.delete_table(u'tally_center')

        # Deleting model 'ResultForm'
        db.delete_table(u'tally_resultform')

        # Deleting model 'Archive'
        db.delete_table(u'tally_archive')

        # Deleting model 'QuarantineCheck'
        db.delete_table(u'tally_quarantinecheck')

        # Deleting model 'Audit'
        db.delete_table(u'tally_audit')

        # Removing M2M table for field quarantine_checks on 'Audit'
        db.delete_table(db.shorten_name(u'tally_audit_quarantine_checks'))

        # Deleting model 'Candidate'
        db.delete_table(u'tally_candidate')

        # Deleting model 'Clearance'
        db.delete_table(u'tally_clearance')

        # Deleting model 'QualityControl'
        db.delete_table(u'tally_qualitycontrol')

        # Deleting model 'Race'
        db.delete_table(u'tally_race')

        # Removing M2M table for field sub_constituency on 'Race'
        db.delete_table(db.shorten_name(u'tally_race_sub_constituency'))

        # Deleting model 'ReconciliationForm'
        db.delete_table(u'tally_reconciliationform')

        # Deleting model 'Result'
        db.delete_table(u'tally_result')

        # Deleting model 'Station'
        db.delete_table(u'tally_station')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tally.archive': {
            'Meta': {'object_name': 'Archive'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.ResultForm']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'tally.audit': {
            'Meta': {'object_name': 'Audit'},
            'action_prior_to_recommendation': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'blank_reconciliation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'blank_results': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'damaged_form': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'for_superadmin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'other': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'quarantine_checks': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['tally.QuarantineCheck']", 'symmetrical': 'False'}),
            'resolution_recommendation': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.ResultForm']"}),
            'reviewed_supervisor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'reviewed_team': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'supervisor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'audit_user'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'supervisor_comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'team_comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'unclear_figures': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'tally.ballot': {
            'Meta': {'ordering': "['number']", 'object_name': 'Ballot'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'race_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'tally.candidate': {
            'Meta': {'object_name': 'Candidate'},
            'ballot': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'candidates'", 'to': "orm['tally.Ballot']"}),
            'candidate_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'full_name': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'race_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'tally.center': {
            'Meta': {'ordering': "['code']", 'object_name': 'Center'},
            'center_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'code': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mahalla': ('django.db.models.fields.TextField', [], {}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'office': ('django.db.models.fields.TextField', [], {}),
            'region': ('django.db.models.fields.TextField', [], {}),
            'sub_constituency': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'centers'", 'null': 'True', 'to': "orm['tally.SubConstituency']"}),
            'village': ('django.db.models.fields.TextField', [], {})
        },
        'tally.clearance': {
            'Meta': {'object_name': 'Clearance'},
            'action_prior_to_recommendation': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'center_code_mismatching': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'center_code_missing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'center_name_mismatching': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'center_name_missing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_supervisor_modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_team_modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'form_already_in_system': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'form_incorrectly_entered_into_system': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'other': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'resolution_recommendation': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clearances'", 'to': "orm['tally.ResultForm']"}),
            'reviewed_supervisor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'reviewed_team': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'supervisor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clearance_user'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'supervisor_comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'team_comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'tally.qualitycontrol': {
            'Meta': {'object_name': 'QualityControl'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'passed_general': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'passed_reconciliation': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'passed_women': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.ResultForm']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'tally.quarantinecheck': {
            'Meta': {'object_name': 'QuarantineCheck'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '256'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '256'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'tally.race': {
            'Meta': {'object_name': 'Race'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'race_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'sub_constituency': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['tally.SubConstituency']", 'symmetrical': 'False'})
        },
        'tally.reconciliationform': {
            'Meta': {'object_name': 'ReconciliationForm'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'ballot_number_from': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'ballot_number_to': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'entry_version': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_stamped': ('django.db.models.fields.BooleanField', [], {}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number_ballots_inside_and_outside_box': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_ballots_inside_box': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_ballots_outside_box': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_ballots_received': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_cancelled_ballots': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_invalid_votes': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_signatures_in_vr': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_sorted_and_counted': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_spoiled_ballots': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_unstamped_ballots': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_unused_ballots': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number_valid_votes': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.ResultForm']"}),
            'signature_dated': ('django.db.models.fields.BooleanField', [], {}),
            'signature_polling_officer_1': ('django.db.models.fields.BooleanField', [], {}),
            'signature_polling_officer_2': ('django.db.models.fields.BooleanField', [], {}),
            'signature_polling_station_chair': ('django.db.models.fields.BooleanField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        'tally.result': {
            'Meta': {'object_name': 'Result'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'candidate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'candidates'", 'to': "orm['tally.Candidate']"}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'entry_version': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['tally.ResultForm']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'tally.resultform': {
            'Meta': {'object_name': 'ResultForm'},
            'ballot': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Ballot']", 'null': 'True'}),
            'barcode': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'center': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Center']", 'null': 'True', 'blank': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_user'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'date_seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'form_stamped': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'form_state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'gender': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True'}),
            'office': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'rejected_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'serial_number': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'null': 'True'}),
            'skip_quarantine_checks': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'station_number': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        'tally.station': {
            'Meta': {'object_name': 'Station'},
            'center': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stations'", 'to': "orm['tally.Center']"}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'registrants': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'station_number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'sub_constituency': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stations'", 'to': "orm['tally.SubConstituency']"})
        },
        'tally.subconstituency': {
            'Meta': {'object_name': 'SubConstituency'},
            'ballot_general': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sc_general'", 'null': 'True', 'to': "orm['tally.Ballot']"}),
            'ballot_women': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sc_women'", 'null': 'True', 'to': "orm['tally.Ballot']"}),
            'code': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'component_ballot': ('django.db.models.fields.BooleanField', [], {}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'field_office': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number_of_ballots': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'races': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'})
        }
    }

    complete_apps = ['tally']