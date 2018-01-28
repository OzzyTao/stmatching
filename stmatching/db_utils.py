import psycopg2

class OSMDB(object):
	"""docstring for OSMDB"""
	def __init__(self, table_ways, connection):
		super(OSMDB, self).__init__()
		self.table_ways = table_ways
		self.connection = connection

	def getCandidates(self, point_coords, radius, edge_num):
		sql_str = '''select gid, 
		st_distance(st_setsrid(st_makepoint({lng},{lat}),4326)::geography,the_geom::geography) as distance,
		st_linelocatepoint(the_geom, st_setsrid(st_makepoint({lng},{lat}),4326)) as fraction,
		length_m,
		source,
		target
		from {table} where st_setsrid(st_makepoint({lng},{lat}),4326)::geography<->the_geom::geography<{radius} order by distance limit {edge_num}'''
		with self.connection.cursor() as cur:
			cur.execute(sql_str.format(table=self.table_ways,lng=point_coords[0],lat=point_coords[1],radius=radius,edge_num=edge_num))
			result = cur.fetchall()
		candidates = []
		for row in result:
			candidates.append({'edge_id':row[0],'distance':row[1],'fraction':row[2],'length_m':row[3],'source':row[4],'target':row[5]})
		return candidates

	def euclideanDistance(self, coords1, coords2):
		sql_str = '''select st_distance(st_setsrid(st_makepoint({lng1},{lat1}),4326)::geography, st_setsrid(st_makepoint({lng2},{lat2}),4326)::geography);'''
		with self.connection.cursor() as cur:
			cur.execute(sql_str.format(lng1=coords1[0],lat1=coords1[1],lng2=coords2[0],lat2=coords2[1]))
			result = cur.fetchone()
		return result[0]

	def snapPoint(self, point_coords, edge_id):
		sql_str = '''select st_linelocatepoint(the_geom, st_setsrid(st_makepoint({lng},{lat}),4326)) as fraction, 
		st_astext(st_closestpoint(the_geom,st_setsrid(st_makepoint({lng},{lat}),4326))) as point_text,
		length_m,
		source,
		target 
		from {table} where gid={edge_id}'''
		with self.connection.cursor() as cur:
			cur.execute(sql_str.format(table=self.table_ways,lng=point_coords[0],lat=point_coords[1],edge_id=edge_id))
			result = cur.fetchone()
		return {'fraction':result[0],'geom_wkt':result[1],'edge_id':edge_id,'length_m':result[2],'source':result[3],'target':result[4]}

	def shortestPath(self, p1, p2, directed = False):
		### direction being True means moving direction is the same as the geometry direction of the edge

		# if directed:
		# 	if p1['edge_id'] == p2['edge_id']:
		# 		if p1['direction']:
		# 			p2['fraction'] = p2['fraction'] if p2['fraction']>p1['fraction'] else p1['fraction']
		# 			return {'path':[(p1['source'],p1['edge_id'],p1['length_m']),
		# 							(p1['target'],-1,0)],
		# 					'length':p1['length_m']*(p2['fraction']-p1['fraction'])}
		# 		else:
		# 			p2['fraction'] = p2['fraction'] if p2['fraction']<p1['fraction'] else p1['fraction']
		# 			return {'path':[(p1['target'],p1['edge_id'],p1['length_m']),
		# 							(p1['source'],-1,0)],
		# 					'length':p1['length_m']*(p1['fraction']-p2['fraction'])}
		# 	else:
		# 		if p1['direction']:
		# 			source = p1['target']
		# 			source_edge_length = (1-p1['fraction'])*p1['length_m']
		# 		else:
		# 			source = p1['source']
		# 			source_edge_length = p1['fraction']*p1['length_m']
		# 		targets = [p2['source'],p2['target']]
		# 		candidate_paths = []
		# 		for target in targets:
		# 			if target == source:
		# 				target_edge_length = p2['fraction']*p2['length_m'] if target==p2['source'] else (1-p2['fraction'])*p2['length_m']
		# 				p2['direction'] = True if p2['source'] == target else False
		# 				return {'path':[(p1['source'] if p1['source']!=source else p1['target'],p1['edge_id'],p1['length_m']),
		# 								(source, p2['edge_id'],p2['length_m']),
		# 								(p2['source'] if p2['source']!=source else p2['target'], -1, 0)],
		# 						'length':source_edge_length+target_edge_length}
		# 		for target in targets:
		# 			path, total_length = self.shortestPath_vertexes(source,target)
		# 			target_edge_length = p2['fraction']*p2['length_m'] if target==p2['source'] else (1-p2['fraction'])*p2['length_m']
		# 			if path[0][1]!=p1['edge_id'] and path[-2][1]!=p2['edge_id']:
		# 				path = [(p1['source'] if p1['source']!=source else p1['target'],p1['edge_id'],p1['length_m'])] + path
		# 				path[-1] = (target,p2['edge_id'],p2['length_m'])
		# 				path += [(p2['source'] if p2['source']!=target else p2['target'],-1,0)]
		# 				candidate_paths.append({'path':path,'length':total_length+source_edge_length+target_edge_length})
		# 		return min(candidate_paths,key=lambda x: x['length'])


		if p1['edge_id'] == p2['edge_id']:
			if p1['fraction'] > p2['fraction']:
				return {'path':[(p1['target'],p1['edge_id'],p1['length_m']),
								(p1['source'],-1,0)], 
						'length':p1['length_m']*(p1['fraction']-p2['fraction'])}
			else:
				return {'path':[(p1['source'],p1['edge_id'],p1['length_m']),
								(p1['target'],-1,0)], 
						'length':p1['length_m']*(p2['fraction']-p1['fraction'])}
		else:
			source_nodes = [{'node':p1['source'],'cost':p1['length_m']*p1['fraction']},
							{'node':p1['target'],'cost':p1['length_m']*(1-p1['fraction'])}]
			destination_nodes = [{'node':p2['source'],'cost':p2['length_m']*p2['fraction']},
							{'node':p2['target'],'cost':p2['length_m']*(1-p2['fraction'])}]
			for s in source_nodes:
				for d in destination_nodes:
					if s['node'] == d['node']:
						return {'path':[(p1['source'] if p1['source']!=s['node'] else p1['target'], p1['edge_id'], p1['length_m']),
										(s['node'], p2['edge_id'],p2['length_m']),
										(p2['source'] if p2['source']!=s['node'] else p2['target'],-1,0)],
								'length':s['cost']+d['cost']}
			candidate_paths = []
			for s in source_nodes:
				for d in destination_nodes:
					path, total_length = self.shortestPath_vertexes(s['node'],d['node'])
					if path[0][1]!=p1['edge_id'] and path[-2][1]!=p2['edge_id']:
						path =[(p1['source'] if p1['source']!=s['node'] else p1['target'],p1['edge_id'],p1['length_m'])] + path
						path[-1] = (d['node'],p2['edge_id'],p2['length_m'])
						path += [(p2['source'] if p2['source']!=d['node'] else p2['target'],-1,0)]
						candidate_paths.append({'path':path,'length':total_length+s['cost']+d['cost']})
			return min(candidate_paths,key=lambda x: x['length'])


	def shortestPath_vertexes(self,source_vertex,target_vertex):
		sql_str = '''select node, edge, cost from pgr_dijkstra(
		'select gid as id, 
		source, 
		target, 
		length_m as cost
		from {table}',
		{source},{target},directed:=false)'''
		with self.connection.cursor() as cur:
			cur.execute(sql_str.format(table=self.table_ways,source=source_vertex,target=target_vertex))
			result = cur.fetchall()
		lengths = [x[-1] for x in result]
		total_length = sum(lengths)
		return result, total_length

	def point_inference(self,fraction,edge_id):
		sql_str = '''select st_astext(st_lineinterpolatepoint(the_geom,{fraction})) from {table} where gid={edge_id}'''
		with self.connection.cursor() as cur:
			cur.execute(sql_str.format(fraction=fraction,table=self.table_ways,edge_id=edge_id))
			result=cur.fetchone()
		return result[0]

	def get_edge(self,edge_id):
		sql_str = '''select source, target, length_m, maxspeed_forward, maxspeed_backward from {table} where gid={edge_id}'''
		with self.connection.cursor() as cur:
			cur.execute(sql_str.format(table=self.table_ways,edge_id=edge_id))
			result = cur.fetchone()
		return {'source':result[0],'target':result[1],'length_m':result[2],'maxspeed_forward':result[3],'maxspeed_backward':result[4]}

