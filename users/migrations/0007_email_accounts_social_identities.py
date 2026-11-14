from collections import defaultdict

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def normalize_and_check_emails(apps, schema_editor):
    Account = apps.get_model('users', 'Account')
    database = schema_editor.connection.alias
    seen = defaultdict(list)
    accounts = list(Account.objects.using(database).all().only('pk', 'email'))

    for account in accounts:
        normalized = (account.email or '').strip().lower()
        if not normalized:
            raise RuntimeError(
                'Every existing account needs an email before email login can be enabled.'
            )
        seen[normalized].append(account.pk)

    duplicates = [ids for ids in seen.values() if len(ids) > 1]
    if duplicates:
        raise RuntimeError(
            'Duplicate emails (ignoring case) exist in the account table. Resolve them '
            'before applying the email account migration.'
        )

    for account in accounts:
        account.email = (account.email or '').strip().lower()
    if accounts:
        Account.objects.using(database).bulk_update(accounts, ['email'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_profile_image'),
    ]

    operations = [
        migrations.RunPython(normalize_and_check_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='account',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.CreateModel(
            name='SocialIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('google', 'Google'), ('github', 'GitHub')], max_length=20)),
                ('provider_uid', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_identities', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='socialidentity',
            constraint=models.UniqueConstraint(fields=('provider', 'provider_uid'), name='unique_social_provider_identity'),
        ),
        migrations.AddConstraint(
            model_name='socialidentity',
            constraint=models.UniqueConstraint(fields=('user', 'provider'), name='unique_user_social_provider'),
        ),
    ]
