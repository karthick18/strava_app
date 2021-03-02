import math
import sys
import geopy
import geopy.distance

# north is 0 degrees, east: 90, south: 180, west: 270
bearing_map = {'north_east': 45, 'south_west': 235}

bearing_radians_map = {'north_east': 0.785, 'south_west': 4.101}

def get_latlng(lat, lng, d, bearing='south_west'):
    if bearing not in bearing_map:
        raise ValueError('Invalid bearing arg {}'.format(bearing))
    degrees = bearing_map[bearing]
    origin = geopy.Point(lat, lng)
    dest = geopy.distance.distance(kilometers=d).destination(origin, degrees)
    return round(dest.latitude, 2), round(dest.longitude, 2)

# check if latitude/longitude A lies between B and C
def lies_between(A,B,C):
    def distance(A,B):
        return math.sqrt((A[0] - B[0])**2 + (A[1] - B[1])**2)
    a = distance(B,C)
    b = distance(C,A)
    c = distance(A,B)
    return a**2 + b**2 >= c**2 and a**2 + c**2 >= b**2

def __get_latlng(lat, lng, d, bearing='south_west'):
    R = 6378.1 #Radius of the Earth
    if bearing not in bearing_radians_map:
        raise ValueError('Invalid bearing arg {}'.format(bearing))
    brng = bearing_radians_map[bearing]
    lat1 = math.radians(lat) #Current lat point converted to radians
    lon1 = math.radians(lng) #Current long point converted to radians
    lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
                      math.cos(lat1)*math.sin(d/R)*math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
                             math.cos(d/R)-math.sin(lat1)*math.sin(lat2))
    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)
    return round(lat2, 2), round(lon2, 2)

if __name__ == '__main__':
    distance = 11
    if len(sys.argv) > 1:
        distance = int(sys.argv[1])
    lat, lng = 52.20472, 0.14056 #37.512844, -121.881369
    lat2, lng2 = get_latlng(lat, lng, 11)
    print(lat2, lng2, 'for', lat, lng, 'distance', distance)
