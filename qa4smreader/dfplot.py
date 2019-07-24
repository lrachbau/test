# -*- coding: utf-8 -*-
'''
Contains plotting routines that take pd.DataFrames and metadata dictionaries 
as input and return figure and axes objects.
'''
from qa4smreader import globals

import numpy as np
import pandas as pd

import os.path

import seaborn as sns

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.gridspec as gridspec
import colorcet as cc

from cartopy import config as cconfig
cconfig['data_dir'] = os.path.join(os.path.dirname(__file__), 'cartopy')
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

import warnings

import time

def boxplot(df, varmeta, printnumbers=globals.boxplot_printnumbers,
            watermark_pos=globals.watermark_pos, figsize=globals.boxplot_figsize,
            dpi=globals.dpi, add_title=True, title_pad = globals.title_pad):
    """
    Create a boxplot from the variables in df. 
    The box shows the quartiles of the dataset while the whiskers extend 
    to show the rest of the distribution, except for points that are 
    determined to be “outliers” using a method that is a function of 
    the inter-quartile range.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing 'lat', 'lon' and (multiple) 'var' Series.
    title : str, optional
        Title of the plot. If None, a title is autogenerated from metadata.
        The default is None.
    label : str, optional
        Label of the colorbar. If None, a label is autogenerated from metadata.
        The default is None.
    df : TYPE
        DESCRIPTION.
    varmeta : dict
        dictionary of metadata for each var. See interface.get_varmeta().
    printnumbers : bool, optional
        Wheter to print median, standard derivation and n_obs . 
        The default is globals.boxplot_printnumbers.
    watermark_pos : str, optional
        Placement of watermark. 'top' | 'bottom' | None.
        If None, no watermark gets placed.
        The default is globals.watermark_pos.
    figsize : tuple, optional
        Figure size in inches. The default is globals.map_figsize.
    dpi : int, optional
        Resolution for raster graphic output. The default is globals.dpi.
    add_title : bool, optional
        The default is True.
    title_pad : TYPE, optional
        DESCRIPTION. The default is globals.title_pad.

    Returns
    -------
    fig : TYPE
        DESCRIPTION.
    ax : TYPE
        DESCRIPTION.

    """
    df = df.copy(deep=False)
    # TODO: drop everything not in varmeta.
    # === drop lat lon ===
    try:
        df.drop(columns=globals.index_names, inplace=True)
    except KeyError:
        pass

    # === rename columns = label of box ===
    if printnumbers:
        # === calculate mean, std dev, Nobs ===
        for var in varmeta:
            varmeta[var]['median'] = df[var].median()
            varmeta[var]['stddev'] = df[var].std()
            varmeta[var]['Nobs'] = df[var].count()
        # === rename columns before plotting ===
        df.columns = ['{0}\n({1})\nmedian: {2:.3g}\nstd. dev.: {3:.3g}\nN obs.: {4:d}'.format(
                varmeta[var]['ds_pretty_name'],
                varmeta[var]['ds_version_pretty_name'],
                varmeta[var]['median'],
                varmeta[var]['stddev'],
                varmeta[var]['Nobs']) for var in varmeta]
    else:
        df.columns = ['{}\n{}'.format(
                varmeta[var]['ds_pretty_name'],
                varmeta[var]['ds_version_pretty_name']) for var in varmeta]

    # === plot ===
    fig,ax = plt.subplots(figsize=figsize, dpi=dpi) #tight_layout = True,
    sns.set_style("whitegrid")
    ax = sns.boxplot(data=df, ax=ax, width=0.15, showfliers=False, color='white')
    sns.despine()

    # === style ===
    globmeta = _get_globmeta(varmeta)
    metric=globmeta['metric']
    ax.set_ylim(get_value_range(df, metric))
    ax.set_ylabel(globals._metric_name[metric] +
                  globals._metric_description[metric].format(globals._metric_units[globmeta['ref']]))

    # === generate title with automatic line break ===
    if add_title:
        plot_title = list() #each list element is a line in the plot title
        plot_title.append('Comparing {} to '.format(globmeta['ref_pretty_name']))
        for var in varmeta:
            to_append = '{}, '.format(varmeta[var]['ds_pretty_name'])
            if len(plot_title[-1] + to_append) <= globals.max_title_len: #line not to long: add to current line
                plot_title[-1] += to_append
            else: #add to next line
                plot_title.append(to_append)
        plot_title = '\n'.join(plot_title)[:-2] #join lines together and remove last ', '
        plot_title = ' and '.join(plot_title.rsplit(', ',1)) #replace last ', ' with ' and '
        ax.set_title(plot_title, pad=title_pad)

    # === watermark ===
    plt.tight_layout()
    if watermark_pos: make_watermark(fig,watermark_pos)
    return fig,ax

