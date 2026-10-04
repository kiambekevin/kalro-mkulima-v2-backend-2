# apps/counties/constants.py

# County codes are ISO-like strings "001" – "047" per the
# Government of Kenya's official numbering.
COUNTY_CODE_LENGTH = 3

# The eight official regions
REGIONS = [
    "Coast",
    "North Eastern",
    "Eastern",
    "Central",
    "Rift Valley",
    "Western",
    "Nyanza",
    "Nairobi",
]

# Cache TTLs
COUNTY_LIST_CACHE_TTL = 60 * 60 * 24     # 24 hours — reference data
SUB_COUNTY_CACHE_TTL = 60 * 60 * 12      # 12 hours
WARD_CACHE_TTL = 60 * 60 * 6             # 6 hours