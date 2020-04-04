import pandas as pd
import numpy as np
import wget
from zipfile import ZipFile 
from utils import convert_y_unit
import json

'''
Acknowledgement:
The BindingDB dataset is hosted in https://www.bindingdb.org/bind/index.jsp.

The Davis Dataset can be found in http://staff.cs.utu.fi/~aatapa/data/DrugTarget/.

The KIBA dataset can be found in https://jcheminf.biomedcentral.com/articles/10.1186/s13321-017-0209-z. 

The Drug Target Common Dataset can be found in https://drugtargetcommons.fimm.fi/.

The COVID-19 Dataset including SARS-CoV, Broad Repurposing Hub can be found in https://www.aicures.mit.edu/data; and https://pubchem.ncbi.nlm.nih.gov/bioassay/1706. 
We use some existing files from https://github.com/yangkevin2/coronavirus_data

We use the SMILES, protein sequence from DeepDTA github repo: https://github.com/hkmztrk/DeepDTA/tree/master/data.
'''

def download_BindingDB(path):

	print('Beginning to download dataset...')
	url = 'https://www.bindingdb.org/bind/downloads/BindingDB_All_2020m2.tsv.zip'
	saved_path = wget.download(url, path)

	print('Beginning to extract zip file...')
	with ZipFile(saved_path, 'r') as zip: 
	    zip.extractall(path = path) 
	    print('Done!') 
	path = path + '/BindingDB_All.tsv'
	return path 


def download_DrugTargetCommons(path):

	print('Beginning to download dataset...')
	url = 'https://drugtargetcommons.fimm.fi/static/Excell_files/DTC_data.csv'
	saved_path = wget.download(url, path)
	path = path + '/DtcDrugTargetInteractions.csv'
	return path 


def process_BindingDB(path = None, df = None, y = 'Kd', binary = False, convert_to_log = True, threshold = 30):
	if df is not None:
		print('Loading Dataset from the pandas input...')
	else:
		print('Loading Dataset from path...')
		df = pd.read_csv(path, sep = '\t', error_bad_lines=False)
	print('Beginning Processing...')
	df = df[df['Number of Protein Chains in Target (>1 implies a multichain complex)'] == 1.0]
	df = df[df['Ligand SMILES'].notnull()]

	if y == 'Kd':
		idx_str = 'Kd (nM)'
	elif y == 'IC50':
		idx_str = 'IC50 (nM)'
	elif y == 'Ki':
		idx_str = 'Ki (nM)'
	elif y == 'EC50':
		idx_str = 'EC50 (nM)'
	else:
		print('select Kd, Ki, IC50 or EC50')

	df_want = df[df[idx_str].notnull()]
	df_want = df_want[['BindingDB Reactant_set_id', 'Ligand InChI', 'Ligand SMILES', 'PubChem CID', 'UniProt (SwissProt) Primary ID of Target Chain', 'BindingDB Target Chain  Sequence', idx_str]]
	df_want.rename(columns={'BindingDB Reactant_set_id':'ID',
							'Ligand SMILES':'SMILES',
							'Ligand InChI':'InChI',
							'PubChem CID':'PubChem_ID',
							'UniProt (SwissProt) Primary ID of Target Chain':'UniProt_ID',
							'BindingDB Target Chain  Sequence': 'Target Sequence',
							idx_str: 'Label'}, 
							inplace=True)

	df_want['Label'] = df_want['Label'].str.replace('>', '')
	df_want['Label'] = df_want['Label'].str.replace('<', '')
	df_want['Label'] = df_want['Label'].astype(float)
	
	# have at least uniprot or pubchem ID
	df_want = df_want[df_want.PubChem_ID.notnull() | df_want.UniProt_ID.notnull()]
	df_want = df_want[df_want.InChI.notnull()]

	df_want = df_want[df_want.Label <= 10000000.0]
	print('There are ' + str(len(df_want)) + ' drug target pairs.')

	if binary:
		print('Default binary threshold for the binding affinity scores are 30, you can adjust it by using the "threshold" parameter')
		y = [1 if i else 0 for i in df_want.Label.values < threshold]
	else:
		if convert_to_log:
			print('Default set to logspace (nM -> p) for easier regression')
			y = convert_y_unit(df_want.Label.values, 'nM', 'p') 
		else:
			y = df_want.Label.values

	return df_want.SMILES.values, df_want['Target Sequence'].values, np.array(y)

def load_process_DAVIS(path, binary = False, convert_to_log = True, threshold = 30):
	print('Beginning Processing...')

	url = 'https://drive.google.com/uc?export=download&id=14h-0YyHN8lxuc0KV3whsaSaA-4KSmiVN'
	saved_path = wget.download(url, path)

	print('Beginning to extract zip file...')
	with ZipFile(saved_path, 'r') as zip: 
	    zip.extractall(path = path) 

	affinity = pd.read_csv(path + '/DAVIS/affinity.txt', header=None, sep = ' ')

	with open(path + '/DAVIS/target_seq.txt') as f:
		target = json.load(f)

	with open(path + '/DAVIS/SMILES.txt') as f:
		drug = json.load(f)

	target = list(target.values())
	drug = list(drug.values())

	SMILES = []
	Target_seq = []
	y = []

	for i in range(len(drug)):
		for j in range(len(target)):
			SMILES.append(drug[i])
			Target_seq.append(target[j])
			y.append(affinity.values[i, j])

	if binary:
		print('Default binary threshold for the binding affinity scores are 30, you can adjust it by using the "threshold" parameter')
		y = [1 if i else 0 for i in np.array(y) < threshold]
	else:
		if convert_to_log:
			print('Default set to logspace (nM -> p) for easier regression')
			y = convert_y_unit(np.array(y), 'nM', 'p') 
		else:
			y = y
	print('Done!')
	return np.array(SMILES), np.array(Target_seq), np.array(y)

