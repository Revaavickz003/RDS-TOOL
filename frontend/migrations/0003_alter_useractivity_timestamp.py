# Generated by Django 5.0.4 on 2024-05-29 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_lead_finallybudjet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useractivity',
            name='timestamp',
            field=models.DateTimeField(),
        ),
    ]