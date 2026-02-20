import math
# WRONG
def euclidean_distance_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float, R_km: float = 6371.0) -> float:

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    lam1 = math.radians(lon1)
    lam2 = math.radians(lon2)

    dphi = phi2 - phi1
    dlam = lam2 - lam1
    phi_m = 0.5 * (phi1 + phi2)

    term1 = 2.0 * math.sin(dphi / 2.0) * math.cos(dlam / 2.0)
    term2 = 2.0 * math.cos(phi_m) * math.sin(dlam / 2.0)
    return R_km * (math.sqrt((term1 * term1) + (term2 * term2)))
