# Generated by Django 4.2.20 on 2025-04-02 20:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_merge_20250402_1455'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patientprofile',
            name='phone_number',
        ),
    ]
