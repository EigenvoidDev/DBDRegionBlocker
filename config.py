REGION_INFO = {
    "US East (N. Virginia)": "us-east-1",
    "US East (Ohio)": "us-east-2",
    "US West (N. California)": "us-west-1",
    "US West (Oregon)": "us-west-2",
    "Canada (Central)": "ca-central-1",
    "Europe (Ireland)": "eu-west-1",
    "Europe (London)": "eu-west-2",
    "Europe (Frankfurt)": "eu-central-1",
    "Asia Pacific (Mumbai)": "ap-south-1",
    "Asia Pacific (Hong Kong)": "ap-east-1",
    "Asia Pacific (Tokyo)": "ap-northeast-1",
    "Asia Pacific (Seoul)": "ap-northeast-2",
    "Asia Pacific (Singapore)": "ap-southeast-1",
    "Asia Pacific (Sydney)": "ap-southeast-2",
    "South America (São Paulo)": "sa-east-1",
}

# Special-case overrides for regions with nonstandard endpoints
REGION_OVERRIDES = {
    "Asia Pacific (Hong Kong)": {"service_endpoint": "ec2.ap-east-1.amazonaws.com"}
}

REGIONS = {
    name: {
        "region": code,
        "service_endpoint": f"gamelift.{code}.amazonaws.com",
        "udp_ping_beacon_endpoint": f"gamelift-ping.{code}.api.aws",
        **REGION_OVERRIDES.get(name, {}),
    }
    for name, code in REGION_INFO.items()
}

LATENCY_THRESHOLDS = {"good": 100, "ok": 200}