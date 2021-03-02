#!/usr/bin/env python3
import time
import pickle
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from stravalib.client import Client
import pandas as pd
import latlng
import strava_secret
import sys
import argparse
import uvicorn
from argparse import ArgumentParser

app = FastAPI()
client = Client()
REDIRECT_URL = 'http://localhost:8000/authorized'

def save_object(obj, filename):
    with open(filename, 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    with open(filename, 'rb') as input:
        loaded_object = pickle.load(input)
        return loaded_object


@app.get("/")
def read_root():
    authorize_url = client.authorization_url(client_id=strava_secret.CLIENT_ID,
                                             redirect_uri=REDIRECT_URL)
    return RedirectResponse(authorize_url)



@app.get("/authorized/")
def get_code(state=None, code=None, scope=None):
    token_response = client.exchange_code_for_token(client_id=strava_secret.CLIENT_ID,
                                                    client_secret=strava_secret.CLIENT_SECRET,
                                                    code=code)
    access_token = token_response['access_token']
    refresh_token = token_response['refresh_token']
    expires_at = token_response['expires_at']
    client.access_token = access_token
    client.refresh_token = refresh_token
    client.token_expires_at = expires_at
    save_object(client, 'client.pkl')
    return {"state": state, "code": code, "scope": scope}

class StravaApp(object):
    def __init__(self):
        self.client = client

    def check_token(self):
        if time.time() > self.client.token_expires_at:
            refresh_response = self.client.refresh_access_token(client_id=strava_secret.CLIENT_ID,
                                                                client_secret=strava_secret.CLIENT_SECRET,
                                                                refresh_token=self.client.refresh_token)
            access_token = refresh_response['access_token']
            refresh_token = refresh_response['refresh_token']
            expires_at = refresh_response['expires_at']
            self.client.access_token = access_token
            self.client.refresh_token = refresh_token
            self.client.token_expires_at = expires_at
        
    def explore_segments(self, bounds, activity_type='running', within_km=0.1, bearing='south_west'):
        if len(bounds) != 4:
            raise ValueError("Bounds should be a list of size 4. Specified {}".format(bounds))
        #print(*bounds)
        ne_lat_lng = bounds[2], bounds[3]
        lat_lng_limit = latlng.get_latlng(*ne_lat_lng, within_km, bearing=bearing)
        #if lat_lng_limit[0] > ne_lat_lng[0] and lat_lng_limit[1] > ne_lat_lng[1]:
        #    ne_lat_lng, lat_lng_limit = lat_lng_limit, ne_lat_lng

        #print('limits', lat_lng_limit)
        # we explore all segments and filter out those whose north east corner is within the limit/range
        segments = self.client.explore_segments(bounds, activity_type=activity_type)
        shortlisted_segments = []
        for seg in segments:
            #print(seg.name, str(seg.id), seg.start_latlng, seg.end_latlng)
            segment = self.get_segment(seg.id)
            end_latlng = segment.end_latlng
            start_latlng = segment.start_latlng
            if latlng.lies_between(end_latlng, lat_lng_limit, ne_lat_lng):
                print('Adding segment {}/{}'.format(segment.id, segment.name))
                shortlisted_segments.append(segment)
            else:
                print('Skipping segment', segment.name, segment.id, segment.end_latlng)
        return shortlisted_segments

    def get_segment(self, segment_id):
        segment = self.client.get_segment(segment_id)
        #print(segment.name, segment.start_latlng, segment.end_latlng, segment.athlete_segment_stats.effort_count)
        return segment#.start_latlng, segment.end_latlng

    def get_activities(self, limit=1000):
        my_cols = ['average_speed', 'total_elevation_gain', 'distance', 'type']
        activities = self.client.get_activities(limit=limit)
        data = []
        for act in activities:
            d = act.to_dict()
            data.append([d.get(col) for col in my_cols])
        df = pd.DataFrame(data, columns=my_cols)
        return df

    def get_athlete(self):
        return self.client.get_athlete()

def main(args):
    segment_coords = args.segment_coordinates
    distance = args.distance
    distance_start = args.distance_start
    if distance > 20:
        print('Setting distance to 20 as range is too high for segment exploration')
        distance = 20
    if distance_start > distance:
        distance_start = 0
    within = args.within
    if within > 0.5:
        print('Setting range for segment to within 0.5 kms as range is too high from segment end')
        within = 0.5
    strava_app = StravaApp()
    try:
        strava_app.client = load_object('client.pkl')
        strava_app.check_token()
        lat_lng = segment_coords #strava_app.get_segment(3991086)
        if args.segment_id.strip() != '':
            segment = strava_app.get_segment(args.segment_id)
            print(segment.name, segment.start_latlng, segment.end_latlng)
            sys.exit(0)

        print(segment_coords, distance, within)
        # get the latitude and longitude for the acceptable segment north-east within limit of above segment
        # get second coords within "distance" kms of the north-east corner of the segment
        matched_segments = []
        for d in range(distance_start, distance, 2):
            lat2, lon2 = latlng.get_latlng(*lat_lng, d, bearing='south_west')
            print('Exploring segments within distance', d, 'km of', *lat_lng)
            matched_segments += strava_app.explore_segments((lat2, lon2, *lat_lng), within_km=within)

        # get second coords within "distance" kms of the south-west corner of the segment            
        for d in range(distance_start, distance, 2):
            lat2, lon2 = latlng.get_latlng(*lat_lng, d, bearing='north_east')
            print('Exploring segments within distance', d, 'km of', *lat_lng)
            matched_segments += strava_app.explore_segments((*lat_lng, lat2, lon2), within_km=within, bearing='north_east')
        segment_list = []
        segment_seen_map = {}
        for m in matched_segments:
            if m.id in segment_seen_map:
                continue
            segment_seen_map[m.id] = True
            segment_list.append(m)
        efforts = 0
        segment_map = {}
        for s in segment_list:
            efforts += s.athlete_segment_stats.effort_count
            segment_map[s.name] = s.athlete_segment_stats.effort_count
        athlete = strava_app.get_athlete()
        print('Athlete', athlete.firstname, 'ID', athlete.id, 'Segments', len(segment_list), 'efforts', efforts)
        print(segment_list)
        for segment, efforts in segment_map.items():
            print('Segment {}, Efforts {}'.format(segment, efforts))
    except FileNotFoundError:
        print("No access token stored yet, visit http://localhost:8000/ to get it")
        print("After visiting that url, a pickle file is stored, run this file again to upload your activity")
        uvicorn.run('strava_app:app', host='localhost', port=8000, log_level='info')

if __name__ == '__main__':
    default_coordinates = [37.512844, -121.881369]
    parser = ArgumentParser(description='Strava app to explore segments',
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-segment-coordinates', '--segment-coordinates', nargs='+', type=float,
                        default=default_coordinates,
                        help='Specify coordinates segment north-east corner latitude and longitude')
    parser.add_argument('-distance', '--distance', type=int, default=10,
                        help='Specify distance in kilometers for explore for segments from the segment coordinates north-east corner from distance start')
    parser.add_argument('-distance-start', '--distance-start', type=int, default=5,
                        help='Specify distance start in kilometers for explore for segments from the segment coordinates north-east corner to specified distance')
    parser.add_argument('-within', '--within', type=float, default=1.0,
                        help='Specify the max range in kilometers to search for the end of the segment from north-east corner')
    parser.add_argument('-segment-id', '--segment-id', type=str, default='',
                        help='Segment ID to get details of end latitude and longitude to use with explore segments')
    args = parser.parse_args()
    sys.exit(main(args))
