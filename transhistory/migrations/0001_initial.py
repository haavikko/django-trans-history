# -*- coding: utf-8 -*-
# Generated by Django 1.11.15.dev20180729042848 on 2020-03-06 17:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Revision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pg_transaction_id', models.BigIntegerField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('committed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('committer', models.IntegerField(blank=True, db_index=True, null=True)),
            ],
        ),
    ]