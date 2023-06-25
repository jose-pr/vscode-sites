# Generated by Django 4.2.2 on 2023-06-25 02:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("vscode_marketplace", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="galleryextension",
            name="statistics",
        ),
        migrations.AlterField(
            model_name="galleryextensionfile",
            name="extension_version",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assets",
                to="vscode_marketplace.galleryextensionversion",
            ),
        ),
        migrations.AlterField(
            model_name="galleryextensionproperty",
            name="extension_version",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="properties",
                to="vscode_marketplace.galleryextensionversion",
            ),
        ),
        migrations.AlterField(
            model_name="galleryextensionversion",
            name="extension",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="versions",
                to="vscode_marketplace.galleryextension",
            ),
        ),
        migrations.CreateModel(
            name="GalleryExtensionStatistic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("value", models.FloatField()),
                (
                    "extension",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statistics",
                        to="vscode_marketplace.galleryextension",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="galleryextensionstatistic",
            constraint=models.UniqueConstraint(
                fields=("name", "extension"), name="gallery_extension_statistic_uid"
            ),
        ),
    ]