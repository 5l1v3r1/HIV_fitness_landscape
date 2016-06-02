# vim: fdm=indent
'''
author:     Fabio Zanini
date:       15/06/15
content:    Make figure 2. This script plots precomputed data, so you have to run
            it after the following scripts that actually compute the results:
               - fitness_cost_saturation.py (sat fit)
               - fitness_cost_KL.py (KL fit)
               - combined_af.py (pooled fit)
'''
# Modules
import os
import sys
import argparse
from itertools import izip
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from Bio.Seq import translate

from hivevo.patients import Patient
from hivevo.HIVreference import HIVreference
from hivevo.sequence import alpha, alphal

from util import add_binned_column, boot_strap_patients



# Functions
def load_data_saturation():
    import cPickle as pickle
    fn = '../data/fitness_cost_saturation_plot.pickle'
    with open(fn, 'r') as f:
        data = pickle.load(f)
    return data


def load_data_KL():
    '''Load data from Vadim's KL approach'''
    S_center = np.loadtxt('../data/genomewide_smuD_KL_quant_medians.txt')
    s_mean, s_std = np.loadtxt('../data/genomewide_smuD_KLmu_multi_boot.txt')[:,:-2]

    data = pd.DataFrame({'mean': s_mean, 'std': s_std}, index=S_center)
    data.index.name = 'Entropy'
    data.name = 'Fitness costs'

    return data


def load_data_pooled():
    '''Load data from the pooled allele frequencies'''
    import cPickle as pickle
    with open('../data/combined_af_avg_selection_coeff_st_any.pkl', 'r') as f:
        caf_s = pickle.load(f)
    return caf_s


def plot_fit(data_sat, data_KL, data_pooled):
    from matplotlib import cm
    from util import add_panel_label

    palette = sns.color_palette('colorblind')

    fig_width = 5
    fs = 16
    fig, axs = plt.subplots(1, 2,
                            figsize=(2 * fig_width, fig_width))


    data_to_fit = data_sat['data_to_fit']
    mu = data_sat['mu']
    s = data_sat['s']

    fun = lambda x, s: mu / s * (1.0 - np.exp(-s * x))

    # PANEL A: data and fits
    ax = axs[0]
    for iS, (S, datum) in enumerate(data_to_fit.iterrows()):
        x = np.array(datum.index)
        y = np.array(datum)
        color = cm.jet(1.0 * iS / data_to_fit.shape[0])

        # Most conserved group is dashed
        if iS == 0:
            ls = '--'
        else:
            ls = '-'

        ax.scatter(x, y,
                   s=70,
                   color=color,
                  )

        xfit = np.linspace(0, 3000)
        yfit = fun(xfit, s.loc[S, 's'])
        ax.plot(xfit, yfit,
                lw=2,
                color=color,
                ls=ls,
               )

    ax.set_xlabel('days since EDI', fontsize=fs)
    ax.set_ylabel('Average allele frequency', fontsize=fs)
    ax.set_xlim(-200, 3200)
    ax.set_ylim(-0.0005, 0.025)
    ax.set_xticks(np.linspace(0, 0.005, 5))
    ax.set_xticks([0, 1000, 2000, 3000])
    ax.xaxis.set_tick_params(labelsize=fs)
    ax.yaxis.set_tick_params(labelsize=fs)

    ax.text(0, 0.023,
            r'$\mu = 1.2 \cdot 10^{-5}$ per day',
            fontsize=16)
    ax.plot([200, 1300], [0.007, 0.007 + (1300 - 200) * mu], lw=1.5, c='k')

    # PANEL B: costs
    ax = axs[1]

    # B1: Saturation fit
    x = np.array(s.index)
    y = np.array(s['s'])
    dy = np.array(s['ds'])

    ymin = 0.1

    x = x[1:]
    y = y[1:]
    dy = dy[1:]

    ax.errorbar(x, y,
                yerr=dy,
                ls='-',
                marker='o',
                lw=2,
                color=palette[0],
                label='Sat',
               )

    # B2: KL fit
    # Ignore most conserved quantile
    x = np.array(data_KL.index)  [1:]
    y = np.array(data_KL['mean'])[1:]
    dy = np.array(data_KL['std'])[1:]
    ax.errorbar(x, y, yerr=dy,
                ls='-',
                marker='o',
                lw=2,
                color=palette[1],
                label='KL',
               )

    # B3: pooled
    x = data_pooled['all'][:-1, 0]
    y = data_pooled['all'][:-1, 1]
    dy = data_pooled['all_std'][:-1, 1]
    ax.errorbar(x, y, yerr=dy,
                ls='-',
                marker='o',
                lw=2,
                color=palette[2],
                label='Pooled',
               )

    ax.legend(loc='upper right', fontsize=16)
    ax.set_xlabel('Variability in group M [bits]', fontsize=fs)
    ax.set_ylabel('Fitness cost', fontsize=fs)
    ax.set_xlim(0.9e-3, 2.5)
    ax.set_ylim(9e-5, 0.11)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.xaxis.set_tick_params(labelsize=fs)
    ax.yaxis.set_tick_params(labelsize=fs)


    # Panel labels
    add_panel_label(axs[0], 'A', x_offset=-0.27)
    add_panel_label(axs[1], 'B', x_offset=-0.21)

    plt.tight_layout()
    plt.ion()
    plt.show()



# Script
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Figure 2')
    args = parser.parse_args()

    data_sat = load_data_saturation()
    data_KL = load_data_KL()
    data_pooled = load_data_pooled()

    plot_fit(data_sat, data_KL, data_pooled)

    for ext in ['.png', '.pdf', '.svg']:
        plt.savefig('../figures/figure_2'+ext)