def scatterplot(df, var, meta, title=None, label=None, plot_extent=None,
                colormap=None, figsize=globals.map_figsize, dpi=globals.dpi,
                projection = None, watermark_pos=globals.watermark_pos,
                add_title = True, add_cbar=True,
                **style_kwargs):
    """
    Create a scatterplot from df and use df[var] as color.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing 'lat', 'lon' and 'var' Series.
    var : str
        variable to be plotted.
    meta : dict
        dictionary of metadata. See interface.get_meta().
    title : str, optional
        Title of the plot. If None, a title is autogenerated from metadata.
        The default is None.
    label : str, optional
        Label of the colorbar. If None, a label is autogenerated from metadata.
        The default is None.
    plot_extent : tuple
        (x_min, x_max, y_min, y_max) in Data coordinates. The default is None.
    colormap : str, optional
        colormap to be used. 
        If None, defaults to globals._colormaps. 
        The default is None.
    figsize : tuple, optional
        Figure size in inches. The default is globals.map_figsize.
    dpi : int, optional
        Resolution for raster graphic output. The default is globals.dpi.
    projection : cartopy.crs, optional
        Projection to be used. If none, defaults to globals.map_projection. 
        The default is None.
    watermark_pos : str, optional
        Placement of watermark. 'top' | 'bottom' | None.
        If None, no watermark gets placed.
        The default is globals.watermark_pos.
    add_title : bool, optional
        The default is True.
    add_cbar : bool, optional
        Add a colorbar. The default is True.
    **style_kwargs : 
        Keyword arguments for plotter.style_map().

    Returns
    -------
    fig : matplotlib.figure
        
    ax : matplotlib.axes
        axes containing the plot without colorbar, watermark etc.
    """
    # === value range ===
    v_min, v_max = get_value_range(df[var], meta['metric'])

    # === coordiniate range ===
    if not plot_extent: plot_extent = get_plot_extent(df)

    # === marker size ===
    markersize = globals.markersize**2 #in points**2

    # === init plot ===
    fig, ax, cax = init_plot(figsize, dpi, add_cbar)

    # === plot ===
    if not colormap: colormap=globals._colormaps[meta['metric']]
    cmap = plt.cm.get_cmap(colormap)
    lat, lon = globals.index_names
    im = ax.scatter(df[lon], df[lat], c=df[var],
            cmap=cmap, s=markersize, vmin=v_min, vmax=v_max, edgecolors='black',
            linewidths=0.1, zorder=2, transform=globals.data_crs)

    # === add colorbar ===
    if add_cbar: _make_cbar(fig, im, cax, df[var], v_min, v_max, meta, label)

    # === style ===
    if add_title: _make_title(ax, meta, title)
    style_map(ax, plot_extent, **style_kwargs)

    # === layout ===
    fig.canvas.draw() #nötig wegen bug in cartopy. dauert sehr lange!
    plt.tight_layout() #pad=1 in units of the font size (default 10points). #pad=0.5,h_pad=1,w_pad=1,rect=(0, 0, 1, 1))

    # === watermark ===
    if watermark_pos: make_watermark(fig,watermark_pos) #tight_layout does not take into account annotations, so make_watermark needs to be called after.

    return fig,ax