def load_process_KIBA(path, binary = False, threshold = 9):
	print('Beginning Processing...')

	url = 'https://drive.google.com/uc?export=download&id=1fb3ZI-3_865OuRMWNMzLPnbLm9CktM44'
	saved_path = wget.download(url, path)

	print('Beginning to extract zip file...')
	with ZipFile(saved_path, 'r') as zip: 
	    zip.extractall(path = path) 

	affinity = pd.read_csv(path + '/KIBA/affinity.txt', header=None, sep = '\t')
	affinity = affinity.fillna(-1)

	with open(path + '/KIBA/target_seq.txt') as f:
		target = json.load(f)

	with open(path + '/KIBA/SMILES.txt') as f:
		drug = json.load(f)

	target = list(target.values())
	drug = list(drug.values())

	SMILES = []
	Target_seq = []
	y = []

	for i in range(len(drug)):
		for j in range(len(target)):
			if affinity.values[i, j] != -1:
				SMILES.append(drug[i])
				Target_seq.append(target[j])
				y.append(affinity.values[i, j])

	if binary:
		print('Note that KIBA is not suitable for binary classification as it is a modified score. Default binary threshold for the binding affinity scores are 9, you should adjust it by using the "threshold" parameter')
		y = [1 if i else 0 for i in np.array(y) < threshold]
	else:
		y = y

	print('Done!')
	return np.array(SMILES), np.array(Target_seq), np.array(y)

def load_AID1706_SARS_CoV_3CL(path, binary = False, threshold = 15):
	print('Beginning Processing...')
	target = 'SGFKKLVSPSSAVEKCIVSVSYRGNNLNGLWLGDSIYCPRHVLGKFSGDQWGDVLNLANNHEFEVVTQNGVTLNVVSRRLKGAVLILQTAVANAETPKYKFVKANCGDSFTIACSYGGTVIGLYPVTMRSNGTIRASFLAGACGSVGFNIEKGVVNFFYMHHLELPNALHTGTDLMGEFYGGYVDEEVAQRVPPDNLVTNNIVAWLYAAIISVKESSFSQPKWLESTTVSIEDYNRWASDNGFTPFSTSTAITKLSAITGVDVCKLLRTIMVKSAQWGSDPILGQYNFEDELTPESVFNQVGGVRLQ'
	url = 'https://pubchem.ncbi.nlm.nih.gov/assay/pcget.cgi?query=download&record_type=datatable&actvty=all&response_type=save&aid=1706'
	saved_path_data = wget.download(url, path)

	url = 'https://drive.google.com/uc?export=download&id=1eipPaFrg-mVULoBhyp2kvEemi2WhDxsM'
	saved_path_conversion = wget.download(url, path)

	df_data = pd.read_csv(saved_path_data)
	df_conversion = pd.read_csv(saved_path_conversion)
	val = df_data.iloc[4:][['PUBCHEM_CID','PUBCHEM_ACTIVITY_SCORE']]

	cid2smiles = dict(zip(df_conversion[['cid','smiles']].values[:, 0], df_conversion[['cid','smiles']].values[:, 1]))
	X_drug = [cid2smiles[i] for i in val.PUBCHEM_CID.values]    
	y = val.PUBCHEM_ACTIVITY_SCORE.values

	if binary:
		print('Default binary threshold for the binding affinity scores is 15, recommended by the investigator')
		y = [1 if i else 0 for i in np.array(y) >= threshold]
	else:
		y = y
	print('Done!')
	return np.array(X_drug), target, np.array(y)

def load_broad_repurposing_hub(path):
	url = 'https://drive.google.com/uc?export=download&id=1A4HbHMZvhgDjx5ZjS-uVrCGBaVmvU8wd'
	saved_path_data = wget.download(url, path)
	df = pd.read_csv(saved_path_data)
	df = df.fillna('UNK')
	return df.smiles.values, df.title.values, df.cid.values.astype(str)

def load_SARS_CoV_Protease_3CL():
	target = 'SGFKKLVSPSSAVEKCIVSVSYRGNNLNGLWLGDSIYCPRHVLGKFSGDQWGDVLNLANNHEFEVVTQNGVTLNVVSRRLKGAVLILQTAVANAETPKYKFVKANCGDSFTIACSYGGTVIGLYPVTMRSNGTIRASFLAGACGSVGFNIEKGVVNFFYMHHLELPNALHTGTDLMGEFYGGYVDEEVAQRVPPDNLVTNNIVAWLYAAIISVKESSFSQPKWLESTTVSIEDYNRWASDNGFTPFSTSTAITKLSAITGVDVCKLLRTIMVKSAQWGSDPILGQYNFEDELTPESVFNQVGGVRLQ'
	target_name = 'SARS-CoV 3CL Protease'
	return target, target_name