import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from . import aux

import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 
          'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']

def initMap(coastline=False, size=(8, 8)):
    fig = plt.figure(figsize=size)
    ax = plt.axes(projection=ccrs.PlateCarree())
    if coastline:
        ax.coastlines(resolution='10m')
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER

    return fig, ax

def setFont(fontSize):
    """The function sets latex font to be used in the next plots. 
    
    :param fontSize: The font size.
    """
    params = {
              #'text.usetex' : True,   #Options
              'font.size' : fontSize,
              'font.family' : 'Times New Roman',
              'mathtext.fontset': 'stix'
              }
    plt.rcParams.update(params)

def plotLoad(operations, Q):
    # init the plot
    maxPath = max([op_per_v.shape[0] for op_per_v in operations.values()])
    n_vehicles = len(operations)
    fig, axes = plt.subplots(n_vehicles, figsize=(14, n_vehicles*3))
    if n_vehicles == 1:
        axes = [axes]

    # plot all subpaths to separate plots
    for i, ax in enumerate(axes):
        per_vehic_sorted = operations[i].set_index('ord').sort_index()
        x_locations = range(per_vehic_sorted.shape[0])
        ax.step(x_locations, per_vehic_sorted['load'].values, where='post')
        ax.hlines([0, Q], 0, maxPath, colors='k', linestyles='--')
        if maxPath > 0:
            ax.set_xlim(0, maxPath)
        if i == len(axes) -1:
            ax.set_xlabel('station ID')
        ax.set_ylabel('load on vehicle [-]')
        ax.set_xticks(x_locations)
        ax.set_xticklabels(per_vehic_sorted['Station ID'].values)
        
    return fig, ax

def plotStations(stations, annotate=False, coastline=False, selfsuf=True, fig_ax=None, pervehicle=False):
    # determine wheather to create a new figure or continue on fig_ax
    if fig_ax == None:
        fig, ax = initMap(coastline=coastline)
    else:
        fig, ax = fig_ax

    # plot self-sufficient stations
    if selfsuf:
        plt.scatter(stations['Longitude'][stations['selfSufficient']], 
                    stations['Latitude'][stations['selfSufficient']], 
                    alpha=0.5, marker='o', label='self-sufficient');
    
    # plot stations per vehicle...
    if pervehicle:
        for vehicle_id in np.sort(stations['vehicle'][~stations['vehicle'].isna()].unique()):
            plt.scatter(stations['Longitude'][stations['vehicle'] == vehicle_id], 
                    stations['Latitude'][stations['vehicle'] == vehicle_id], 
                    alpha=0.5, marker='^', label='allocated to vehicle {}'.format(int(vehicle_id)));
    
    # ... or plot self-insufficient stations
    else:
        plt.scatter(stations['Longitude'][~stations['selfSufficient']], 
                    stations['Latitude'][~stations['selfSufficient']], 
                    alpha=0.5, marker='^', label='requires rebalancing');

    # annotate the stations
    if annotate == 'id':
        for station in stations.index:
            plt.annotate(stations.loc[station, 'Station ID'], (stations.loc[station, 'Longitude']+5e-4, 
                                                               stations.loc[station, 'Latitude']+5e-4))

    elif annotate == 'ord':
        stations_w_ord = stations.reset_index()
        for station in stations_w_ord.index:
            plt.annotate(station, (stations_w_ord.loc[station, 'Longitude']+5e-4, 
                                   stations_w_ord.loc[station, 'Latitude']+5e-4))
    elif annotate == 'name':
        for station in stations.index:
            plt.annotate(stations.loc[station, 'Station'], 
                            (stations.loc[station, 'Longitude']+5e-4, 
                             stations.loc[station, 'Latitude']+5e-4))

    plt.legend()

    return fig, ax

def plotRoute(stations, operations, params, selfsuf=False, **kwargs):
    # move 'vehicle' also to stations
    for v in operations.keys():
        indices = stations['Station ID'].isin(operations[v]['Station ID'].values)
        stations.loc[indices, 'vehicle'] = v

    # plot station locations
    fig, ax = plotStations(stations, selfsuf=False, **kwargs)

    # plot self-sufficients
    if not type(selfsuf) == bool:
        plt.scatter(selfsuf['Longitude'], selfsuf['Latitude'], alpha=0.5, marker='o', c='0.5', label='self-sufficient');

    # plot route
    for v in operations.keys():
        plt.plot(operations[v].sort_values(by='ord')['Longitude'].values,
                 operations[v].sort_values(by='ord')['Latitude'].values, alpha=0.3
                );

    plt.legend()
    
    return fig, ax

def plotRoute_from_system(system, t, annotate=None):
    # helper function
    def getCoords(ids):
        return [system.stations[s_id].longitude for s_id in ids], [system.stations[s_id].latitude for s_id in ids]
    
    # initialize the map
    fig, ax = initMap(size=(10, 10))

    # get the current vehicle coordinates
    coords = system.vehicleCoords(t)

    visited = []
    for vehicle in system.vehicles.values():
        # plot planned route
        op_current = vehicle.op_archive[t]
        plannedStations = op_current.index.values
        lon, lat = getCoords(plannedStations)
        plt.plot(lon, lat, alpha=0.7, ls='--', c=colors[vehicle.id]);
        
        # plot stations that are planned to be visited
        plt.scatter(lon, lat, c=colors[vehicle.id], marker='^', 
                    label='allocated to vehicle {}'.format(vehicle.id+1));
        
        # plot past route
        mask = vehicle.loc_archive.t_arrival <= op_current.t_arrival.values[0]
        past = vehicle.loc_archive[mask]['Station ID']
        if not past.empty:
            lon, lat = getCoords(past)
            plt.plot(lon, lat, alpha=0.7, c=colors[vehicle.id]);
        
        # plot the current vehicle location
        plt.scatter(coords[vehicle.id][0], coords[vehicle.id][1], facecolors='none', s=150, edgecolors=colors[vehicle.id])

        # record the visited stations
        visited += list(vehicle.loc_archive.index.values)
        visited += list(vehicle.op.index.values)
        
    # plot self-sufficients
    lon, lat = getCoords([station.id for station in system.stations.values() 
                              if not station.id in plannedStations])
    plt.scatter(lon, lat, alpha=0.7, marker='o', c='0.5', label='self-sufficient');
    
    # annotate the stations
    if annotate == 'all':
        to_be_annotated = [station for station in system.stations.values()]
    elif annotate == 'visited':
        to_be_annotated = [station for station in system.stations.values() if station.id in visited]
    else:
        to_be_annotated = []
    for station in to_be_annotated:
        plt.annotate(station.id, (station.longitude+5e-4, station.latitude+5e-4))

    plt.legend()
    ax.set_aspect('auto')
    
    return fig, ax

