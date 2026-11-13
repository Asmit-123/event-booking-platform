from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="registration_deadline",
            field=models.DateTimeField(
                blank=True,
                help_text="Optional deadline for attendee registration.",
                null=True,
            ),
        ),
    ]
