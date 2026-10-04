# apps/counties/models.py
import uuid

from django.db import models

from apps.common.models import TimeStampedModel
from .managers import CountyManager, SubCountyManager, WardManager


class County(TimeStampedModel):
    """
    One of Kenya's 47 counties. Keyed by its official 3-digit code
    ("001" – "047") so external systems can reference it directly.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=3, unique=True, db_index=True,
        help_text='Official county code, e.g. "032" for Nakuru.',
    )
    name = models.CharField(max_length=60, unique=True, db_index=True)
    region = models.CharField(max_length=40, db_index=True)

    # Optional geography
    capital = models.CharField(max_length=80, blank=True)
    area_km2 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    population_2019 = models.PositiveIntegerField(null=True, blank=True)

    # Display
    icon = models.CharField(max_length=60, blank=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    objects = CountyManager()

    class Meta:
        ordering = ["code"]
        verbose_name = "County"
        verbose_name_plural = "Counties"

    def __str__(self):
        return f"{self.code} {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)[:60]
        super().save(*args, **kwargs)


class SubCounty(TimeStampedModel):
    """
    A sub-county (constituency) within a county. Optional to use —
    some flows only need the county.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    county = models.ForeignKey(
        County, on_delete=models.CASCADE, related_name="sub_counties",
    )
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=6, blank=True)

    objects = SubCountyManager()

    class Meta:
        ordering = ["county__code", "name"]
        unique_together = [("county", "name")]
        verbose_name = "Sub-county"
        verbose_name_plural = "Sub-counties"

    def __str__(self):
        return f"{self.name} ({self.county.code})"


class Ward(TimeStampedModel):
    """
    A ward (ward / location) within a sub-county. Used by extension
    officers to organise field-day attendance and by the dashboard for
    granular reporting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_county = models.ForeignKey(
        SubCounty, on_delete=models.CASCADE, related_name="wards",
    )
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=8, blank=True)

    objects = WardManager()

    class Meta:
        ordering = ["sub_county__county__code", "sub_county__name", "name"]
        unique_together = [("sub_county", "name")]
        verbose_name = "Ward"
        verbose_name_plural = "Wards"

    def __str__(self):
        return f"{self.name} ({self.sub_county.name})"