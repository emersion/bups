import os
import json

config_file = os.path.realpath(os.path.dirname(__file__)+"/../config/config.json")

def read():
	f = open(config_file, 'r')
	cfg = json.load(f)
	f.close()
	return cfg

def write(cfg):
	f = open(config_file, 'w')
	json.dump(cfg, f, indent=4)
	f.close()
