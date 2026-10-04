# apps/counties/admin.py
from django.contrib import admin

from .models import County, SubCounty, Ward


class SubCountyInline(admin.TabularInline):
    model = SubCounty
    extra = 0
    fields = ("name", "code")
    show_change_link = True


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "region", "capital",
        "population_2019", "area_km2", "sub_county_count",
    )
    list_filter = ("region",)
    search_fields = ("code", "name", "capital")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (SubCountyInline,)
    ordering = ("code",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Sub-counties")
    def sub_county_count(self, obj):
        return obj.sub_counties.count()


class WardInline(admin.TabularInline):
    model = Ward
    extra = 0
    fields = ("name", "code")


@admin.register(SubCounty)
class SubCountyAdmin(admin.ModelAdmin):
    list_display = ("name", "county", "code", "ward_count")
    list_filter = ("county__region", "county")
    search_fields = ("name", "county__name", "county__code")
    autocomplete_fields = ("county",)
    inlines = (WardInline,)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Wards")
    def ward_count(self, obj):
        return obj.wards.count()


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("name", "sub_county", "county_display", "code")
    list_filter = ("sub_county__county__region", "sub_county__county")
    search_fields = ("name", "code", "sub_county__name", "sub_county__county__name")
    autocomplete_fields = ("sub_county",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="County")
    def county_display(self, obj):
        return obj.sub_county.county.name