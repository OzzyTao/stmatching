import psycopg2
import gpxpy
from stmatching.db_utils import OSMDB
from stmatching.map_matcher import MapMatcher

db = OSMDB('ways',psycopg2.connect("dbname='melbourne_osm_test'"))
with open('./4_2_Route.gpx','r') as gpx_file:
	gpx = gpxpy.parse(gpx_file)
	for track in gpx.tracks:
		for segment in track.segments:
			pts = []
			for point in segment.points:
				pts.append({'coords':(point.longitude,point.latitude),
							'timestamp':point.time.timestamp()})
			pts = pts[:30]
			matcher = MapMatcher(db,pts,50,5,20)
			print(matcher.get_path())