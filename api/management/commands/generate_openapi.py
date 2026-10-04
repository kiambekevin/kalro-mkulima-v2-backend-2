# api/management/commands/generate_openapi.py
"""
Dump the OpenAPI schema to a file. Useful in CI:

    python manage.py generate_openapi --file=openapi.yaml
"""
from django.core.management.base import BaseCommand
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import (
    OpenApiJsonRenderer,
    OpenApiYamlRenderer,
)
from drf_spectacular.settings import spectacular_settings


class Command(BaseCommand):
    help = "Generate the OpenAPI schema (JSON or YAML)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default="openapi.yaml",
            help="Output file path. Extension determines format (.json or .yaml).",
        )
        parser.add_argument(
            "--validate", action="store_true",
            help="Validate the generated schema (requires drf-spectacular[sidecar]).",
        )

    def handle(self, *args, **options):
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)

        from api.v1.openapi import apply_public_endpoints
        schema = apply_public_endpoints(schema)

        path = options["file"]
        if path.endswith(".json"):
            renderer = OpenApiJsonRenderer()
        else:
            renderer = OpenApiYamlRenderer()

        rendered = renderer.render(schema, renderer_context={})
        with open(path, "wb") as fh:
            fh.write(rendered)

        self.stdout.write(self.style.SUCCESS(f"Wrote {path}"))

        if options["validate"]:
            try:
                from drf_spectacular.validation import validate_schema
                validate_schema(schema)
                self.stdout.write(self.style.SUCCESS("Schema is valid."))
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"Schema validation failed: {exc}"))