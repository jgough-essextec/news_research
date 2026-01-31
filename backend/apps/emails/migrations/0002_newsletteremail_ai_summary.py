# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='newsletteremail',
            name='ai_summary',
            field=models.TextField(blank=True, help_text='AI-generated summary of email contents'),
        ),
    ]
