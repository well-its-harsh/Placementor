from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_student_resume'),
    ]
    operations = [
        migrations.AddField(
            model_name='application',
            name='status',
            field=models.CharField(max_length=20, choices=[('applied','Applied'),('approved','Approved'),('rejected','Rejected')], default='applied'),
        ),
        migrations.AddField(
            model_name='application',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
