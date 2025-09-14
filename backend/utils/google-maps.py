import os
import googlemaps
from dotenv import load_dotenv

load_dotenv()

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

def calculate_distance(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Calculates distance (in km) and duration (in minutes) using Google Maps Distance Matrix API.
    """
    origins = (origin_lat, origin_lng)
    destinations = (dest_lat, dest_lng)

    result = gmaps.distance_matrix(origins, destinations, mode="driving")

    if result["status"] == "OK":
        element = result["rows"][0]["elements"][0]
        if element["status"] == "OK":
            distance_km = element["distance"]["value"] / 1000  # meters → km
            duration_min = element["duration"]["value"] / 60  # seconds → minutes
            return distance_km, duration_min

    return None, None
