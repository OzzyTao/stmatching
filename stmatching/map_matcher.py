from scipy import stats

class MapMatcher:
	def __init__(self, db, point_list, search_radius=50, candidates_num=5, gps_err_sd=20, length_ratio_sd=0.5,temporal = False):
		self.db = db
		self.point_list = point_list
		self.search_radius = search_radius
		self.candidates_num = candidates_num
		self.gps_err_sd = gps_err_sd
		self.length_ratio_sd = length_ratio_sd
		self._map_matching()


	def _map_matching(self):
		valid_point_list = []
		weighting_network = []
		for point in self.point_list:
			candidates = self.db.getCandidates(point['coords'],self.search_radius, self.candidates_num)
			if candidates:
				weighting_network.append({'observation':point,'candidates':candidates})
				valid_point_list.append(point)
		number_of_points = len(weighting_network)
		for i in range(len(weighting_network)):
			candidates = weighting_network[i]['candidates']
			for candidate in candidates:
				if i!=0:
					candidate['pre_paths'] = []
					for pre_candidate in weighting_network[i-1]['candidates']:
						tmp_path = self.db.shortestPath(pre_candidate,candidate)
						candidate['pre_paths'].append(tmp_path)
		GPS_distribution = stats.norm(loc=0,scale=self.gps_err_sd)
		length_ratio_distribution = stats.norm(loc=1,scale=self.length_ratio_sd)
		for i in range(len(weighting_network)):
			for candidate in weighting_network[i]['candidates']:
				candidate['weight'] = GPS_distribution.pdf(candidate['distance'])
				if i>0:
					d = self.db.euclideanDistance(weighting_network[i]['observation']['coords'],weighting_network[i-1]['observation']['coords'])
					tmp =[]
					for pre_i in range(len(weighting_network[i-1]['candidates'])):
						pre_length = candidate['pre_paths'][pre_i]['length'] 
						length_diff_weight = length_ratio_distribution.pdf(d/pre_length if pre_length>0 else 2)
						tmp.append({'weight':candidate['weight']*length_diff_weight+weighting_network[i-1]['candidates'][pre_i]['weight'],'length':len(candidate['pre_paths'][pre_i]['path'])})
					candidate['pre'] = self._weight_paths(tmp)
					candidate['weight'] = tmp[candidate['pre']]['weight']
		self.weighting_network = weighting_network
		matched = []
		path  = []
		weights = [x['weight'] for x in weighting_network[-1]['candidates']]
		pre_index = weights.index(max(weights)) 
		for i in range(number_of_points-1,-1,-1):
			self.weighting_network[i]['chosen_index'] = pre_index
			candidate = weighting_network[i]['candidates'][pre_index]
			output_obj = {'observation':self.weighting_network[i]['observation'],
							'fraction':candidate['fraction'],
							'edge_id':candidate['edge_id'],
							'geom_wkt':self.db.point_inference(candidate['fraction'],candidate['edge_id'])}
			matched = [output_obj] + matched
			if 'pre' in candidate:
				pre_index = candidate['pre']
				path = candidate['pre_paths'][pre_index]['path'] + path
		path = self._clean_path(path)
		self.matched = matched
		self.path = path

	def _weight_paths(self, ps):
		index = -1
		max_weight = -1
		shortest_length = -1
		for i, p in enumerate(ps):
			if p['weight'] > max_weight:
				index = i
				max_weight = p['weight']
				shortest_length = p['length']
			elif p['weight'] == max_weight and p['length']<shortest_length:
				shortest_length = p['length']
				index = i 
		return index

	def _clean_path(self, p):
		pre_edge =-2
		pre_node = -1
		result = []
		for i,r in enumerate(p):
			if r[1]!=-1 and r[0]!=pre_node:
				result.append(r)
				pre_edge = r[1]
				pre_node = r[0]
			elif i==len(p)-1:
				result.append(r)
		return result

	def get_matched(self):
		return self.matched

	def get_path(self):
		return self.path

	def infer(self, time_ux):
		number_of_points = len(self.weighting_network)
		index = 0
		for i in range(number_of_points):
			if self.weighting_network[i]['observation']['timestamp'] >= time_ux:
				index = i
				break
		if index>0:
			time_delta= time_ux - self.weighting_network[index-1]['observation']['timestamp']
			candid_index = self.weighting_network[index]['chosen_index']
			current_candidate = self.weighting_network[index]['candidates'][candid_index]
			distance_diff = current_candidate['pre_paths'][current_candidate['pre']]['length']
			time_diff = self.weighting_network[index]['observation']['timestamp']-self.weighting_network[index-1]['observation']['timestamp']
			distance_delta = distance_diff / time_diff * time_delta
			path = current_candidate['pre_paths'][current_candidate['pre']]
			source_snaped = self.weighting_network[index-1]['candidates'][current_candidate['pre']]['snaped']
			target_snaped = current_candidate['snaped']
			source_segment = source_snaped['fraction']*source_snaped['length_m'] if source_snaped['target']==path[0][0] else (1-source_snaped['fraction'])*source_snaped['length_m']
			if distance_delta <= source_segment:
				fraction_diff = distance_delta/source_snaped['length_m']
				fraction = source_snaped['fraction']-fraction_diff if source_snaped['target']==path[0][0] else source_snaped['fraction']+fraction_diff
				return {'edge_id':source_snaped['edge_id'],
						'fraction':fraction,
						'geom_wkt':self.db.point_inference(fraction,source_snaped['edge_id'])}
			else:
				distance_delta = distance_delta - source_segment
				for seg in path[1:-2]:
					if distance_delta <= seg[2]:
						edge = self.db.get_edge(seg[1])
						fraction = distance_delta/seg[2] if seg[0]==edge['source'] else 1-distance_delta/seg[2]
						return {'edge_id':seg[1],
								'fraction':fraction,
								'geom_wkt':self.db.point_inference(fraction,seg[1])}
					else:
						distance_delta -= seg[2]
				target_segment = target_snaped['fraction']*target_snaped['length_m'] if target_snaped['source']==path[-2][0] else (1-source_snaped['fraction'])*source_snaped['length_m']
				assert distance_delta <= target_segment
				fraction = distance_delta/target_snaped['length_m'] if target_snaped['source']==path[-2][0] else 1-distance_delta/target_snaped['length_m']
				return {'edge_id':target_snaped['edge_id'],
						'fraction':fraction,
						'geom_wkt':self.db.point_inference(fraction,target_snaped['edge_id'])}


















