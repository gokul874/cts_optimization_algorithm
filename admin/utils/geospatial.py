def calculate_distance(coord1, coord2):
    # Calculate the distance between two geographical coordinates
    from geopy.distance import geodesic

    return geodesic(coord1, coord2).kilometers

def get_coordinates(address):
    # Convert an address to geographical coordinates
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.geocode(address)
    return (location.latitude, location.longitude) if location else None

def is_within_radius(coord1, coord2, radius):
    # Check if the distance between two coordinates is within a specified radius
    distance = calculate_distance(coord1, coord2)
    return distance <= radius