# Generated by Django 5.0.2 on 2024-09-23 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0005_remove_subject_topic'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uploaded_file', models.FileField(upload_to='documents/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