def mapplot(df, var, meta, title=None, label=None, plot_extent=None,
            colormap=None, figsize=globals.map_figsize, dpi=globals.dpi,
            projection = None, watermark_pos=globals.watermark_pos,
            add_title = True, add_cbar=True,
            **style_kwargs):
    """
    Create an overview map from df using df[var] as color.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing 'lat', 'lon' and 'var' Series.
    var : str
        variable to be plotted.
    meta : dict
        dictionary of metadata. See interface.get_meta().
    title : str, optional
        Title of the plot. If None, a title is autogenerated from metadata.
        The default is None.
    label : str, optional
        Label of the colorbar. If None, a label is autogenerated from metadata.
        The default is None.
    plot_extent : tuple
        (x_min, x_max, y_min, y_max) in Data coordinates. The default is None.
    colormap : str, optional
        colormap to be used. 
        If None, defaults to globals._colormaps. 
        The default is None.
    figsize : tuple, optional
        Figure size in inches. The default is globals.map_figsize.
    dpi : int, optional
        Resolution for raster graphic output. The default is globals.dpi.
    projection : cartopy.crs, optional
        Projection to be used. If none, defaults to globals.map_projection. 
        The default is None.
    watermark_pos : str, optional
        Placement of watermark. 'top' | 'bottom' | None.
        If None, no watermark gets placed.
        The default is globals.watermark_pos.
    add_title : bool, optional
        The default is True.
    add_cbar : bool, optional
        Add a colorbar. The default is True.
    **style_kwargs : 
        Keyword arguments for plotter.style_map().

    Returns
    -------
    fig : matplotlib.figure
        
    ax : matplotlib.axes
        axes containing the plot without colorbar, watermark etc.
    """
    # === value range ===
    v_min, v_max = get_value_range(df[var], meta['metric'])

    # === coordiniate range ===
    if not plot_extent: plot_extent = get_plot_extent(df)

    # === init plot ===
    fig, ax, cax = init_plot(figsize, dpi, add_cbar)

    # === prepare data ===
    zz, zz_extent = geotraj_to_geo2d(df, var)

    # === plot ===
    if not colormap: colormap=globals._colormaps[meta['metric']]
    cmap = plt.cm.get_cmap(colormap)
    im = ax.imshow(zz, cmap=cmap, vmin=v_min, vmax=v_max,
                   interpolation='nearest', origin='lower',
                   extent=zz_extent,
                   transform=globals.data_crs, zorder=2)

    # === add colorbar ===
    if add_cbar: _make_cbar(fig, im, cax, df[var], v_min, v_max, meta, label)

    # === style ===
    if add_title: _make_title(ax, meta, title)
    style_map(ax, plot_extent, **style_kwargs)

    # === layout ===
    fig.canvas.draw() #nötig wegen bug in cartopy. dauert sehr lange!
    plt.tight_layout(pad=1) #pad=0.5,h_pad=1,w_pad=1,rect=(0, 0, 1, 1))

    # === watermark ===
    if watermark_pos: make_watermark(fig,watermark_pos) #tight_layout does not take into account annotations, so make_watermark needs to be called after.

    return fig,ax

