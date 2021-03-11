import random
import math
import os
import subprocess
import time
import shutil
import itertools
import multiprocessing
import copy
import distutils.dir_util
import configparser


class MugenEvolve:
	def __init__(self, population_size, no_of_generations, elitism_percentage, mutation_percentage):
		self.no_of_generations = no_of_generations
		self.population_size = population_size
		self.elitism_percentage = elitism_percentage
		self.mutation_percentage = mutation_percentage
		self.generations = []
		self.evolution_time = None
		self.path = "Vault_" + time.strftime("%Y%m%d_%H%M%S")

	def run(self):
		self.create_vault()
		self.start_evolution_timer()
		for i in range(self.no_of_generations):
			self.create_generation(id=i+1)
		self.stop_evolution_timer()
		self.create_log()

	def create_vault(self):
		os.mkdir(self.path)
		#shutil.make_archive(os.path.abspath(self.path), 'zip', root_dir=os.path.abspath(''), base_dir=self.path)

	def start_evolution_timer(self):
		self.evolution_time = time.time()

	def stop_evolution_timer(self):
		self.evolution_time = (time.time() - self.evolution_time)/60

	def create_generation(self, id):
		if id==1:
			self.generations.append(Generation(id=id, target=self.path, population_size=self.population_size))

		else:
			self.generations.append(Generation(id=id, target=self.path, population_size=self.population_size, parent_generation=self.generations[-1], elitism_percentage=self.elitism_percentage, mutation_percentage=self.mutation_percentage))

	def create_log(self):
		fout = open(os.path.join(self.path, 'log.txt'), 'w')
		fout.write("PopulationSize = ")
		fout.write(str(self.population_size)+'\n')
		fout.write("NoOfGenerations = ")
		fout.write(str(self.no_of_generations)+'\n')
		fout.write("ElitismPercentage = ")
		fout.write(str(self.elitism_percentage)+'\n')
		fout.write("MutationPercentage = ")
		fout.write(str(self.mutation_percentage)+'\n')
		fout.write("EvolutionTime = ")
		fout.write(str(self.evolution_time)+'\n')
		fout.close()


class Generation:
	def __init__(self, id, target, population_size, parent_generation=None, elitism_percentage=None, mutation_percentage=None):
		self.id = id
		self.name =  "Gen_" + str(self.id)
		self.path = os.path.join(target, self.name)
		self.population_size = population_size
		self.parent_generation = parent_generation
		self.characters = []
		self.mugen = Mugen()
		self.match_results_path = os.path.join(self.path, 'match_results')
		self.mutant_ids = []
		self.create_vault()
		if self.parent_generation is None:
			self.no_of_elites = None
			self.no_of_mutants = None
			self.populate_random()
		else:
			self.no_of_elites = int((elitism_percentage/100) * self.population_size)
			self.no_of_mutants = int((mutation_percentage/100) * self.population_size)
			self.evolve()
		self.rate_characters()
		self.create_ratings_file()

	def create_vault(self):
		os.mkdir(self.path)

	def populate_random(self):
		for i in range(self.population_size):
			self.characters.append(Character(id=i+1, target=self.path, generation_id=self.id, random=True))

	def evolve(self):
		self.add_elites()
		self.decide_mutant_ids()
		self.add_crossovers()

	def add_elites(self):
		for i in range(self.no_of_elites):
			character = Character(id=i+1, target=self.path, generation_id=self.id, move_sequence=self.parent_generation.characters[i].get_move_sequence(), move_triggers=self.parent_generation.characters[i].get_move_triggers())
			self.characters.append(character)

	def decide_mutant_ids(self):
		self.mutant_ids = random.sample(range(self.no_of_elites+1, self.population_size+1), self.no_of_mutants)
	
	def add_crossovers(self):
		parent1_position_max = math.ceil((self.population_size - self.no_of_elites)/2)
		for i in range(parent1_position_max):
			self.characters.extend(self.get_children(self.parent_generation.characters[i], self.parent_generation.characters[i+1]))

	def get_children(self, p1, p2):
		child1_id = len(self.characters)+1
		child2_id = child1_id + 1
		child1_move_sequence = p1.get_move_sequence()
		child2_move_sequence = p2.get_move_sequence()
		parent_move_triggers = [p1.get_move_triggers(), p2.get_move_triggers()]
		child_move_triggers = [[], []]
		for i in range(len(parent_move_triggers[0])):
			x = random.randint(0,1)
			child_move_triggers[0].append(copy.copy(parent_move_triggers[x][i]))
			child_move_triggers[1].append(copy.copy(parent_move_triggers[(x+1)%2][i]))
		if child1_id in self.mutant_ids:
			random.shuffle(child1_move_sequence)
		child1 = Character(id=child1_id, target=self.path, generation_id=self.id, move_sequence=child1_move_sequence, move_triggers=child_move_triggers[0], parent1_id=p1.get_id(), parent2_id=p2.get_id(), sibling_id=child2_id)
		if child2_id <= self.population_size:
			if child2_id in self.mutant_ids:
				random.shuffle(child2_move_sequence)
			child2 = Character(id=child2_id, target=self.path, generation_id=self.id, move_sequence=child2_move_sequence, move_triggers=child_move_triggers[1], parent1_id=p1.get_id(), parent2_id=p2.get_id(), sibling_id=child1_id)
			return [child1, child2]
		else:
			return [child1]

	def rate_characters(self):
		self.write_characters_to_mugen()
		os.mkdir(self.match_results_path)
		match_pool = self.create_match_pool()
		self.mugen.run_parallel_matches(match_pool=match_pool, match_results_path=self.match_results_path)
		match_results = self.mugen.load_match_results_as_list(self.match_results_path)
		random.shuffle(match_results)
		for p1_name, p2_name, winning_team in match_results:
			p1_id = int(p1_name.split('_')[2])
			p2_id = int(p2_name.split('_')[2])
			if winning_team==1:
				winner_id = p1_id
			else:
				winner_id = p2_id
			self.update_ratings(p1_id, p2_id, winner_id)
		self.sort_characters_by_rating()
		self.mugen.character_vault_reset()

	def write_characters_to_mugen(self):
		mugen_character_vault_path_abs = self.mugen.get_character_vault_path_abs()
		distutils.dir_util.copy_tree(src=self.path, dst=mugen_character_vault_path_abs)

	def create_match_pool(self):
		char_names = [char.get_name() for char in self.characters]
		match_pool = itertools.combinations(char_names, 2)
		return match_pool

	def update_ratings(self, id1, id2, winner_id):
		r1 = self.characters[id1-1].get_rating()
		r2 = self.characters[id2-1].get_rating()
		e1 = 1/(1 + math.pow(10, (r2-r1)/400))
		e2 = 1/(1 + math.pow(10, (r1-r2)/400))
		r1 = r1 + 50*(int(id1==winner_id) - e1)
		r2 = r2 + 50*(int(id2==winner_id) - e2)
		self.characters[id1-1].set_rating(r1)
		self.characters[id2-1].set_rating(r2)

	def sort_characters_by_rating(self):
		self.characters.sort(key=lambda c:c.get_rating(), reverse=True)

	def create_ratings_file(self):
		fout = open(os.path.join(self.path, 'ratings.txt'), 'w')
		for character in self.characters:
			fout.write(str(character.get_id()) + ' : ' + str(character.get_rating()) + '\n')
		fout.close()


