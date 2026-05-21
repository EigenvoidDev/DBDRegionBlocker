# ===========
# Region Data
# ===========

REGION_NAMES = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ca-central-1": "Canada (Central)",
    "eu-west-1": "Europe (Ireland)",
    "eu-west-2": "Europe (London)",
    "eu-central-1": "Europe (Frankfurt)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "sa-east-1": "South America (São Paulo)",
}

REGION_OVERRIDES = {"ap-east-1": {"service_endpoint": "ec2.ap-east-1.amazonaws.com"}}

# ===========
# Builders
# ===========


def build_regions():
    regions = {}

    for region_code, region_name in REGION_NAMES.items():
        region_data = {
            "code": region_code,
            "name": region_name,
            "service_endpoint": f"gamelift.{region_code}.amazonaws.com",
            "udp_ping_beacon_endpoint": f"gamelift-ping.{region_code}.api.aws",
        }

        region_data.update(REGION_OVERRIDES.get(region_code, {}))

        regions[region_code] = region_data

    return regions


REGIONS = build_regions()

# ===========
# Helpers
# ===========


def get_all_regions():
    return list(REGIONS.values())


# ===========
# Constants
# ===========

LATENCY_THRESHOLDS = {
    "good": 100,
    "ok": 200,
}