def geotraj_to_geo2d(df, var):
    """
    Converts geotraj (list of lat, lon, value) to a regular grid over lon, lat.
    The data in df needs to be sampled from a regular grid, the order does not matter.
    When used with plt.imshow(), specify data_extent to make sure, 
    the pixels are exactly where they are expected.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing 'lat', 'lon' and 'var' Series.
    var : str
        variable to be converted.

    Returns
    -------
    zz : numpy.ndarray
        array holding the gridded data. When using plt.imshow, specify origin='lower'.
        [0,0] : llc (lower left corner)
        first coordinate is longitude.
    data_extent : tuple
        (x_min, x_max, y_min, y_max) in Data coordinates.

    """
    def _float_gcd(a, b, atol = 1e-08):
        "Greatest common divisor (=groesster gemeinsamer teiler)"
        while abs(b) > atol:
            a, b = b, a % b
        return a

    def _get_even(a):
        "Find the stepsize of a and return an evenly spaced array"
        a = np.unique(a)
        das = np.unique(np.diff(a)) #find stepsizes
        da = das[0] #smallest stepsize
        for d in das[1:]: #make sure, other stepsizes are multiple of dy
            da = _float_gcd(d, da)
        a_min = a[0]
        a_max = a[-1]
        len_a = int( (a_max-a_min) / da + 1 )
        return a_min, a_max, da, len_a #np.arange(a_min, a_max+da, da)

    def _index(a, a_min, da):
        "Return the index corresponding to a"
        return int((a-a_min)/da)

    lons = df[globals.index_names[1]]
    lats = df[globals.index_names[0]]
    data = df[var]

    x_min, x_max, dx, len_x = _get_even(lons)
    y_min, y_max, dy, len_y = _get_even(lats)

    zz = np.empty((len_y, len_x), dtype=np.float64)
    zz[:] = np.nan

    for x, y, z in zip(lons, lats, data): #TODO: speed up! takes 2s for 180k points
        zz[_index(y, y_min, dy), _index(x, x_min, dx)] = z

    data_extent = (x_min-dx/2, x_max+dx/2, y_min-dy/2, y_max+dy/2)

    return zz, data_extent

def get_value_range(ds, metric=None, force_quantile=False, quantiles=[0.025,0.975]):
    """
    Get the value range (v_min, v_max) from globals._metric_value_ranges
    If the range is (None, None), a symmetric range around 0 is created,
    showing at least the symmetric <quantile> quantile of the data. 
    if force_quantile is True, the quantile range is used.

    Parameters
    ----------
    ds : (pandas.Series | pandas.DataFrame)
        Series holding the data
    metric : (str | None), optional
        name of the metric (e.g. 'R'). None equals to force_quantile=True.
        The default is None.
    force_quantile : bool, optional
        always use quantile, regardless of globals.
        The default is False.
    quantiles : list, optional
        quantile of data to include in the range.
        The default is [0.025,0.975]

    Returns
    -------
    v_min : float
        lower value range of plot.
    v_max : float
        upper value range of plot.
    extend : str
        arg for colorbar. Whether to extend the colorbar using an arrow.
    """
    if metric == None: force_quantile=True
    if not force_quantile: #try to get range from globals
        try:
            v_min = globals._metric_value_ranges[metric][0]
            v_max = globals._metric_value_ranges[metric][1]
            if (v_min == None and v_max == None): #get quantile range and make symmetric around 0.
                v_min, v_max = get_quantiles(ds,quantiles)
                v_max = max(abs(v_min),abs(v_max)) #make sure the range is symmetric around 0
                v_min = -v_max
            elif v_min == None:
                v_min = get_quantiles(ds,quantiles)[0]
            elif v_max == None:
                v_max = get_quantiles(ds,quantiles)[1]
            else: #v_min and v_max are both determinded in globals
                pass
        except KeyError: #metric not known, fall back to quantile
            force_quantile = True
            warnings.warn('The metric \'{}\' is not known. \n'.format(metric) + \
                          'Could not get value range from globals._metric_value_ranges\n' + \
                          'Computing quantile range \'{}\' instead.\n'.format(str(quantiles)) +
                          'Known metrics are: \'' + \
                          '\', \''.join([metric for metric in globals._metric_value_ranges]) + '\'')

    if force_quantile: #get quantile range
        v_min, v_max = get_quantiles(ds,quantiles)

    return v_min, v_max

def get_quantiles(ds,quantiles):
    """
    Gets lower and upper quantiles from pandas.Series or pandas.DataFrame

    Parameters
    ----------
    ds : (pandas.Series | pandas.DataFrame)
        Input data.
    quantiles : list
        quantile of data to include in the range

    Returns
    -------
    v_min : float
        lower quantile.
    v_max : float
        upper quantile.

    """
    q = ds.quantile(quantiles)
    if isinstance(ds,pd.Series):
        return q.iloc[0], q.iloc[1]
    elif isinstance(ds,pd.DataFrame):
        return min(q.iloc[0]), max(q.iloc[1])
    else:
        raise TypeError("Inappropriate argument type. 'ds' must be pandas.Series or pandas.DataFrame.")