def plotLoad_from_system(system, t, maxTime=None):
    n_vehicles = len(system.vehicles)
    fig, axes = plt.subplots(n_vehicles, figsize=(16, n_vehicles*3))
    if n_vehicles == 1:
        axes = [axes]

    # plot all subpaths to separate plots
    for i in system.sortedVehicleKeys():
        vehicle = system.vehicles[i]
        startTime = vehicle.load_archive.t.values[0]
        
        # planned load
        load = load_from_op(vehicle.op_archive[t])
        axes[i].plot(load.index, load.load, ls='--', c='tab:blue')
        
        # past load
        pastLoad = pastLoad_from_vehicle(vehicle, load.index[0])
        axes[i].plot(pastLoad.index, pastLoad.load, c='tab:blue')
        
        # arrival times (past locations)
        mask = vehicle.loc_archive.t_arrival < t 
        pastLocs = vehicle.loc_archive[mask]
        axes[i].vlines(pastLocs.t_arrival, 0, system.params['Q'], ls=':', lw=0.5, colors='black')
        for ind in pastLocs.index:
            axes[i].annotate(int(pastLocs.loc[ind, 'Station ID']), 
                                 xy=(pastLocs.loc[ind, 't_arrival'], system.params['Q']+1))
        
        # arrival times (future locations)
        arrivals = arrivals_from_op(vehicle.op_archive[t])
        axes[i].vlines(arrivals.t, 0, system.params['Q'], ls=':', lw=0.5, colors='black')
        for ind in arrivals.index:
            axes[i].annotate(arrivals.loc[ind, 'Station ID'], xy=(arrivals.loc[ind, 't'], system.params['Q']+1))

        # current time
        axes[i].vlines(t, 0, system.params['Q'], ls='-', lw=0.5, colors='tab:red')
        
        # plot settings
        axes[i].hlines([0, system.params['Q']], startTime, maxTime, colors='k', linestyles='-')
        axes[i].set_xlim(startTime, None)
        axes[i].set_ylim(None, system.params['Q']*1.2)
        if i == len(axes) - 1:
            axes[i].set_xlabel('time')
        axes[i].set_ylabel('load on vehicle {}'.format(i+1))
        
    return fig, axes

def pastLoad_from_vehicle(vehicle, t):
    mask = vehicle.load_archive.t <= t
    pastLoad = vehicle.load_archive[mask].copy()
    pastLoad.set_index('t', inplace=True)
    
    mask = vehicle.loc_archive.t_arrival < t
    if (~mask).any():
        mask.loc[mask[~mask].index[0]] = True
    newIndices = vehicle.loc_archive[mask].set_index('t_arrival').index
    arrivalLoad = pd.DataFrame(index=newIndices)
    
    merged = pd.concat([pastLoad, arrivalLoad])
    merged = merged[~merged.index.duplicated(keep="first")]
    
    return merged.sort_index().ffill()

def load_from_op(op):
    arrivals = op[['load', 'delta', 't_arrival']].copy()
    arrivals.columns = ['depLoad', 'delta', 't']
    arrivals['load'] = arrivals['depLoad'] - arrivals['delta']
    arrivals.drop(columns=['delta', 'depLoad'], inplace=True)
    arrivals.reset_index(inplace=True)

    departures = op[['load', 't_departure']].copy()
    departures.columns = ['load', 't']
    departures.reset_index(inplace=True)

    op_processed = pd.concat([arrivals, departures])
    return op_processed.sort_values(by='t').set_index('t', drop=True)

def arrivals_from_op(op):
    arrivals = op[['load', 'delta', 't_arrival']].copy()
    arrivals.columns = ['depLoad', 'delta', 't']
    arrivals['load'] = arrivals['depLoad'] - arrivals['delta']
    arrivals.drop(columns=['delta', 'depLoad'], inplace=True)
    return arrivals.reset_index()

def makePlots(tr, selfsuf, stations, params, args):
    # save operations
    tr.saveOperations(args.path_run + '{}/'.format(args.model))

    # plot load
    setFont(14)
    tr.dropArtificials()
    fig, ax = plotLoad(tr.op, params['Q'])
    fig.tight_layout()
    fig.savefig(args.path_run + '{}/load.pdf'.format(args.model))

    # plot route
    if params['units'] == 'meters':
        fig_ax = plt.subplots(figsize=(8, 8))
    else:
        fig_ax = None
    fig, ax = plotRoute(stations, tr.op, params, annotate='id', pervehicle=True, 
                selfsuf=selfsuf, fig_ax=fig_ax)
    fig.savefig(args.path_run + '{}/route.pdf'.format(args.model))