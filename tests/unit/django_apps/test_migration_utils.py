from django.db import models
from django.test import override_settings

from shared.django_apps.migration_utils import *


class TestMigrationUtils:
    def test_risky_add_field(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AddField.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AddField.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyAddField("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyAddField("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_alter_field(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AlterField.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AlterField.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyAlterField("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyAlterField("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_remove_field(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RemoveField.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RemoveField.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyRemoveField("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyRemoveField("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_alter_unique_together(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AlterUniqueTogether.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AlterUniqueTogether.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyAlterUniqueTogether("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyAlterUniqueTogether("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_alter_index_together(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AlterIndexTogether.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AlterIndexTogether.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyAlterIndexTogether("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyAlterIndexTogether("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_add_index(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AddIndex.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AddIndex.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyAddIndex("foo", models.Index(name="bar", fields=["id"]))
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyAddIndex("foo", models.Index(name="bar", fields=["id"]))
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_remove_index(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RemoveIndex.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RemoveIndex.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyRemoveIndex("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyRemoveIndex("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_add_constraint(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AddConstraint.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.AddConstraint.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyAddConstraint("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyAddConstraint("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_remove_constraint(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RemoveConstraint.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RemoveConstraint.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyRemoveConstraint("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyRemoveConstraint("foo", "bar")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_run_sql(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RunSQL.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RunSQL.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyRunSQL("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyRunSQL("foo", "bar", None)
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called

    def test_risky_run_python(self, mocker):
        mock_forward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RunPython.database_forwards"
        )
        mock_backward = mocker.patch(
            "shared.django_apps.migration_utils.migrations.RunPython.database_backwards"
        )
        with override_settings(SKIP_RISKY_MIGRATION_STEPS=True):
            migration = RiskyRunPython(lambda *args, **kwargs: "")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert not mock_forward.called
            assert not mock_backward.called

        with override_settings(SKIP_RISKY_MIGRATION_STEPS=False):
            migration = RiskyRunPython(lambda *args, **kwargs: "")
            migration.database_forwards("foo", "bar", "baz", "qux")
            migration.database_backwards("foo", "bar", "baz", "qux")
            assert mock_forward.called
            assert mock_backward.called
