from django.db import migrations

def update_default_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.filter(id=1).update(
        domain='127.0.0.1:8000',
        name='Grand Lodge of Kosovo'
    )

class Migration(migrations.Migration):
    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_default_site),
    ] 