def get_plot_extent(df):
    """
    Gets the plot_extent from the data. Uses range of data and 
    adds a padding fraction as specified in globals.map_pad

    Parameters
    ----------
    df : pandas.DataFrame
        Plot data.
    
    Returns
    -------
    extent : tuple | list
        (x_min, x_max, y_min, y_max) in Data coordinates.
    
    """
    lat,lon = globals.index_names
    extent=[df[lon].min(),
            df[lon].max(),
            df[lat].min(),
            df[lat].max()]
    dx = extent[1]-extent[0]
    dy = extent[3]-extent[2]
    #set map-padding around data to be globals.map_pad percent of the smaller dimension
    padding = min(dx,dy) * globals.map_pad/(1+globals.map_pad)
    extent[0] -= padding
    extent[1] += padding
    extent[2] -= padding
    extent[3] += padding
    if extent[0]<-180: extent[0]=-180
    if extent[1]>180: extent[1]=180
    if extent[2]<-90: extent[2]=-90
    if extent[3]>90: extent[3]=90
    return extent

def init_plot(figsize, dpi, add_cbar, projection=globals.crs):
    fig = plt.figure(figsize=figsize, dpi=dpi)
    if add_cbar:
        gs = gridspec.GridSpec(nrows=2, ncols=1, height_ratios=[19,1])
        ax = fig.add_subplot(gs[0],projection=projection)
        cax = fig.add_subplot(gs[1])
    else:
        gs = gridspec.GridSpec(nrows=1, ncols=1)
        ax = fig.add_subplot(gs[0],projection=projection)
        cax = None
    return fig, ax, cax

def get_cbarextend(ds, v_min, v_max):
    """
    Find out whether the colorbar should extend, based on data and limits.  

    Parameters
    ----------
    ds : pandas.Series
        Series holding the data.
    v_min : float
        lower value range of plot.
    v_max : float
        upper value range of plot.
    metric : str
        metric used in plot

    Returns
    -------
    str
        one of ['neither', 'min', 'max', 'both'].

    """
    if v_min <= min(ds):
        if v_max >= max(ds):
            return 'neither'
        else:
            return 'max'
    else:
        if v_max >= max(ds):
            return 'min'
        else:
            return 'both'

def get_cbarextend2(metric):
    """
    Find out whether the colorbar should extend, based on globals._metric_value_ranges[metric]

    Parameters
    ----------
    metric : str
        metric used in plot

    Returns
    -------
    str
        one of ['neither', 'min', 'max', 'both'].

    """
    vrange = globals._metric_value_ranges[metric]
    if vrange[0]==None:
        if vrange[1]==None: return 'both'
        else: return 'min'
    else:
        if vrange[1]==None: return 'max'
        else: return 'neither'

def _make_cbar(fig, im, cax, ds, v_min, v_max, meta, label=None):
    metric = meta['metric']
    ref = meta['ref']
    if not label:
        try:
            label = globals._metric_name[metric] + \
                        globals._metric_description[metric].format(
                                globals._metric_units[ref])
        except KeyError as e:
            raise Exception('The metric \'{}\' or reference \'{}\' is not known.\n'.format(metric, ref) + str(e))
    #extend=get_cbarextend(ds,v_min,v_max)
    extend=get_cbarextend2(metric)
    cbar = fig.colorbar(im, cax=cax, orientation='horizontal', extend=extend)
    cbar.set_label(label) #, size=5)
    cbar.outline.set_linewidth(0.4)
    cbar.outline.set_edgecolor('black')
    cbar.ax.tick_params(width=0.4)#, labelsize=4)

