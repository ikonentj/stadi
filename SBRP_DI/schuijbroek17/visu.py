import matplotlib.pylab as plt
import numpy as np
from SBRP_DI import aux
from SBRP_DI import schuijbroek17 as sch17

def plotProbs(t_vals, p_vals, freq=1, legend=True):
    plt.figure(figsize=(16, 6))
    for i in range(0, p_vals.shape[1], freq):
        plt.plot(t_vals, p_vals[:,i], alpha=0.5, label=str(i))
    plt.plot(t_vals, np.sum(p_vals, axis=1), 
    			alpha=0.5, c='k', linestyle='--', label='sum')
    plt.grid()
    plt.xlim(t_vals[0], t_vals[-1])
    if legend:
	    plt.legend(ncol=4);

def plotRates(mu, lamda, station, props, legend=True):
    fig = plt.figure(figsize=(16, 6))
    row = aux.duplicateLast(mu.loc[station, :])
    plt.step(row.index, row.values, where='post', label='pickup $\mu (t)$')
    row = aux.duplicateLast(lamda.loc[station, :])
    plt.step(row.index, row.values, where='post', label='return $\lambda (t)$')
    n = int(1 / props['interval'])
    plt.xticks(row.index[::4*n], 
              ['{}:00'.format(hour) for hour in range(0, 25, 4)])
    if legend:
        plt.legend(ncol=4)
    plt.ylabel('rate')
    plt.xlabel('time')
    plt.grid();

def plotCapacities(stations, slr=True, level=True, annotate='id'):
    fig = plt.figure(figsize=(16, 8))

    # capacities
    x = np.arange(stations.shape[0]) 
    plt.vlines(x, 0, stations['# of Docks'], linestyles='dashed', color='r', label='docks')
    plt.scatter(x, np.zeros(stations.shape[0]), marker='_', s=70, color='r')
    plt.scatter(x, stations['# of Docks'], marker='_', s=70, color='r')

    # service level requirements
    if slr and 's_min' in stations.columns and 's_max' in stations.columns:
        plt.vlines(x, stations['s_min'], stations['s_max'], linestyles='solid', color='b', label='bounds for SL requirement')
        plt.scatter(x, stations['s_min'], marker='_', s=70, color='b')
        plt.scatter(x, stations['s_max'], marker='_', s=70, color='b')

    # level
    if level and 'level' in stations.columns:
        plt.scatter(x[stations['selfSufficient']], 
                    stations['level'][stations['selfSufficient']], 
                    s=70, color='b', label='self-sufficient')
        plt.scatter(x[~stations['selfSufficient']], 
                    stations['level'][~stations['selfSufficient']], 
                    marker='^', s=70, color='r', label='requires rebalancing')
    plt.legend()
        
    # labels for x axis
    if annotate == 'id':
        plt.xticks(x, stations.index, rotation='vertical')
    elif annotate == 'ord':
        plt.xticks(x, stations.reset_index().index)
    elif annotate == 'name':
        plt.xticks(x, stations['Station'], rotation='vertical')
    elif annotate == False:
        fig.axes[0].get_xaxis().set_visible(False)

    # settings
    plt.ylabel('bikes')
    plt.grid();

    return fig

def plotLevelPredictions(sys, props, t_start, t_end, station_ids=None, stamps=True, cumsum=True, max_prob=0.5, c='m', tdisc=101):
    # extract hours
    hours_start = aux.dt_to_hours(t_start)
    hours_end   = aux.dt_to_hours(t_end)
    if hours_start == 0 and hours_end == 0:
        hours_end = 24

    # determine the ids of the stations to be plotted
    if station_ids == None:
        station_ids = sys.sortedKeys()
        
    # init the plot
    fig, axes = plt.subplots(len(station_ids), figsize=(18, 4*len(station_ids)))
    if not type(axes) == np.ndarray:
        axes = [axes]
        
    for i, station_id in enumerate(station_ids):
        # pick a station from the system
        station = sys.stations[station_id]
        
        # determine and plot the probabilities
        t_vals, p_vals = station.predictor.determine_probs(station.level(), t_start, t_end)
        t_vals, p_vals = sch17.tools.interpolate(p_vals, t_vals, 
                                                    np.linspace(t_vals[0], t_vals[-1], tdisc))
        
        # plot the probabilities
        im = axes[i].imshow(p_vals.T, interpolation='nearest',
                       origin='lower', 
                       extent=[hours_start, hours_end, -0.5, station.n_docks+0.5],
                       aspect='auto',
                       vmin=0, vmax=max_prob
                      )
        cbar = fig.colorbar(im, ax=axes[i], label='probability [-]')

        # plot the realizations
        if stamps:
            stamps_slice = station.stamps[t_start:t_end]
            axes[i].scatter(aux.dt_to_hours(stamps_slice.index), stamps_slice.bikesAvailable, c=c, s=5)
        
        if cumsum:
            pr_cumsum = station.pr_cumsum(t_start, t_end)
            axes[i].step(
                        aux.dt_to_hours(pr_cumsum.index), 
                        pr_cumsum.values + station.level(), 
                        where='post', c=c
                        )
            finalLevel = pr_cumsum.values[-1] + station.level()
            axes[i].plot([aux.dt_to_hours(pr_cumsum.index[-1]), hours_end], [finalLevel, finalLevel], c=c)
            
        # settings
        axes[i].set_ylabel('# of bikes at {} ({})'.format(station_id, station.name[:8]))
        axes[i].set_xlabel('hour on {}'.format(station.stamps.index[0].strftime("%Y-%m-%d")))
        axes[i].set_ylim(-0.5, sys.stations[station_id].n_docks+0.5)
        
    return fig, axes, cbar