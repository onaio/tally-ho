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

        # Adding model 'Candidate'
        db.create_table(u'tally_candidate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ballot', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Ballot'])),
            ('full_name', self.gf('django.db.models.fields.TextField')()),
            ('race_type', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
        ))
        db.send_create_signal('tally', ['Candidate'])

        # Adding model 'Center'
        db.create_table(u'tally_center', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('sub_constituency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.SubConstituency'], null=True)),
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
            ('result_form', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['tally.ResultForm'], unique=True)),
            ('ballot_number_from', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('ballot_number_to', self.gf('django.db.models.fields.PositiveIntegerField')()),
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
            ('remarks', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('tally', ['ReconciliationForm'])

        # Adding model 'Result'
        db.create_table(u'tally_result', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('candidate', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Candidate'])),
            ('result_form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.ResultForm'])),
            ('entry_version', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
        ))
        db.send_create_signal('tally', ['Result'])

        # Adding model 'ResultForm'
        db.create_table(u'tally_resultform', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ballot', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Ballot'], null=True)),
            ('center', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Center'], null=True)),
            ('barcode', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('form_stamped', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('form_state', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('gender', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256, null=True)),
            ('office', self.gf('django.db.models.fields.CharField')(max_length=256, null=True)),
            ('serial_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('station_number', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
        ))
        db.send_create_signal('tally', ['ResultForm'])

        # Adding model 'SubConstituency'
        db.create_table(u'tally_subconstituency', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ballot_general', self.gf('django.db.models.fields.related.ForeignKey')(related_name='ballot_general', null=True, to=orm['tally.Ballot'])),
            ('ballot_women', self.gf('django.db.models.fields.related.ForeignKey')(related_name='ballot_women', null=True, to=orm['tally.Ballot'])),
            ('code', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('component_ballot', self.gf('django.db.models.fields.BooleanField')()),
            ('field_office', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('number_of_ballots', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
            ('races', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
        ))
        db.send_create_signal('tally', ['SubConstituency'])

        # Adding model 'Station'
        db.create_table(u'tally_station', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('center', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.Center'])),
            ('sub_constituency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tally.SubConstituency'])),
            ('gender', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('registrants', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('station_number', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('tally', ['Station'])


    def backwards(self, orm):
        # Deleting model 'Ballot'
        db.delete_table(u'tally_ballot')

        # Deleting model 'Candidate'
        db.delete_table(u'tally_candidate')

        # Deleting model 'Center'
        db.delete_table(u'tally_center')

        # Deleting model 'Race'
        db.delete_table(u'tally_race')

        # Removing M2M table for field sub_constituency on 'Race'
        db.delete_table(db.shorten_name(u'tally_race_sub_constituency'))

        # Deleting model 'ReconciliationForm'
        db.delete_table(u'tally_reconciliationform')

        # Deleting model 'Result'
        db.delete_table(u'tally_result')

        # Deleting model 'ResultForm'
        db.delete_table(u'tally_resultform')

        # Deleting model 'SubConstituency'
        db.delete_table(u'tally_subconstituency')

        # Deleting model 'Station'
        db.delete_table(u'tally_station')


    models = {
        'tally.ballot': {
            'Meta': {'object_name': 'Ballot'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'race_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'tally.candidate': {
            'Meta': {'object_name': 'Candidate'},
            'ballot': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Ballot']"}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'full_name': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'race_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'tally.center': {
            'Meta': {'object_name': 'Center'},
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
            'sub_constituency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.SubConstituency']", 'null': 'True'}),
            'village': ('django.db.models.fields.TextField', [], {})
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
            'ballot_number_from': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'ballot_number_to': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
            'remarks': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['tally.ResultForm']", 'unique': 'True'})
        },
        'tally.result': {
            'Meta': {'object_name': 'Result'},
            'candidate': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Candidate']"}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'entry_version': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'result_form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.ResultForm']"})
        },
        'tally.resultform': {
            'Meta': {'object_name': 'ResultForm'},
            'ballot': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Ballot']", 'null': 'True'}),
            'barcode': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'center': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Center']", 'null': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'form_stamped': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'form_state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'gender': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True'}),
            'office': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True'}),
            'serial_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'station_number': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'})
        },
        'tally.station': {
            'Meta': {'object_name': 'Station'},
            'center': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.Center']"}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'registrants': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'station_number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'sub_constituency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tally.SubConstituency']"})
        },
        'tally.subconstituency': {
            'Meta': {'object_name': 'SubConstituency'},
            'ballot_general': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ballot_general'", 'null': 'True', 'to': "orm['tally.Ballot']"}),
            'ballot_women': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ballot_women'", 'null': 'True', 'to': "orm['tally.Ballot']"}),
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