def _make_title(ax, meta=None, title=None, title_pad=globals.title_pad):
    if not title:
        try:
            title = 'Comparing {0} ({1}) to {2} ({3})'.format(
                meta['ref_pretty_name'],
                meta['ref_version_pretty_name'],
                meta['ds_pretty_name'],
                meta['ds_version_pretty_name'])
        except TypeError:
            raise Exception('Either \'meta\' or \'title\' need to be specified!')
    ax.set_title(title, pad=title_pad)

def style_map(ax, plot_extent, add_grid=True, map_resolution=globals.naturalearth_resolution,
              add_topo=False, add_coastline=True,
              add_land=True, add_borders=True, add_us_states=False):
    ax.set_extent(plot_extent)
    ax.outline_patch.set_linewidth(0.4)
    if add_grid: # add gridlines
        grid_interval = max((plot_extent[1] - plot_extent[0]),
                            (plot_extent[3] - plot_extent[2]))/5 #create approximately 4 gridlines in the bigger dimension
        grid_interval = min(globals.grid_intervals, key = lambda x:abs(x-grid_interval)) #select the grid spacing from the list which fits best
        gl = ax.gridlines(crs=globals.data_crs, draw_labels=False,
                          linewidth=0.5, color='grey', linestyle='--',
                          zorder=3)
        xticks = np.arange(-180,180.001,grid_interval)
        yticks = np.arange(-90,90.001,grid_interval)
        gl.xlocator = mticker.FixedLocator(xticks)
        gl.ylocator = mticker.FixedLocator(yticks)
        try: #drawing labels fails for most projections
            gltext = ax.gridlines(crs=globals.data_crs, draw_labels=True,
                          linewidth=0.5, color='grey', alpha=0., linestyle='--',
                          zorder=4)
            xticks = xticks[(xticks>=plot_extent[0]) & (xticks<=plot_extent[1])]
            yticks = yticks[(yticks>=plot_extent[2]) & (yticks<=plot_extent[3])]
            gltext.xformatter=LONGITUDE_FORMATTER
            gltext.yformatter=LATITUDE_FORMATTER
            gltext.xlabels_top=False
            gltext.ylabels_left=False
            gltext.xlocator = mticker.FixedLocator(xticks)
            gltext.ylocator = mticker.FixedLocator(yticks)
        except RuntimeError as e:
            print("No tick labels plotted.\n" + str(e))
    if add_topo: ax.stock_img()
    if add_coastline:
        coastline = cfeature.NaturalEarthFeature('physical', 'coastline',
                                 map_resolution,
                                 edgecolor='black', facecolor='none')
        ax.add_feature(coastline, linewidth=0.4, zorder=3)
    if add_land:
        land = cfeature.NaturalEarthFeature('physical', 'land',
                                 map_resolution,
                                 edgecolor='none', facecolor='white')
        ax.add_feature(land, zorder=1)
    if add_borders:
        borders = cfeature.NaturalEarthFeature('cultural', 'admin_0_countries',
                                 map_resolution,
                                 edgecolor='black', facecolor='none')
        ax.add_feature(borders, linewidth=0.2, zorder=3)
    if add_us_states: ax.add_feature(cfeature.STATES, linewidth=0.1, zorder=3)

