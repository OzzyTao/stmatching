from unittest import TestCase
from stmatching.db_utils import OSMDB
import psycopg2

class DBTest(TestCase):
	def setUp(self):
		self.db = OSMDB('ways',psycopg2.connect("dbname='melbourne_osm_test'"))

	def test_get_edge(self):
		edge = self.db.get_edge(1)
		self.assertEqual(edge['source'],18098)

