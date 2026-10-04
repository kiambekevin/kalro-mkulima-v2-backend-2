# apps/counties/services.py
"""
Reference-data services. These are mostly used by management commands
and by the `accounts` app to resolve a county from a user's input.
"""
import logging

from django.db import transaction

from .constants import REGIONS
from .models import County, SubCounty, Ward

logger = logging.getLogger(__name__)


# ───────────────────────────── Lookups ─────────────────────────────

def resolve_county(value):
    """
    Accept a county by code ("032"), name ("Nakuru"), or UUID. Returns
    a County instance or None.
    """
    if not value:
        return None

    if hasattr(value, "pk"):
        return value

    value = str(value).strip()
    if not value:
        return None

    if len(value) == 3 and value.isdigit():
        return County.objects.filter(code=value).first()

    return County.objects.filter(name__iexact=value).first()


def resolve_sub_county(county, value):
    if not county or not value:
        return None
    return (
        SubCounty.objects
        .filter(county=county, name__iexact=str(value).strip())
        .first()
    )


def resolve_ward(sub_county, value):
    if not sub_county or not value:
        return None
    return (
        Ward.objects
        .filter(sub_county=sub_county, name__iexact=str(value).strip())
        .first()
    )


# ───────────────────────────── Validation ─────────────────────────────

def validate_region(region: str) -> bool:
    return region in REGIONS


# ───────────────────────────── Bulk import ─────────────────────────────

@transaction.atomic
def import_counties(payload: list[dict]) -> dict:
    """
    Upsert a list of counties from a JSON payload. Each item:
        { "code": "032", "name": "Nakuru", "region": "Rift Valley",
          "capital": "Nakuru", "population_2019": 2162202,
          "area_km2": 7509.5 }
    """
    created = updated = 0
    for item in payload:
        code = str(item["code"]).zfill(3)
        obj, is_new = County.objects.update_or_create(
            code=code,
            defaults={
                "name": item["name"],
                "region": item.get("region", ""),
                "capital": item.get("capital", ""),
                "population_2019": item.get("population_2019"),
                "area_km2": item.get("area_km2"),
            },
        )
        created += 1 if is_new else 0
        updated += 0 if is_new else 1

    logger.info("Imported counties: %d created, %d updated.", created, updated)
    return {"created": created, "updated": updated}


@transaction.atomic
def import_sub_counties(payload: list[dict]) -> dict:
    """
    Each item: { "county_code": "032", "name": "Nakuru East", "code": "" }
    """
    created = updated = skipped = 0
    for item in payload:
        county = County.objects.filter(code=str(item["county_code"]).zfill(3)).first()
        if not county:
            skipped += 1
            continue
        _, is_new = SubCounty.objects.update_or_create(
            county=county,
            name=item["name"],
            defaults={"code": item.get("code", "")},
        )
        created += 1 if is_new else 0
        updated += 0 if is_new else 1
    return {"created": created, "updated": updated, "skipped": skipped}


@transaction.atomic
def import_wards(payload: list[dict]) -> dict:
    """
    Each item: { "county_code": "032", "sub_county": "Nakuru East", "name": "Biashara" }
    """
    created = updated = skipped = 0
    for item in payload:
        county = County.objects.filter(code=str(item["county_code"]).zfill(3)).first()
        if not county:
            skipped += 1
            continue
        sc = SubCounty.objects.filter(county=county, name=item["sub_county"]).first()
        if not sc:
            skipped += 1
            continue
        _, is_new = Ward.objects.update_or_create(
            sub_county=sc,
            name=item["name"],
            defaults={"code": item.get("code", "")},
        )
        created += 1 if is_new else 0
        updated += 0 if is_new else 1
    return {"created": created, "updated": updated, "skipped": skipped}