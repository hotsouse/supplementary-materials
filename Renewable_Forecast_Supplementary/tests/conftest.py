from pathlib import Path
import sys
import pytest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from renewable.data import load_data

@pytest.fixture(scope='session')
def root():return Path(__file__).resolve().parents[1]
@pytest.fixture(scope='session')
def panels(root):return load_data(root/'data/raw/ELEC-C_20261019-070746.csv')[1]
@pytest.fixture(scope='session')
def records(root):return pd.read_csv(root/'outputs/tables/CANDIDATE_PREDICTIONS.csv')
