# Generated by Django 5.1.6 on 2025-04-14 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_alter_patientprofile_phone_number_doctoravailability'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='doctoravailability',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='doctoravailability',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='doctoravailability',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False)), fields=('doctor', 'date', 'start_time'), name='unique_active_availability'),
        ),
    ]