class Mugen:
	def __init__(self):
		self.path_abs = self.resolve_abs_path_of_mugen_folder()
		self.character_vault_reset()

	def resolve_abs_path_of_mugen_folder(self):
		cwd = os.path.dirname(__file__)
		parent_of_cwd = os.path.dirname(cwd)
		mugen_folder_path =  os.path.join(parent_of_cwd, 'mugen')
		return mugen_folder_path

	def character_vault_reset(self):
		character_vault_path_abs = self.get_character_vault_path_abs()
		for folder_name in os.listdir(character_vault_path_abs):
			distutils.dir_util.remove_tree(os.path.join(character_vault_path_abs, folder_name))

	def get_character_vault_path_abs(self):
		return os.path.join(self.path_abs, 'chars')

	def run_match(self, p1_name, p2_name, result_path):
		exe_path_abs = os.path.join(self.path_abs, 'mugen')
		result_path_abs = os.path.abspath(result_path)
		command = [exe_path_abs, p1_name, p2_name, '-log', result_path_abs, '-rounds', '1'] 
		subprocess.call(command, cwd=self.path_abs)

	def run_parallel_matches(self, match_pool, match_results_path):
		workers_arg_pool = []
		for p1_name, p2_name in match_pool:
			result_path = os.path.join(match_results_path, p1_name + '-' + p2_name + '.txt')
			arg = (p1_name, p2_name, result_path)
			workers_arg_pool.append(arg)
		pool = multiprocessing.Pool()
		pool.starmap(self.run_match, workers_arg_pool)
		pool.close()
		pool.join()

	def load_match_results_as_list(self, match_results_path):
		match_results = []
		for file_name in os.listdir(match_results_path):
			p1_name = file_name.strip('.txt').split('-')[0]
			p2_name = file_name.strip('.txt').split('-')[1]
			winning_team = self.get_winning_team(os.path.join(match_results_path, file_name))
			match_results.append((p1_name, p2_name, winning_team))
		return match_results

	def get_winning_team(self, result_path):
		fin = open(result_path)
		for line in fin:
			if line.startswith('winningteam'):
				return int(line.strip().split()[2])


