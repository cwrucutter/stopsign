#!/usr/bin/env python3

import pandas as pd

import matplotlib
matplotlib.use('TKAgg')
from matplotlib import pyplot as plt

pkg_path = '/home/buck/ros_ws/src/stopsign'
POSITIVE_FILE = '%s/data/015_visualize/positive_bits_200.csv' % (pkg_path,)
NEGATIVE_FILE = '%s/data/015_visualize/negative_bits_200%s.csv' % (pkg_path, '_%d')

bit_label = 'd%02db%01d'

descriptors = []
for i in range(32):
    for bit_index in range(0, 8):
        descriptors.append('d%02db%01d' % (i, bit_index,))

klass = ['class']

# Vizualize Correlation Matrices

df = pd.read_csv(POSITIVE_FILE, header=0)

correlation_matrix = df.corr()
plt.matshow(correlation_matrix)
plt.savefig('positive_corr_matrix.png')
plt.show()

for i in range(5):
    df = pd.read_csv(NEGATIVE_FILE % (i,), header=0)
    correlation_matrix = df.corr()
    plt.matshow(correlation_matrix)
    plt.savefig('negative_corr_matrix_%d.png' % (i,))
    plt.show()

# Visualize "Pairwise" Correlation via Karnaugh Maps
# abcd
#   00 01 11 10
# 00
# 01  counts
# 11   here
# 10
# This would require 4 billion visualizations which would be cool, but tangential to the project
