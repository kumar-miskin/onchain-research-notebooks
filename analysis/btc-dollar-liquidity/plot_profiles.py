"""Render matched-session profiles from local analysis outputs. No network access."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def render(directory):
    p=Path(directory)
    w=pd.read_csv(p/'200week_profiles.csv',index_col=0,parse_dates=True)/1e9
    d=pd.read_csv(p/'200session_profiles.csv',index_col=0,parse_dates=True)/1e9
    colors=['#73a89a','#969394','#251f21']
    fig,ax=plt.subplots(figsize=(12,6))
    for name,color,ls in [('NVDA','#251f21','-'),('Mag7 basket','#969394','--'),
                          ('Gross BTC-linked activity','#73a89a','-'),('BTC spot','#73a89a',':')]:
        z=w[name]
        ax.plot(z.index,z,lw=2.5,color=color,ls=ls,label=name)
    ax.set(title='Dollar trading activity on matched US equity sessions',ylabel='Billions of US dollars per week (200-week mean)')
    ax.legend(frameon=False);ax.grid(axis='y',alpha=.2)
    fig.text(.10,.02,'Source: Yahoo Finance daily history. BTC weekends/US equity holidays excluded; gross channels can overlap.',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(p/'matched_comparison.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(12,8))
    cols=['BTC spot','Listed funds / GBTC trust','MSTR equity proxy']
    for ax,frame,title in [(axs[0],w,'200-week mean, $B/week'),(axs[1],d,'200-session mean, $B/session')]:
        z=frame[cols].dropna();ax.stackplot(z.index,z.T,labels=cols,colors=colors)
        ax.set_ylabel(title);ax.grid(axis='y',alpha=.2)
    axs[0].legend(frameon=False,loc='upper left');fig.suptitle('Gross BTC-linked trading activity')
    fig.text(.10,.02,'Yahoo Finance. Selected spot funds/GBTC trust + MSTR from Aug 11, 2020. Not unique liquidity or net inflows.',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,.97]);fig.savefig(p/'matched_channels.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--input-dir',required=True)
    render(a.parse_args().input_dir)
