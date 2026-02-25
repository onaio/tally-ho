from django.db import migrations


def cleanup_duplicate_active_records(apps, schema_editor):
    """For each model, find result_forms with multiple active records.
    Keep the most recently modified and deactivate the rest."""
    from django.db.models import Count

    model_names = ['Audit', 'QualityControl', 'Clearance']

    for model_name in model_names:
        Model = apps.get_model('tally', model_name)

        dupes = (
            Model.objects
            .filter(active=True)
            .values('result_form_id')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )

        total_deactivated = 0
        for entry in dupes:
            rf_id = entry['result_form_id']
            active_records = list(
                Model.objects
                .filter(result_form_id=rf_id, active=True)
                .order_by('-modified_date')
            )
            to_deactivate = [r.pk for r in active_records[1:]]
            count = Model.objects.filter(
                pk__in=to_deactivate
            ).update(active=False)
            total_deactivated += count

        if total_deactivated:
            print(
                f"\n  {model_name}: deactivated {total_deactivated} "
                f"duplicate active records"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0077_alter_quarantinecheck_constraints'),
    ]

    operations = [
        migrations.RunPython(
            cleanup_duplicate_active_records,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
