# Generated by Django 4.2.20 on 2025-04-01 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_remove_patientprofile_age_customuser_dob_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]