def make_watermark(fig,placement):
    """
    Adds a watermark to fig and adjusts the current axis to make sure there
    is enough padding around the watermarks.
    Padding can be adjusted in globals.watermark_pad.
    Fontsize can be adjusted in globals.watermark_fontsize.
    plt.tight_layout needs to be called prior to make_watermark

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    placement : str
        'top' : places watermark in top right corner
        'bottom' : places watermark in bottom left corner

    Returns
    -------
    None.

    """
    #ax = fig.gca()
    #pos1 = ax.get_position() #fraction of figure
    fontsize = globals.watermark_fontsize
    pad = globals.watermark_pad
    height = fig.get_size_inches()[1]
    offset = ((fontsize+pad)/globals.matplotlib_ppi)/height
    if placement == 'top':
        plt.annotate(s=globals.watermark, xy = [1,1], xytext = [-pad,-pad],
                     fontsize=fontsize, color='grey',
                     horizontalalignment='right', verticalalignment='top',
                     xycoords = 'figure fraction', textcoords = 'offset points')
        #pos2 = matplotlib.transforms.Bbox.from_extents(pos1.x0, pos1.y0, pos1.x1, pos1.y1-offset)
        #ax.set_position(pos2) #todo: rather use fig.subplots_adjust
        top=fig.subplotpars.top
        fig.subplots_adjust(top=top-offset)
    elif placement == 'bottom':
        plt.annotate(s=globals.watermark, xy = [0,0], xytext = [pad,pad],
                     fontsize=fontsize, color='grey',
                     horizontalalignment='left', verticalalignment='bottom',
                     xycoords = 'figure fraction', textcoords = 'offset points')
        #pos2 = matplotlib.transforms.Bbox.from_extents(pos1.x0, pos1.y0+offset, pos1.x1, pos1.y1)
        #ax.set_position(pos2) #todo: rather use fig.subplots_adjust
        bottom=fig.subplotpars.bottom
        fig.subplots_adjust(bottom=bottom+offset) #defaults to rc when none!
    else:
        pass

def _get_globmeta(varmeta):
    """
    get globmeta from varmeta and make sure it is consistent in itself.
    """
    globkeys = ['metric', 'ref', 'ref_pretty_name', 'ref_version', 'ref_version_pretty_name']
    def get_globdict(meta):
        return {k:meta[k] for k in globkeys}
    variter = iter(varmeta)
    globmeta = get_globdict(varmeta[next(variter)])
    while True: #for loop with iterator: compare if globmeta is universal among all variables
        try:
            var = next(variter)
            if globmeta != get_globdict(varmeta[var]):
                raise Exception('Global Metadata inconsistent among variables!\nglobmeta : {}\nvs.\nglobmeta(\'{}\') : {}'.format(
                        globmeta, var, get_globdict(varmeta[var]) ) )
        except StopIteration:
            break
    return globmeta

def debug_tight_layout_gs(fig,gs):
    try:
        print('space before tight_layout\n   top: {:.3f}, bottom: {:.3f}, left: {:.3f}, right: {:.3f}'.format(
            1-gs.top, gs.bottom,
            gs.left, 1-gs.right))
    except:
        pass
    fig.canvas.draw() #recessary due to a bug in cartopy (https://github.com/SciTools/cartopy/issues/1207#issuecomment-439966984)
    gs.tight_layout(fig, pad=1)
    print('space after tight_layout\n   top: {:.3f}, bottom: {:.3f}, left: {:.3f}, right: {:.3f}'.format(
            1-gs.top, gs.bottom,
            gs.left, 1-gs.right))
    print('spacing if using fontsize as padding\n   left/right: {:.3f}, top/bottom: {:.3f}'.format(
            *(matplotlib.rcParams['font.size'] / 72) / fig.get_size_inches()))

def debug_tight_layout(fig):
    print('space before tight_layout\n   top: {:.3f}, bottom: {:.3f}, left: {:.3f}, right: {:.3f}'.format(
        1-fig.subplotpars.top, fig.subplotpars.bottom,
        fig.subplotpars.left, 1-fig.subplotpars.right))
    fig.canvas.draw() #recessary due to a bug in cartopy (https://github.com/SciTools/cartopy/issues/1207#issuecomment-439966984)
    plt.tight_layout(pad=1)
    print('space after tight_layout\n   top: {:.3f}, bottom: {:.3f}, left: {:.3f}, right: {:.3f}'.format(
            1-fig.subplotpars.top, fig.subplotpars.bottom,
            fig.subplotpars.left, 1-fig.subplotpars.right))
    print('spacing if using fontsize as padding\n   left/right: {:.3f}, top/bottom: {:.3f}'.format(
            *(matplotlib.rcParams['font.size'] / 72) / fig.get_size_inches()))