class Character:
	def __init__(self, id, target, generation_id, move_sequence=None, move_triggers=None, sibling_id=None, parent1_id=None, parent2_id=None, random=False):
		self.id = id
		self.generation_id = generation_id
		self.name = 'chan_' + str(self.generation_id) + '_' + str(self.id)
		self.path = os.path.join(target, self.name)
		self.move_sequence = move_sequence
		self.move_triggers = move_triggers
		self.sibling_id = sibling_id
		self.parent1_id = parent1_id
		self.parent2_id = parent2_id
		self.random = random
		self.rating = 1000
		self.character_template_path = 'CharacterTemplate'
		self.trigger_domain_path = 'trigger_domain.txt'
		self.move_domain_path = 'move_domain.txt'
		if self.random:
			self.create_random_ai()
		self.create_vault()

	def create_random_ai(self):
		self.create_random_move_sequence()
		self.create_random_move_triggers()

	def create_random_move_sequence(self):
		self.move_sequence = list(range(1,37))
		random.shuffle(self.move_sequence)

	def create_random_move_triggers(self):
		self.move_triggers = []
		for i in range(len(self.move_sequence)):
			self.move_triggers.append(self.get_random_trigger_list())

	def get_random_trigger_list(self):
		trigger_domain = self.load_trigger_domain_as_list()
		no_of_triggers = random.randint(1,4)
		random_trigger_indices = random.sample(range(len(trigger_domain)), no_of_triggers)
		trigger_list = ["triggerall = Random < 50\n"]
		for i in random_trigger_indices:
			trigger_name = trigger_domain[i][0]
			trigger_argument = random.choice(trigger_domain[i][1:])
			trigger = "triggerall = " + trigger_name + trigger_argument + '\n'
			trigger_list.append(trigger)
		return trigger_list

	def load_trigger_domain_as_list(self):
		fin = open(self.trigger_domain_path)
		trigger_domain = []
		for line in fin:
			line = line.strip().split(',')
			trigger_domain.append(line)
		fin.close()
		return trigger_domain

	def create_vault(self):
		os.mkdir(self.path)
		self.copy_template()
		self.rename_files()
		self.modify_def()
		self.append_to_cmd()
		self.save_family_details()

	def copy_template(self):
		distutils.dir_util.copy_tree(src=self.character_template_path, dst=self.path)

	def rename_files(self):
		os.rename(os.path.join(self.path, 'cmd.cmd'), os.path.join(self.path, self.name+'.cmd'))
		os.rename(os.path.join(self.path, 'def.def'), os.path.join(self.path, self.name+'.def'))

	def modify_def(self):
		src_path = os.path.join(self.path, self.name+'.def')
		dest_path = os.path.join(self.path, 'deftemp.def')
		fin = open(src_path)
		fout = open(dest_path, 'w')
		quoted_name = "\"" + self.name + "\""
		for line in fin:
			if line.startswith("name"):
				line="name =  " + quoted_name + "\n"
			elif line.startswith("displayname"):
				line="displayname =  " + quoted_name + "\n"
			elif line.startswith("cmd"):
				line="cmd =  " + self.name + ".cmd" + "\n"
			fout.write(line)
		fin.close()
		fout.close()
		os.remove(src_path)
		os.rename(dest_path, src_path)

	def append_to_cmd(self):
		move_domain =  self.load_move_domain_as_list()
		fa =  open(os.path.join(self.path, self.name+'.cmd'), 'a')
		for move_id in self.move_sequence:
			fa.write('\n;' + str(move_id) + '\n')
			for line in move_domain[move_id-1]:
				fa.write(line)
			for line in self.move_triggers[move_id-1]:
				fa.write(line)
		fa.close()

	def load_move_domain_as_list(self):
		fin = open(self.move_domain_path)
		move_domain = []
		for line in fin:
			if line.startswith(';'):
				move_template = []
				for line in fin:
					if not line.strip():
						break
					move_template.append(line)
				move_domain.append(move_template)
		fin.close()
		return move_domain

	def save_family_details(self):
		fout = open(os.path.join(self.path, 'family.txt'), 'w')
		fout.write('Parent1-id : '+ str(self.parent1_id) + '\n')
		fout.write('Parent2-id : '+ str(self.parent2_id) + '\n')
		fout.write('Sibling-id : '+ str(self.sibling_id) + '\n')
		fout.close()

	def get_id(self):
		return self.id

	def get_name(self):
		return self.name

	def get_rating(self):
		return self.rating

	def get_move_sequence(self):
		return copy.copy(self.move_sequence)

	def get_move_triggers(self):
		return copy.deepcopy(self.move_triggers)

	def set_rating(self, rating):
		self.rating = rating


def main():
	config = configparser.ConfigParser()
	config.read('config.txt')
	for section in config.sections():
		mugen_evolve = MugenEvolve(population_size=int(config[section]['PopulationSize']),
									no_of_generations=int(config[section]['NoOfGenerations']),
									elitism_percentage=int(config[section]['ElitismPercentage']),
									mutation_percentage=int(config[section]['MutationPercentage']))
		mugen_evolve.run()


if __name__ == '__main__':
	main()