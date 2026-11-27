"""Publication typography. Locally licensed font files can be registered via TNR_FONT_DIR."""
import os
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import font_manager


def configure_figures():
    directory = os.environ.get('TNR_FONT_DIR')
    if directory:
        for file in sorted(Path(directory).iterdir()):
            if file.suffix.lower() in {'.ttf', '.otf'}:
                font_manager.fontManager.addfont(file)
    plt.rcParams.update({'font.family': 'serif', 'font.serif': [
        'Times New Roman', 'Nimbus Roman', 'Liberation Serif'], 'font.size': 30,
        'axes.titlesize': 30, 'axes.titleweight': 'bold', 'axes.labelsize': 30,
        'xtick.labelsize': 30, 'ytick.labelsize': 30, 'legend.fontsize': 30,
        'figure.labelsize': 30, 'axes.spines.top': False, 'axes.spines.right': False,
        'pdf.fonttype': 42})
