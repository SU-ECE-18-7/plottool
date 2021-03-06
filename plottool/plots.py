# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import warnings
from six.moves import zip, range, zip_longest
from plottool import draw_func2 as df2
import six
import scipy.stats
import matplotlib.pyplot as plt
import utool as ut  # NOQA
import numpy as np
from plottool import custom_figure

#ut.noinject(__name__, '[plots]')
print, rrr, profile = ut.inject2(__name__, '[plots]')

#custom_figure.TITLE_SIZE = 8
# Titlesize for old non-multiplot plots
#custom_figure.TITLE_SIZE = 12


def is_default_dark_bg():
    #return True
    #lightbg = not  ut.get_argflag('--darkbg')
    lightbg = ut.get_argflag('--save') or ut.get_argflag('--lightbg')
    return not lightbg


def multi_plot(xdata, ydata_list, **kwargs):
    r"""
    plots multiple lines, bars, etc...

    This is the big function that implements almost all of the heavy lifting in
    this file.  Any function not using this should probably find a way to use
    it. It is pretty general and relatively clean.


    Args:
        xdata (ndarray):
        ydata_list (list of ndarrays):

    Kwargs:
        fnum, pnum, title, xlabel, ylabel, num_xticks, use_legend, legend_loc,
        labelsize, xmin, xmax, ymin, ymax, ticksize, titlesize, legendsize, spread_list
        can append _list to any of these
        plot_kw_keys = ['label', 'color', 'marker', 'markersize', 'markeredgewidth', 'linewidth', 'linestyle']
        kind = ['bar', 'plot', ...]

    References:
        matplotlib.org/examples/api/barchart_demo.html

    CommandLine:
        python -m plottool.plots --exec-multi_plot --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> xdata = [1, 2, 3, 4, 5]
        >>> ydata_list = [[1, 2, 3, 4, 5], [3, 3, 3, 3, 3], [5, 4, np.nan, 2, 1], [4, 3, np.nan, 1, 0]]
        >>> kwargs = {'label_list': ['spam', 'eggs', 'jam', 'pram'],  'linestyle': '-'}
        >>> fig = multi_plot(xdata, ydata_list, title='$\phi_1(\\vec{x})$', xlabel='\nfds', **kwargs)
        >>> result = ('fig = %s' % (str(fig),))
        >>> print(result)
        >>> ut.show_if_requested()
    """
    import matplotlib as mpl
    import plottool as pt

    xdata = np.array(xdata).copy()
    num_lines = len(ydata_list)

    fnum = pt.ensure_fnum(kwargs.get('fnum', None))
    pnum = kwargs.get('pnum', None)
    kind = kwargs.get('kind', 'plot')
    transpose = kwargs.get('transpose', False)

    def parsekw_list(key, kwargs, num_lines=num_lines):
        """ copies relevant plot commands into plot_list_kw """
        if key in kwargs:
            val_list = [kwargs[key]] * num_lines
        elif key + '_list' in kwargs:
            val_list = kwargs[key + '_list']
        elif key + 's' in kwargs:
            # hack, multiple ways to do something
            val_list = kwargs[key + 's']
        else:
            val_list = None
            #val_list = [None] * num_lines
        return val_list

    # Parse out arguments to ax.plot
    plot_kw_keys = ['label', 'color', 'marker', 'markersize',
                    'markeredgewidth', 'linewidth', 'linestyle']
    # hackish / extra args that dont go to plot, but help
    extra_plot_kw_keys = ['spread_alpha', 'autolabel']
    plot_kw_keys += extra_plot_kw_keys
    plot_ks_vals = [parsekw_list(key, kwargs) for key in plot_kw_keys]
    plot_list_kw = dict([
        (key, vals)
        for key, vals in zip(plot_kw_keys, plot_ks_vals) if vals is not None
    ])

    if 'color' not in plot_list_kw:
        plot_list_kw['color'] = pt.distinct_colors(num_lines)

    if kind == 'plot':
        if 'marker' not in plot_list_kw:
            plot_list_kw['marker'] = pt.distinct_markers(num_lines)
        if 'spread_alpha' not in plot_list_kw:
            plot_list_kw['spread_alpha'] = [.2] * num_lines

    if kind == 'bar':
        # Remove non-bar kwargs
        ut.delete_keys(plot_list_kw, ['markeredgewidth', 'linewidth', 'marker',
                                      'markersize', 'linestyle'])
        width = kwargs.get('width', .9) / num_lines
        if transpose:
            #plot_list_kw['orientation'] = ['horizontal'] * num_lines
            plot_list_kw['height'] = [width] * num_lines
        else:
            plot_list_kw['width'] = [width] * num_lines
        #xdata - (width / 2)

    spread_list = kwargs.get('spread_list', None)
    if spread_list is None:
        pass

    # nest into a list of dicts for each line in the multiplot
    valid_keys = ut.setdiff_ordered(list(plot_list_kw.keys()), extra_plot_kw_keys)
    valid_vals = ut.dict_take(plot_list_kw, valid_keys)
    plot_kw_list = [dict(zip(valid_keys, vals)) for vals in zip(*valid_vals)]

    extra_kw_keys = [key for key in extra_plot_kw_keys if key in plot_list_kw]
    extra_kw_vals = ut.dict_take(plot_list_kw, extra_kw_keys)
    extra_kw_list = [dict(zip(extra_kw_keys, vals)) for vals in zip(*extra_kw_vals)]

    # Setup figure
    # newfig = kwargs.get('newfig', True)
    # if newfig:
    fig = pt.figure(fnum=fnum, pnum=pnum)
    # else:
    #     fig = pt.gcf()

    # +---------------
    # Draw plot lines
    ax = pt.gca()
    ydata_list = np.array(ydata_list)

    if transpose:
        if kind == 'bar':
            plot_func = ax.barh
        elif kind == 'plot':
            def plot_func(_x, _y, **kw):
                return ax.plot(_y, _x, **kw)
    else:
        plot_func = getattr(ax, kind)  # usually ax.plot

    assert len(ydata_list) > 0, 'no ydata'
    #ut.embed()
    #assert len(extra_kw_list) == len(plot_kw_list), 'bad length'
    #assert len(extra_kw_list) == len(ydata_list), 'bad length'
    _iter = enumerate(zip_longest(ydata_list, plot_kw_list, extra_kw_list))
    for count, (ydata, plot_kw, extra_kw) in _iter:
        ymask = np.isfinite(ydata)
        ydata_ = ydata.compress(ymask)
        xdata_ = xdata.compress(ymask)
        #print('count = %r' % (count,))
        #print('ydata_ = %r' % (ydata_,))
        #print('xdata_ = %r' % (xdata_,))
        #ax.plot(xdata_, ydata_, **plot_kw)
        if kind == 'bar':
            baseoffset = (width * num_lines) / 2
            lineoffset = (width * count)
            offset = baseoffset - lineoffset  # Fixeme for more histogram bars
            xdata_ = xdata_ - offset
        objs = plot_func(xdata_, ydata_, **plot_kw)
        if kind == 'bar':
            if extra_kw is not None and extra_kw.get('autolabel', False):
                # FIXME: probably a more cannonical way to include bar
                # autolabeling with tranpose support, but this is a hack that
                # works for now
                for rect in objs:
                    if transpose:
                        numlbl = width = rect.get_width()
                        xpos = width + ((xdata.max() - xdata.min()) * .005)
                        ypos = rect.get_y() + rect.get_height() / 2.
                        ha, va = 'left', 'center'
                    else:
                        numlbl = height = rect.get_height()
                        xpos = rect.get_x() + rect.get_width() / 2.
                        ypos = 1.05 * height
                        ha, va = 'center', 'bottom'
                    barlbl = '%.3f' % (numlbl,)
                    ax.text(xpos, ypos, barlbl, ha=ha, va=va)

        if spread_list is not None:
            # Plots a spread around plot lines usually indicating standard
            # deviation
            xdata = np.array(xdata)
            spread = spread_list[count]
            ydata_ave = np.array(ydata_)
            y_data_dev = np.array(spread)
            y_data_max = ydata_ave + y_data_dev
            y_data_min = ydata_ave - y_data_dev
            ax = df2.gca()
            spread_alpha = extra_kw['spread_alpha']
            ax.fill_between(xdata, y_data_min, y_data_max, alpha=spread_alpha,
                            color=plot_kw.get('color', None))  # , zorder=0)
    # L________________

    #max_y = max(np.max(y_data), max_y)
    #min_y = np.min(y_data) if min_y is None else min(np.min(y_data), min_y)

    if transpose:
        #xdata_list = ydata_list
        ydata = xdata
        # Hack / Fix any transpose issues
        def transpose_key(key):
            if key.startswith('x'):
                return 'y' + key[1:]
            elif key.startswith('y'):
                return 'x' + key[1:]
            elif key.startswith('num_x'):
                # hackier, fixme to use regex or something
                return 'num_y' + key[5:]
            elif key.startswith('num_y'):
                # hackier, fixme to use regex or something
                return 'num_x' + key[5:]
            else:
                return key
        kwargs = {transpose_key(key): val for key, val in kwargs.items()}

    # Setup axes labeling
    title      = kwargs.get('title', None)
    xlabel     = kwargs.get('xlabel', '')
    ylabel     = kwargs.get('ylabel', '')

    # Font sizes
    #titlesize  = kwargs.get('titlesize',  12)
    #labelsize  = kwargs.get('labelsize',  10)
    #legendsize = kwargs.get('legendsize', 10)

    titlesize  = kwargs.get('titlesize',  custom_figure.TITLE_SIZE)
    labelsize  = kwargs.get('labelsize',  custom_figure.LABEL_SIZE)
    legendsize = kwargs.get('legendsize', custom_figure.LEGEND_SIZE)

    labelkw = {
        'fontproperties': mpl.font_manager.FontProperties(
            weight='light', size=labelsize)
    }
    ax.set_xlabel(xlabel, **labelkw)
    ax.set_ylabel(ylabel, **labelkw)

    ticksize = kwargs.get('ticksize', None)
    if ticksize is not None:
        for label in ax.get_xticklabels():
            label.set_fontsize(ticksize)
        for label in ax.get_yticklabels():
            label.set_fontsize(ticksize)

    # Setup axes limits
    if 'xlim' in kwargs:
        raise AssertionError('use xmax xmin instead')
    if 'ylim' in kwargs:
        raise AssertionError('use ymax ymin instead')

    xmin = kwargs.get('xmin', ax.get_xlim()[0])
    xmax = kwargs.get('xmax', ax.get_xlim()[1])
    ymin = kwargs.get('ymin', ax.get_ylim()[0])
    ymax = kwargs.get('ymax', ax.get_ylim()[1])

    text_type = six.text_type

    if text_type(xmax) == 'data':
        xmax = xdata.max()
    if text_type(xmin) == 'data':
        xmin = xdata.min()

    # Setup axes ticks
    num_xticks = kwargs.get('num_xticks', None)
    num_yticks = kwargs.get('num_yticks', None)
    if num_xticks is not None:
        # TODO check if xdata is integral
        if ut.is_int(xdata):
            xticks = np.linspace(np.ceil(xmin), np.floor(xmax),
                                 num_xticks).astype(np.int32)
        else:
            xticks = np.linspace((xmin), (xmax), num_xticks)
        ax.set_xticks(xticks)
    if num_yticks is not None:
        if ut.is_int(ydata):
            yticks = np.linspace(np.ceil(ymin), np.floor(ymax),
                                 num_yticks).astype(np.int32)
        else:
            yticks = np.linspace((ymin), (ymax), num_yticks)
        ax.set_yticks(yticks)

    yticklabels = kwargs.get('yticklabels', None)
    if yticklabels is not None:
        # Hack ONLY WORKS WHEN TRANSPOSE = True
        # Overrides num_yticks
        ax.set_yticks(ydata)
        ax.set_yticklabels(yticklabels)

    xticklabels = kwargs.get('xticklabels', None)
    if xticklabels is not None:
        # Overrides num_xticks
        ax.set_xticks(xdata)
        ax.set_xticklabels(xticklabels)

    xtick_rotation = kwargs.get('xtick_rotation', None)
    if xtick_rotation is not None:
        [lbl.set_rotation(xtick_rotation)
         for lbl in ax.get_xticklabels()]
    ytick_rotation = kwargs.get('ytick_rotation', None)
    if ytick_rotation is not None:
        [lbl.set_rotation(ytick_rotation)
         for lbl in ax.get_yticklabels()]

    # Axis padding
    xpad = kwargs.get('xpad', None)
    ypad = kwargs.get('ypad', None)
    xpad_factor = kwargs.get('xpad_factor', None)
    ypad_factor = kwargs.get('ypad_factor', None)
    if xpad is None and xpad_factor is not None:
        xpad = (xmax - xmin) * xpad_factor
    if ypad is None and ypad_factor is not None:
        ypad = (ymax - ymin) * ypad_factor
    xpad = 0 if xpad is None else xpad
    ypad = 0 if ypad is None else ypad
    ypad_high = kwargs.get('ypad_high', ypad)
    ypad_low  = kwargs.get('ypad_low', ypad)
    xpad_high = kwargs.get('xpad_high', xpad)
    xpad_low  = kwargs.get('xpad_low', xpad)
    xmin, xmax = (xmin - xpad_low), (xmax + xpad_high)
    ymin, ymax = (ymin - ypad_low), (ymax + ypad_high)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    xscale          = kwargs.get('xscale', None)
    yscale          = kwargs.get('yscale', None)
    if yscale is not None:
        ax.set_yscale(yscale)
    if xscale is not None:
        ax.set_xscale(xscale)

    # Setup title
    if title is not None:
        titlekw = {
            'fontproperties': mpl.font_manager.FontProperties(
                weight='light', size=titlesize)
        }
        ax.set_title(title, **titlekw)

    use_legend   = kwargs.get('use_legend', 'label' in valid_keys)
    legend_loc   = kwargs.get('legend_loc', 'best')
    legend_alpha = kwargs.get('legend_alpha', 1.0)
    if use_legend:
        df2.legend(loc=legend_loc, size=legendsize, alpha=legend_alpha)

    use_darkbackground = kwargs.get('use_darkbackground', None)
    lightbg = kwargs.get('lightbg', None)
    if lightbg is None:
        lightbg = not is_default_dark_bg()
    if use_darkbackground is None:
        use_darkbackground = not lightbg
        #use_darkbackground = is_default_dark_bg()
    if use_darkbackground:
        pt.dark_background(force=use_darkbackground is True)
    # TODO: return better info
    return fig


def plot_multiple_scores(known_nd_data, known_target_points, nd_labels,
                         target_label, title=None, use_legend=True,
                         color_list=None, marker_list=None, report_max=True,
                         **kwargs):
    r"""
    Plots nd-data in 2d using multiple contour lines

    CommandLine:
        python -m plottool.plots --test-plot_multiple_scores --show

        python -m plottool.plots --exec-plot_rank_cumhist \
            --adjust=.15 --dpi=512 --figsize=11,4 --clipwhite \
            --dpath ~/latex/crall-candidacy-2015/ --save "figures/tmp.jpg"  --diskshow \

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> known_nd_data = np.array([[  1,   2,   4,   7,   1,   2,   4,   7,   1,   2,   4,   7,   1,
        ...                              2,   4,   7,   1,   2,   4,   7],
        ...                           [ 50,  50,  50,  50, 100, 100, 100, 100, 200, 200, 200, 200, 300,
        ...                            300, 300, 300, 500, 500, 500, 500]], dtype=np.int64).T
        >>> known_target_points = np.array([35, 32, 32, 30, 33, 32, 33, 30, 32, 31, 31, 32, 36, 33, 33, 32, 33,
        ...                                 33, 32, 31], dtype=np.int64)
        >>> label_list = ['custom', 'custom:sv_on=False']
        >>> nd_labels = [u'K', u'dsize']
        >>> target_label = 'score'
        >>> fnum = None
        >>> pnum = None
        >>> use_legend = True
        >>> title = 'test'
        >>> result = plot_multiple_scores(known_nd_data, known_target_points, nd_labels, target_label, title=title)
        >>> print(result)
        >>> ut.show_if_requested()
    """
    #import matplotlib as mpl
    assert(len(known_nd_data.T) == 2), 'cannot do more than 2 right now'

    # Put the data into a dense field grid
    nd_basis = [np.unique(arr) for arr in known_nd_data.T]
    inverse_basis = [dict(zip(arr, np.arange(len(arr)))) for arr in nd_basis]
    data_field = np.full(ut.maplen(nd_basis), np.nan)
    # Fill in field values
    for coord, val in zip(known_nd_data, known_target_points):
        index = [invbase[pt] for invbase, pt in zip(inverse_basis, coord)]
        data_field.__setitem__(tuple(index), val)

    xdata = nd_basis[0]
    ydata_list = data_field.T

    if report_max:
        # TODO: multiple max poses
        import vtool as vt
        maxpos_list = ydata_list.argmax(axis=1)
        max_nd0_list = nd_basis[0].take(maxpos_list)
        max_score_list = vt.ziptake(ydata_list, maxpos_list)
        hasmultiple_max = (ydata_list == np.array(max_score_list)[:, None]).sum(axis=1) > 1
        multiple_max_markers = ['*' if flag else '' for flag in hasmultiple_max]

        if nd_labels[1] is None:
            label_list = [
                '%.2f%% %s=%r%s'
                % (max_score, nd_labels[0], max_nd0, marker)
                for max_nd0, max_score, marker in zip(
                    max_nd0_list, max_score_list, multiple_max_markers)
            ]
        else:
            label_list = [
                '%.2f%% %s=%r%s - %s=%r'
                % (max_score, nd_labels[0], max_nd0, marker, nd_labels[1], val)
                for val, max_nd0, max_score, marker in zip(
                    nd_basis[1], max_nd0_list, max_score_list, multiple_max_markers)
            ]
    else:
        label_list = ['%s=%r' % (nd_labels[1], val,) for val in nd_basis[1]]

    fig = multi_plot(
        xdata, ydata_list, label_list=label_list, markersize=10,
        marker_list=marker_list, color_list=color_list, title=title,
        xlabel=nd_labels[0], ylabel=target_label, **kwargs)
    return fig


def plot_rank_cumhist(cdf_list, label_list, color_list=None, marker_list=None,
                      edges=None, xlabel='', ylabel='cumfreq', use_legend=True,
                      num_xticks=None, kind='bar', **kwargs):
    r"""

    CommandLine:
        python -m plottool.plots --test-plot_rank_cumhist --show

        python -m plottool.plots --exec-plot_rank_cumhist \
            --adjust=.15 --dpi=512 --figsize=11,4 --clipwhite \
            --dpath ~/latex/crall-candidacy-2015/ --save "figures/tmp.jpg"  --diskshow \

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> cdf_list = np.array(
        >>>     [[ 88,  92,  93,  96,  96,  96,  96,  98,  99,  99, 100, 100, 100],
        >>>      [ 79,  82,  82,  85,  86,  87,  87,  87,  88,  89,  90,  90,  90]])
        >>> edges = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        >>> label_list = ['custom', 'custom:sv_on=False']
        >>> fnum = None
        >>> pnum = None
        >>> plot_rank_cumhist(cdf_list, label_list, edges=edges, fnum=fnum, pnum=pnum)
        >>> ut.show_if_requested()
    """
    num_cdfs = len(cdf_list)
    num_data = len(cdf_list[0])
    if color_list is None:
        color_list = df2.distinct_colors(num_cdfs)

    if edges is None:
        x_data = np.arange(num_data)
    else:
        x_data = np.array(edges[1:])
    #max_y = 0
    #min_y = None
    if True or marker_list is None:
        #marker_list = ['o'] * num_cdfs
        marker_list = df2.distinct_markers(num_cdfs)
    if len(x_data) > 256:
        marker_list = [None] * num_cdfs
    if len(x_data) <= 10:
        markersize = 12
    else:
        markersize = 7

    fig = multi_plot(
        x_data, cdf_list,
        kind=kind,
        label_list=label_list, color_list=color_list, marker_list=marker_list,
        markersize=markersize, linewidth=2, markeredgewidth=2, linestyle='-',
        num_xticks=num_xticks, xlabel=xlabel, ylabel=ylabel,
        use_legend=use_legend,
        **kwargs
    )
    return fig


def draw_hist_subbin_maxima(hist, centers=None, bin_colors=None,
                            maxima_thresh=None, **kwargs):
    r"""
    Args:
        hist (ndarray):
        centers (None):

    CommandLine:
        python -m plottool.plots --test-draw_hist_subbin_maxima --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> import plottool as pt
        >>> hist = np.array([    6.73, 8.69, 0.00, 0.00, 34.62, 29.16, 0.00, 0.00, 6.73, 8.69])
        >>> centers = np.array([-0.39, 0.39, 1.18, 1.96,  2.75,  3.53, 4.32, 5.11, 5.89, 6.68])
        >>> bin_colors = pt.df2.plt.get_cmap('hsv')(centers / vt.TAU)
        >>> use_darkbackground = True
        >>> maxima_thresh = .8
        >>> result = draw_hist_subbin_maxima(hist, centers, bin_colors,
        >>>                                  maxima_thresh
        >>>                                  use_darkbackground=use_darkbackground)
        >>> print(result)
        >>> pt.show_if_requested()
    """
    # Find maxima
    import vtool as vt
    maxima_x, maxima_y, argmaxima = vt.hist_argmaxima(hist, centers, maxima_thresh)
    argmaxima = np.array(ut.ensure_iterable(argmaxima))
    maxima_y = np.array(ut.ensure_iterable(maxima_y))
    maxima_x = np.array(ut.ensure_iterable(maxima_x))
    if len(argmaxima) > 0 and argmaxima[-1] == len(hist) - 1:
        argmaxima = argmaxima[:-1]
        maxima_x = maxima_x[:-1]
        maxima_y = maxima_y[:-1]
    if len(argmaxima) > 0 and argmaxima[0] == 0:
        maxima_x = maxima_x[1:]
        maxima_y = maxima_y[1:]
        argmaxima = argmaxima[1:]
    # Expand parabola points around submaxima
    x123, y123 = vt.maxima_neighbors(argmaxima, hist, centers)
    # Find submaxima
    if len(argmaxima) == 0:
        submaxima_x = []
        submaxima_y = []
        xpoints = []
        ypoints = []
    else:
        submaxima_x, submaxima_y = vt.interpolate_submaxima(argmaxima, hist, centers)
        # Extract parabola points
        coeff_list =  [np.polyfit(xtup, ytup, 2) for xtup, ytup in zip(x123.T, y123.T)]
        xpoints = [np.linspace(x1, x3, 50) for (x1, x2, x3) in x123.T]
        ypoints = [np.polyval(coeff, x_pts) for x_pts, coeff in zip(xpoints, coeff_list)]

    use_darkbackground = kwargs.get('use_darkbackground', None)
    linecolor = 'w' if use_darkbackground else 'k'

    # Draw threshold lines
    if maxima_thresh is not None:
        maxima_thresh_val = maxima_y.max() * maxima_thresh
        plt.plot(centers, [maxima_thresh_val] * len(centers), 'r--')
    # Draw linear interpolation lines
    if bin_colors is None:
        bin_colors = 'r'
        plt.plot(centers, hist, linecolor + '-')
    else:
        # TODO use bin_color correctly
        #import matplotlib as mpl
        # Create a colormap using exact specified colors
        #bin_cmap = mpl.colors.ListedColormap(bin_colors)
        bin_cmap = plt.get_cmap('hsv')  # HACK
        #mpl.colors.ListedColormap(bin_colors)
        colorline(centers, hist, cmap=bin_cmap)
    # Draw Submax Parabola
    for x_pts, y_pts in zip(xpoints, ypoints):
        plt.plot(x_pts, y_pts, 'y--')
    # Draw maxbin
    plt.scatter(maxima_x,    maxima_y,    marker='o', color=linecolor,  s=50)
    # Draw submaxbin
    plt.scatter(submaxima_x, submaxima_y, marker='*', color='r', s=100)
    # Draw Bins
    plt.scatter(centers, hist, c=bin_colors, marker='o', s=25)

    if use_darkbackground is None:
        use_darkbackground = is_default_dark_bg()
    if use_darkbackground:
        df2.dark_background()
    print('submaxima_x = %r' % (submaxima_x,))
    print('submaxima_y = %r' % (submaxima_y,))
    #return (submaxima_x, submaxima_y)


def zoom_effect01(ax1, ax2, xmin, xmax, **kwargs):
    """
    connect ax1 & ax2. The x-range of (xmin, xmax) in both axes will
    be marked.  The keywords parameters will be used ti create
    patches.

    Args:
        ax1 (mpl.axes): the main axes
        ax2 (mpl.axes): the zoomed axes
        (xmin,xmax) : the limits of the colored area in both plot axes.

    Returns:
        tuple: (c1, c2, bbox_patch1, bbox_patch2, p)

    References:
        matplotlib.org/users/annotations_guide.html

    CommandLine:
        python -m plottool.plots zoom_effect01 --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> import plottool as pt
        >>> cdf_list = np.array(
        >>>     [[10, 15, 40, 42, 50, 88,  92,  93,  96,  96,  96,  96,  98,  99,  99, 100, 100, 100],
        >>>      [20, 30, 31, 66, 75, 79,  82,  82,  85,  86,  87,  87,  87,  88,  89,  90,  90,  90]])
        >>> edges = list(range(0, len(cdf_list[0]) + 1))
        >>> label_list = ['custom', 'custom:sv_on=False']
        >>> fnum = 1
        >>> numranks = len(cdf_list[0])
        >>> top = 3
        >>> plot_rank_cumhist(cdf_list, label_list, edges=edges, xmin=.9, num_xticks=numranks, fnum=fnum, pnum=(2, 1, 1), kind='plot', ymin=0, ymax=100)
        >>> ax1 = pt.gca()
        >>> plot_rank_cumhist(cdf_list.T[0:top].T, label_list, edges=edges[0:top + 1], xmin=.9, num_xticks=top, fnum=fnum, pnum=(2, 1, 2), kind='plot', ymin=0, ymax=100)
        >>> ax2 = pt.gca()
        >>> xmin = 1
        >>> xmax = top
        >>> (c1, c2, bbox_patch1, bbox_patch2, p) = zoom_effect01(ax1, ax2, xmin, xmax)
        >>> result = ('(c1, c2, bbox_patch1, bbox_patch2, p) = %s' % (ut.repr2((c1, c2, bbox_patch1, bbox_patch2, p)),))
        >>> print(result)
        >>> ut.quit_if_noshow()
        >>> import plottool as pt
        >>> ut.show_if_requested()

    """
    from matplotlib.transforms import (
        Bbox, TransformedBbox, blended_transform_factory)

    from mpl_toolkits.axes_grid1.inset_locator import (
        BboxPatch, BboxConnector, BboxConnectorPatch)

    def connect_bbox(bbox1, bbox2,
                     loc1a, loc2a, loc1b, loc2b,
                     prop_lines, prop_patches=None):
        if prop_patches is None:
            prop_patches = prop_lines.copy()
            prop_patches['alpha'] = prop_patches.get('alpha', 1) * .01  # * 0.05
        prop_patches['alpha'] = .1

        c1 = BboxConnector(bbox1, bbox2, loc1=loc1a, loc2=loc2a, **prop_lines)
        c1.set_clip_on(False)
        c2 = BboxConnector(bbox1, bbox2, loc1=loc1b, loc2=loc2b, **prop_lines)
        c2.set_clip_on(False)

        bbox_patch1 = BboxPatch(bbox1, **prop_patches)
        bbox_patch2 = BboxPatch(bbox2, **prop_patches)

        p = BboxConnectorPatch(bbox1, bbox2,
                               #loc1a=3, loc2a=2, loc1b=4, loc2b=1,
                               loc1a=loc1a, loc2a=loc2a, loc1b=loc1b, loc2b=loc2b,
                               **prop_patches)
        p.set_clip_on(False)

        return c1, c2, bbox_patch1, bbox_patch2, p

    trans1 = blended_transform_factory(ax1.transData, ax1.transAxes)
    trans2 = blended_transform_factory(ax2.transData, ax2.transAxes)

    bbox = Bbox.from_extents(xmin, 0, xmax, 1)

    mybbox1 = TransformedBbox(bbox, trans1)
    mybbox2 = TransformedBbox(bbox, trans2)

    prop_patches = kwargs.copy()
    prop_patches['ec'] = 'none'
    prop_patches['alpha'] = 0.2

    (c1, c2, bbox_patch1, bbox_patch2, p) = \
        connect_bbox(mybbox1, mybbox2,
                     loc1a=3, loc2a=2, loc1b=4, loc2b=1,
                     prop_lines=kwargs, prop_patches=prop_patches)

    ax1.add_patch(bbox_patch1)
    ax2.add_patch(bbox_patch2)
    ax2.add_patch(c1)
    ax2.add_patch(c2)
    ax2.add_patch(p)

    return c1, c2, bbox_patch1, bbox_patch2, p

# Interface to LineCollection:


def colorline(x, y, z=None, cmap=plt.get_cmap('hsv'),
              norm=plt.Normalize(0.0, 1.0),
              linewidth=1, alpha=1.0):
    """
    Plot a colored line with coordinates x and y
    Optionally specify colors in the array z
    Optionally specify a colormap, a norm function and a line width

    References:
        nbviewer.ipython.org/github/dpsanders/matplotlib-examples/blob/master/colorline.ipynb

    CommandLine:
        python -m plottool.plots --test-colorline --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> import plottool as pt
        >>> # build test data
        >>> x = np.array([1, 3, 3, 2, 5]) / 5.0
        >>> y = np.array([1, 2, 1, 3, 5]) / 5.0
        >>> z = None
        >>> cmap = df2.plt.get_cmap('hsv')
        >>> norm = plt.Normalize(0.0, 1.0)
        >>> linewidth = 1
        >>> alpha = 1.0
        >>> # execute function
        >>> pt.figure()
        >>> result = colorline(x, y, z, cmap)
        >>> # verify results
        >>> print(result)
        >>> pt.dark_background()
        >>> pt.show_if_requested()
    """
    from matplotlib.collections import LineCollection

    def make_segments(x, y):
        """
        Create list of line segments from x and y coordinates, in the
        Returns:
            ndarray - segments in correct format for LineCollection:
                an array with shape: (numlines, points per line, 2)
                the last dimension is for x and y respectively
        """
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        return segments

    # Default colors equally spaced on [0,1]:
    if z is None:
        z = np.linspace(0.0, 1.0, len(x))

    # Special case if a single number:
    if not hasattr(z, "__iter__"):  # to check for numerical input -- this is a hack
        z = np.array([z])

    z = np.asarray(z)

    segments = make_segments(x, y)
    lc = LineCollection(segments, array=z, cmap=cmap, norm=norm, linewidth=linewidth, alpha=alpha)

    ax = plt.gca()
    ax.add_collection(lc)

    return lc


def plot_stems(x_data, y_data, fnum=None, pnum=(1, 1, 1), **kwargs):
    """

    CommandLine:
        python -m plottool.plots --test-plot_stems
        python -m plottool.plots --test-plot_stems --show

    Example:
        >>> from plottool import *  # NOQA
        >>> import plottool as pt
        >>> x_data = [1, 1, 2, 3, 3, 3, 4, 4, 5]
        >>> y_data = [1, 2, 1, 2, 1, 4, 4, 5, 1]
        >>> pt.plots.plot_stems(x_data, y_data)
        >>> pt.show_if_requested()
    """
    if fnum is None:
        fnum = df2.next_fnum()
    df2.figure(fnum=fnum, pnum=pnum, doclf=False, docla=False)
    df2.draw_stems(x_data, y_data)
    ax = df2.gca()
    ax.set_xlabel('query index')
    ax.set_ylabel('query ranks')

    use_darkbackground = kwargs.get('use_darkbackground', None)
    if use_darkbackground is None:
        use_darkbackground = is_default_dark_bg()
    if use_darkbackground:
        df2.dark_background()

    ax.set_figtitle('plot_stems')
    #df2.legend(loc='upper left')
    df2.legend(loc='best')
    df2.iup()


def plot_score_histograms(scores_list,
                          scores_lbls=None,
                          score_markers=None,
                          score_colors=None,
                          markersizes=None,
                          fnum=None,
                          pnum=(1, 1, 1),
                          title=None,
                          score_label='score',
                          score_thresh=None,
                          overlay_prob_given_list=None,
                          overlay_score_domain=None,
                          **kwargs):
    """
    TODO:
        rewrite using multiplog

    CommandLine:
        python -m plottool.plots --test-plot_score_histograms --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> randstate = np.random.RandomState(seed=0)
        >>> # Get a training sample
        >>> tp_support = randstate.normal(loc=6.5, size=(256,))
        >>> tn_support = randstate.normal(loc=3.5, size=(256,))
        >>> scores_list = [tp_support, tn_support]
        >>> scores_lbls = None
        >>> score_markers = None
        >>> score_colors = None
        >>> markersizes = None
        >>> fnum = None
        >>> pnum = (1, 1, 1)
        >>> logscale = True
        >>> title = 'plot_scores_histogram'
        >>> result = plot_score_histograms(scores_list, scores_lbls, score_markers, score_colors, markersizes, fnum, pnum, logscale, title)
        >>> ut.show_if_requested()
        >>> print(result)
    """
    if isinstance(scores_list, np.ndarray):
        if len(scores_list.shape) == 1:
            scores_list = [scores_list]

    if title is None:
        if len(scores_list) == 1:
            title = 'Histogram of %d ' % (len(scores_list[0])) + score_label + 's'
        else:
            title = 'Histogram of ' + score_label + 's'
    title += kwargs.get('titlesuf', '')
    if scores_lbls is None:
        scores_lbls = [six.text_type(lblx) for lblx in range(len(scores_list))]
    if score_markers is None:
        score_markers = ['o' for lblx in range(len(scores_list))]
    if score_colors is None:
        score_colors = df2.distinct_colors(len(scores_list))[::-1]
    if markersizes is None:
        markersizes = [12 / (1.0 + lblx) for lblx in range(len(scores_list))]
    #labelx_list = [[lblx] * len(scores_) for lblx, scores_ in enumerate(scores_list)]
    agg_scores  = np.hstack(scores_list)

    # append amount of support
    scores_lbls = ['%s %d' % (lbl, len(ydata),) for lbl, ydata in zip(scores_lbls, scores_list)]

    dmin = agg_scores.min()
    dmax = agg_scores.max()

    # References:
    # stats.stackexchange.com/questions/798/calculating-optimal-number-of-bins-in-a-histogram-for-n-where-n-ranges-from-30
    #bandwidth = diff(range(x)) / (2 * IQR(x) / length(x) ^ (1 / 3)))

    if fnum is None:
        fnum = df2.next_fnum()

    df2.figure(fnum=fnum, pnum=pnum, doclf=False, docla=False)

    bins = None
    bin_width = kwargs.get('bin_width', None)
    if bin_width is not None:
        total_min = np.floor(min([min(scores) for scores in scores_list]))
        total_max = np.ceil(max([max(scores) for scores in scores_list]))
        #ave_diff = np.mean(ut.flatten([np.diff(sorted(scores)) for scores in scores_list]))
        #std_diff = np.std(ut.flatten([np.diff(sorted(scores)) for scores in scores_list]))
        #(total_max - total_min) / bin_width
        start = min(0, total_min)
        num_bins = kwargs.get('num_bins', None)
        if num_bins is None:
            num_bins = int((total_max - start) // bin_width)
        #end = total_max
        bins = [start + (bin_width * count) for count in range(num_bins)]
    else:
        import scipy as sp
        sortscores = np.sort(np.hstack(scores_list))
        area = sp.integrate.cumtrapz(sortscores)
        area = area / area[-1]
        inlier_scores = sortscores[np.logical_and(area < .95, area > .05)]
        (inlier_scores.max() - inlier_scores.min())

    # Plot each datapoint on a line
    _n_max = 0
    _n_min = 0
    _bin_max = 0
    for lblx in list(range(len(scores_list))):
        label = scores_lbls[lblx]
        color = score_colors[lblx]
        #marker = score_markers[lblx]
        data = scores_list[lblx]

        dmin = int(np.floor(data.min()))
        dmax = int(np.ceil(data.max()))
        if bins is None:
            bins = dmax - dmin
            bins = 50
        ax  = df2.gca()

        try:
            _n, _bins, _patches = ax.hist(
                data, bins=bins, label=str(label), color=color,
                histtype='stepfilled', alpha=.7, stacked=True)
            #range=(dmin, dmax),
            #for _p in _patches:
            #    _p.set_edgecolor(None)
            _n_min = min(_n_min, _n.min())
            _n_max = max(_n_max, _n.max())
            _bin_max = max(_bin_max, max(_bins))
        except Exception as ex:
            ut.printex(ex, 'probably gave negative scores', keys=['bins', 'data', 'total_min'])
            import utool
            utool.embed()
            raise

            if ut.SUPER_STRICT:
                raise

    if overlay_score_domain is not None:
        p_max = max([prob.max() for prob in overlay_prob_given_list])
        scale_factor = _n_max / p_max
        for lblx in list(range(len(scores_list))):
            color = score_colors[lblx]
            p_given_lbl = overlay_prob_given_list[lblx]
            p_given_lbl_norm = p_given_lbl * scale_factor
            #/ p_given_lbl.max()
            flags = overlay_score_domain < _bin_max
            overlay_score_domain_clip = overlay_score_domain[flags]
            p_given_lbl_norm_clip = p_given_lbl_norm[flags]
            ax.plot(overlay_score_domain_clip, p_given_lbl_norm_clip, color=color)

    _n_max = ax.get_ylim()[1]

    if score_thresh is not None:
        ydomain = np.linspace(_n_min, _n_max, 10)
        xvalues = [score_thresh] * len(ydomain)
        df2.plt.plot(xvalues, ydomain, 'g-', label='score thresh=%.2f' % (score_thresh,))

    import matplotlib as mpl
    ax = df2.gca()
    xlim = kwargs.get('xlim', None)
    if xlim is not None:
        ax.set_xlim(xlim)

    labelkw = {
        'fontproperties': mpl.font_manager.FontProperties(
            weight='light', size=kwargs.get('labelsize', custom_figure.LABEL_SIZE))
    }
    #df2.set_xlabel('sorted ' +  score_label + ' indices')
    ax.set_xlabel(score_label, **labelkw)
    ax.set_ylabel('frequency', **labelkw)
    #df2.dark_background()
    titlesize = kwargs.get('titlesize', custom_figure.TITLE_SIZE)
    titlekw = {
        'fontproperties': mpl.font_manager.FontProperties(weight='light', size=titlesize)
    }
    ax.set_title(title, **titlekw)
    #df2.legend(loc='upper left')
    df2.legend(loc='best', size=kwargs.get('legendsize', custom_figure.LEGEND_SIZE))
    #print('[df2] show_histogram()')
    #df2.dark_background()

    #ax.set_xscale('log')
    #ax.set_yscale('log')

    use_darkbackground = kwargs.get('use_darkbackground', None)
    if use_darkbackground is None:
        use_darkbackground = is_default_dark_bg()
    if use_darkbackground:
        df2.dark_background()
    #return fig


def plot_probabilities(prob_list,
                       prob_lbls=None,
                       prob_colors=None,
                       xdata=None,
                       prob_thresh=None,
                       score_thresh=None,
                       figtitle='plot_probabilities',
                       fnum=None,
                       pnum=(1, 1, 1),
                       fill=False,
                       **kwargs):
    """
    Input: a list of scores (either chip or descriptor)

    Concatenates and sorts the scores
    Sorts and plots with different types of scores labeled

    Args:
        prob_list (list):
        prob_lbls (None): (default = None)
        prob_colors (None): (default = None)
        xdata (None): (default = None)
        prob_thresh (None): (default = None)
        figtitle (str): (default = 'plot_probabilities')
        fnum (int):  figure number(default = None)
        pnum (tuple):  plot number(default = (1, 1, 1))
        fill (bool): (default = False)

    CommandLine:
        python -m plottool.plots --exec-plot_probabilities --show --lightbg

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> prob_list = [[.01, .02, .03, .04, .03, .06, .03, .04]]
        >>> prob_lbls = ['prob']
        >>> prob_colors = None
        >>> xdata = None
        >>> prob_thresh = None
        >>> figtitle = 'plot_probabilities'
        >>> fnum = None
        >>> pnum = (1, 1, 1)
        >>> fill = True
        >>> score_thresh = None
        >>> result = plot_probabilities(prob_list, prob_lbls, prob_colors, xdata, prob_thresh, score_thresh, figtitle, fnum, pnum, fill)
        >>> print(result)
        >>> ut.show_if_requested()
    """
    assert len(prob_list) > 0
    if xdata is None:
        xdata = np.arange(len(prob_list[0]))
    assert all([len(xdata) == len(density) for density in prob_list])

    if prob_lbls is None:
        prob_lbls = [lblx for lblx in range(len(prob_list))]
    if prob_colors is None:
        prob_colors = df2.distinct_colors(len(prob_list))[::-1]

    assert len(prob_list) == len(prob_lbls)
    assert len(prob_list) == len(prob_colors)
    #labelx_list = [[lblx] * len(scores_) for lblx, scores_ in enumerate(prob_list)]
    #agg_scores  = np.hstack()
    #agg_labelx  = np.hstack(labelx_list)
    #agg_sortx = agg_scores.argsort()

    if fnum is None:
        fnum = df2.next_fnum()

    df2.figure(fnum=fnum, pnum=pnum, doclf=False, docla=False)

    for tup in zip(prob_list, prob_lbls, prob_colors):
        density, label, color = tup
        ydata = density
        df2.plt.plot(xdata, ydata, color=color, label=label, alpha=.7)
        if fill:
            df2.plt.fill_between(xdata, ydata, color=color, alpha=.7)
        #ut.embed()
        #help(df2.plot)

    if prob_thresh is not None:
        df2.plt.plot(xdata, [prob_thresh] * len(xdata), 'g-', label='prob thresh')

    if score_thresh is not None:
        ydata_min = min([_ydata.min() for _ydata in prob_list])
        ydata_max = max([_ydata.max() for _ydata in prob_list])
        ydomain = np.linspace(ydata_min, ydata_max, 10)
        df2.plt.plot([score_thresh] * len(ydomain), ydomain, 'g-',
                     label='score thresh=%.2f' % (score_thresh,))
    import matplotlib as mpl
    labelkw = {
        'fontproperties': mpl.font_manager.FontProperties(
            weight='light', size=kwargs.get('labelsize', custom_figure.LABEL_SIZE))
    }

    ax = df2.gca()
    #ax.set_xlim(xdata.min(), xdata.max())
    ax.set_xlabel('score value', **labelkw)
    ax.set_ylabel('probability', **labelkw)

    use_darkbackground = kwargs.get('use_darkbackground', None)
    if use_darkbackground is None:
        use_darkbackground = is_default_dark_bg()
    if use_darkbackground:
        df2.dark_background()

    titlesize = kwargs.get('titlesize', custom_figure.TITLE_SIZE)
    if kwargs.get('remove_yticks', False):
        ax.set_yticks([])
    titlekw = {
        'fontproperties': mpl.font_manager.FontProperties(weight='light', size=titlesize)
    }
    ax.set_title(figtitle, **titlekw)
    #df2.legend(loc='upper left')
    if kwargs.get('use_legend', True):
        df2.legend(loc='best', size=kwargs.get('legendsize', custom_figure.LEGEND_SIZE))
    #df2.iup()


# Short alias
plot_probs = plot_probabilities
# Incorrect (but legacy) alias
plot_densities = plot_probabilities


def plot_sorted_scores(scores_list,
                       scores_lbls=None,
                       score_markers=None,
                       score_colors=None,
                       markersizes=None,
                       fnum=None,
                       pnum=(1, 1, 1),
                       logscale=True,
                       figtitle=None,
                       score_label='score',
                       thresh=None,
                       use_stems=None,
                       **kwargs):
    """
    Concatenates and sorts the scores
    Sorts and plots with different types of scores labeled

    Args:
        scores_list (list): a list of scores
        scores_lbls (None):
        score_markers (None):
        score_colors (None):
        markersizes (None):
        fnum (int):  figure number
        pnum (tuple):  plot number
        logscale (bool):
        figtitle (str):

    CommandLine:
        python -m plottool.plots --test-plot_sorted_scores --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> randstate = np.random.RandomState(seed=0)
        >>> # Get a training sample
        >>> tp_support = randstate.normal(loc=6.5, size=(256,))
        >>> tn_support = randstate.normal(loc=3.5, size=(256,))
        >>> scores_list = [tp_support, tn_support]
        >>> scores_lbls = None
        >>> score_markers = None
        >>> score_colors = None
        >>> markersizes = None
        >>> fnum = None
        >>> pnum = (1, 1, 1)
        >>> logscale = True
        >>> figtitle = 'plot_sorted_scores'
        >>> result = plot_sorted_scores(scores_list, scores_lbls, score_markers, score_colors, markersizes, fnum, pnum, logscale, figtitle)
        >>> ut.show_if_requested()
        >>> print(result)
    """
    import matplotlib as mpl
    if figtitle is None:
        figtitle = 'sorted ' + score_label
    if scores_lbls is None:
        scores_lbls = [lblx for lblx in range(len(scores_list))]
    if score_markers is None:
        score_markers = ['o' for lblx in range(len(scores_list))]
    if score_colors is None:
        score_colors = df2.distinct_colors(len(scores_list))[::-1]
    if markersizes is None:
        markersizes = [12 / (1.0 + lblx) for lblx in range(len(scores_list))]
    labelx_list = [[lblx] * len(scores_) for lblx, scores_ in enumerate(scores_list)]
    agg_scores  = np.hstack(scores_list)
    agg_labelx  = np.hstack(labelx_list)

    agg_sortx = agg_scores.argsort()

    sorted_scores = agg_scores.take(agg_sortx, axis=0)
    sorted_labelx = agg_labelx.take(agg_sortx, axis=0)

    if fnum is None:
        fnum = df2.next_fnum()

    df2.figure(fnum=fnum, pnum=pnum, doclf=False, docla=False)

    # plot stems to get a better sense of the distribution for binary data
    if use_stems is None:
        use_stems = len(scores_list) == 2
    if use_stems:
        ymax = sorted_scores.max()
        absolute_bottom = sorted_scores.min()
        for lblx in range(len(scores_list)):
            bottom = (absolute_bottom - (ymax * .1)) if lblx % 2 == 1 else ymax
            color = score_colors[lblx]
            xdata = np.where(sorted_labelx == lblx)[0]
            ydata = sorted_scores[xdata]
            # TODO: stems for binary labels
            df2.draw_stems(xdata, ydata, setlims=False, color=color, markersize=0, bottom=bottom)
            pass

    # Plot each datapoint on a line
    for lblx in range(len(scores_list)):
        label = scores_lbls[lblx]
        color = score_colors[lblx]
        marker = score_markers[lblx]
        markersize = markersizes[lblx]
        xdata = np.where(sorted_labelx == lblx)[0]
        ydata = sorted_scores[xdata]
        #printDBG('[sorted_scores] lblx=%r label=%r, marker=%r' % (lblx, label, marker))
        df2.plot(xdata, ydata, marker, color=color, label=label, alpha=.7,
                 markersize=markersize)

    if thresh is not None:
        indicies = np.arange(len(sorted_labelx))
        #print('indicies.shape = %r' % (indicies.shape,))
        df2.plot(indicies, [thresh] * len(indicies), 'g-',
                 label=score_label + ' thresh=%.2f' % (thresh,))

    if logscale:
        # DEPRICATE
        set_logyscale_from_data(sorted_scores)

    ax = df2.gca()
    # dont let xlimit go far over the number of labels
    ax.set_xlim(0, len(sorted_labelx) + 1)

    labelkw = {
        'fontproperties': mpl.font_manager.FontProperties(
            weight='light', size=kwargs.get('labelsize', custom_figure.LABEL_SIZE))
    }

    ax.set_xlabel('sorted individual ' +  score_label + ' indices', **labelkw)
    ax.set_ylabel(score_label, **labelkw)

    use_darkbackground = kwargs.get('use_darkbackground', None)
    if use_darkbackground is None:
        use_darkbackground = is_default_dark_bg()
    if use_darkbackground:
        df2.dark_background()
    titlesize = kwargs.get('titlesize', custom_figure.TITLE_SIZE)
    titlekw = {
        'fontproperties': mpl.font_manager.FontProperties(weight='light', size=titlesize)
    }
    ax.set_title(figtitle, **titlekw)
    #df2.legend(loc='upper left')
    df2.legend(loc='best', size=kwargs.get('legendsize', custom_figure.LEGEND_SIZE))
    #df2.legend(loc='best')
    #df2.iup()


def set_logyscale_from_data(y_data):
    # DEPRICATE
    if len(y_data) == 1:
        print('Warning: not enough information to infer yscale')
        return
    logscale_kwargs = get_good_logyscale_kwargs(y_data)
    ax = df2.gca()
    ax.set_yscale('symlog', **logscale_kwargs)


def get_good_logyscale_kwargs(y_data, adaptive_knee_scaling=False):
    # DEPRICATE
    # Attempts to detect knee points by looking for
    # log derivatives way past the normal standard deviations
    # The input data is assumed to be sorted and y_data
    basey = 10
    nStdDevs_thresh = 10
    # Take the log of the data
    logy = np.log(y_data)
    logy[np.isnan(logy)] = 0
    logy[np.isinf(logy)] = 0
    # Find the derivative of data
    dy = np.diff(logy)
    dy_sortx = dy.argsort()
    # Get mean and standard deviation
    dy_stats = ut.get_stats(dy)
    dy_sorted = dy[dy_sortx]
    # Find the number of standard deveations past the mean each datapoint is
    try:
        nStdDevs = np.abs(dy_sorted - dy_stats['mean']) / dy_stats['std']
    except Exception as ex:
        ut.printex(ex, key_list=[
            'dy_stats',
            (len, 'y_data'),
            'y_data',
        ])
        raise
    # Mark any above a threshold as knee points
    knee_indexes = np.where(nStdDevs > nStdDevs_thresh)[0]
    knee_mag = nStdDevs[knee_indexes]
    knee_points = dy_sortx[knee_indexes]
    #printDBG('[df2] knee_points = %r' % (knee_points,))
    # Check to see that we have found a knee
    if len(knee_points) > 0 and adaptive_knee_scaling:
        # Use linear scaling up the the knee points and
        # scale it by the magnitude of the knee
        kneex = knee_points.argmin()
        linthreshx = knee_points[kneex] + 1
        linthreshy = y_data[linthreshx] * basey
        linscaley = min(2, max(1, (knee_mag[kneex] / (basey * 2))))
    else:
        linthreshx = 1E2
        linthreshy = 1E2
        linscaley = 1
    logscale_kwargs = {
        'basey': basey,
        'nonposx': 'clip',
        'nonposy': 'clip',
        'linthreshy': linthreshy,
        'linthreshx': linthreshx,
        'linscalex': 1,
        'linscaley': linscaley,
    }
    #print(logscale_kwargs)
    return logscale_kwargs


def plot_pdf(data, draw_support=True, scale_to=None, label=None, color=0,
             nYTicks=3):
    fig = df2.gcf()
    ax = df2.gca()
    data = np.array(data)
    if len(data) == 0:
        warnstr = '[df2] ! Warning: len(data) = 0. Cannot visualize pdf'
        warnings.warn(warnstr)
        df2.draw_text(warnstr)
        return
    if len(data) == 1:
        warnstr = '[df2] ! Warning: len(data) = 1. Cannot visualize pdf'
        warnings.warn(warnstr)
        df2.draw_text(warnstr)
        return
    bw_factor = .05
    if isinstance(color, (int, float)):
        colorx = color
        line_color = plt.get_cmap('gist_rainbow')(colorx)
    else:
        line_color = color

    # Estimate a pdf
    data_pdf = estimate_pdf(data, bw_factor)
    # Get probability of seen data
    prob_x = data_pdf(data)
    # Get probability of unseen data data
    x_data = np.linspace(0, data.max(), 500)
    y_data = data_pdf(x_data)
    # Scale if requested
    if scale_to is not None:
        scale_factor = scale_to / y_data.max()
        y_data *= scale_factor
        prob_x *= scale_factor
    #Plot the actual datas on near the bottom perterbed in Y
    if draw_support:
        pdfrange = prob_x.max() - prob_x.min()
        perb   = (np.random.randn(len(data))) * pdfrange / 30.
        preb_y_data = np.abs([pdfrange / 50. for _ in data] + perb)
        ax.plot(data, preb_y_data, 'o', color=line_color, figure=fig, alpha=.1)
    # Plot the pdf (unseen data)
    ax.plot(x_data, y_data, color=line_color, label=label)
    if nYTicks is not None:
        yticks = np.linspace(min(y_data), max(y_data), nYTicks)
        ax.set_yticks(yticks)


def estimate_pdf(data, bw_factor):
    try:
        data_pdf = scipy.stats.gaussian_kde(data, bw_factor)
        data_pdf.covariance_factor = bw_factor
    except Exception as ex:
        print('[df2] ! Exception while estimating kernel density')
        print('[df2] data=%r' % (data,))
        print('[df2] ex=%r' % (ex,))
        raise
    return data_pdf


def interval_stats_plot(param2_stat_dict, fnum=None, pnum=(1, 1, 1), x_label='',
                        y_label='', title=''):
    r"""

    interval plot for displaying mean, range, and std

    Args:
        fnum (int):  figure number
        pnum (tuple):  plot number

    CommandLine:
        python -m plottool.plots --test-interval_stats_plot
        python -m plottool.plots --test-interval_stats_plot --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> import plottool as pt
        >>> # build test data
        >>> param2_stat_dict = {
        ...     0.5: dict([('max', 0.0584), ('min', 0.0543), ('mean', 0.0560), ('std', 0.00143),]),
        ...     0.6: dict([('max', 0.0593), ('min', 0.0538), ('mean', 0.0558), ('std', 0.00178),]),
        ...     0.7: dict([('max', 0.0597), ('min', 0.0532), ('mean', 0.0556), ('std', 0.00216),]),
        ...     0.8: dict([('max', 0.0601), ('min', 0.0525), ('mean', 0.0552), ('std', 0.00257),]),
        ...     0.9: dict([('max', 0.0604), ('min', 0.0517), ('mean', 0.0547), ('std', 0.00300),]),
        ...     1.0: dict([('max', 0.0607), ('min', 0.0507), ('mean', 0.0541), ('std', 0.00345),])
        ... }
        >>> fnum = None
        >>> pnum = (1, 1, 1)
        >>> title = 'p vs score'
        >>> x_label = 'p'
        >>> y_label = 'score diff'
        >>> result = interval_stats_plot(param2_stat_dict, fnum, pnum, x_label, y_label, title)
        >>> print(result)
        >>> ut.show_if_requested()
    """
    if fnum is None:
        fnum = df2.next_fnum()
    import six
    x_data = np.array(list(six.iterkeys(param2_stat_dict)))
    sortx = x_data.argsort()
    x_data_sort = x_data[sortx]
    from matplotlib import pyplot as plt
    # Prepare y data for boxplot
    y_data_keys = ['std', 'mean', 'max', 'min']
    y_data_dict = list(six.itervalues(param2_stat_dict))
    def get_dictlist_key(dict_list, key):
        return [dict_[key] for dict_ in dict_list]
    y_data_components = [get_dictlist_key(y_data_dict, key) for key in y_data_keys]
    # The stacking is pretty much not needed anymore, but whatever
    y_data_sort = np.vstack(y_data_components)[:, sortx]
    y_data_std_sort  = y_data_sort[0]
    y_data_mean_sort = y_data_sort[1]
    y_data_max_sort  = y_data_sort[2]
    y_data_min_sort  = y_data_sort[3]
    y_data_stdlow_sort  = y_data_mean_sort - y_data_std_sort
    y_data_stdhigh_sort = y_data_mean_sort + y_data_std_sort
    FIX_STD_SYMETRY = True
    if FIX_STD_SYMETRY:
        # Standard deviation is symetric where min and max are not.
        # To avoid weird looking plots clip the stddev fillbetweens
        # at the min and max
        #ut.embed()
        outlier_min_std = y_data_stdlow_sort  < y_data_min_sort
        outlier_max_std = y_data_stdhigh_sort > y_data_max_sort
        y_data_stdlow_sort[outlier_min_std]  =  y_data_min_sort[outlier_min_std]
        y_data_stdhigh_sort[outlier_max_std] =  y_data_max_sort[outlier_max_std]
    # Make firgure
    fig = df2.figure(fnum=fnum, pnum=pnum, doclf=False, docla=False)
    ax = plt.gca()
    # Plot max and mins
    ax.fill_between(x_data_sort, y_data_min_sort, y_data_max_sort, alpha=.2,
                    color='g', label='range')
    df2.append_phantom_legend_label('range', 'g', alpha=.2)
    # Plot standard deviations
    ax.fill_between(x_data_sort, y_data_stdlow_sort, y_data_stdhigh_sort,
                    alpha=.4, color='b', label='std')
    df2.append_phantom_legend_label('std', 'b', alpha=.4)
    # Plot means
    ax.plot(x_data_sort, y_data_mean_sort, 'o-', color='b', label='mean')
    df2.append_phantom_legend_label('mean', 'b', 'line')
    df2.show_phantom_legend_labels()
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    return fig
    #df2.dark_background()
    #plt.show()


def interval_line_plot(xdata, ydata_mean, y_data_std, color=[1, 0, 0],
                       label=None, marker='o', linestyle='-'):
    r"""
    Args:
        xdata (ndarray):
        ydata_mean (ndarray):
        y_data_std (ndarray):

    SeeAlso:
        pt.multi_plot (using the spread_list kwarg)

    CommandLine:
        python -m plottool.plots --test-interval_line_plot --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> xdata = [1, 2, 3, 4, 5, 6, 7, 8]
        >>> ydata_mean = [2, 3, 4, 3, 3, 2, 2, 2]
        >>> y_data_std = [1, 2, 1, 1, 3, 2, 2, 1]
        >>> result = interval_line_plot(xdata, ydata_mean, y_data_std)
        >>> print(result)
        >>> ut.show_if_requested()
    """
    xdata = np.array(xdata)
    ydata_mean = np.array(ydata_mean)
    y_data_std = np.array(y_data_std)
    y_data_max = ydata_mean + y_data_std
    y_data_min = ydata_mean - y_data_std
    ax = df2.gca()
    ax.fill_between(xdata, y_data_min, y_data_max, alpha=.2, color=color)
    ax.plot(xdata, ydata_mean, marker=marker, color=color, label=label, linestyle=linestyle)
    return


def plot_search_surface(known_nd_data, known_target_points, nd_labels,
                        target_label, fnum=None, pnum=None, title=None):
    r"""
    3D Function

    Args:
        known_nd_data (?): should be integral for now
        known_target_points (?):
        nd_labels (?):
        target_label (?):
        fnum (int):  figure number(default = None)

    Returns:
        ?: ax

    CommandLine:
        python -m plottool.plots --exec-plot_search_surface --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> known_nd_data = np.array([x.flatten() for x in np.meshgrid(*[np.linspace(-20, 20, 10).astype(np.int32), np.linspace(-20, 20, 10).astype(np.int32)])]).T
        >>> # complicated polynomial target
        >>> known_target_points = -.001 * known_nd_data.T[0] ** 4 + .25 * known_nd_data.T[1] ** 2 - .0005 * known_nd_data.T[1] ** 4 + .001 * known_nd_data.T[1] ** 3
        >>> nd_labels = ['big-dim', 'small-dim']
        >>> target_label = ['score']
        >>> fnum = 1
        >>> ax = plot_search_surface(known_nd_data, known_target_points, nd_labels, target_label, fnum)
        >>> ut.show_if_requested()
    """
    import plottool as pt
    from mpl_toolkits.mplot3d import Axes3D  # NOQA
    fnum = pt.ensure_fnum(fnum)
    print('fnum = %r' % (fnum,))
    #pt.figure(fnum=fnum, pnum=pnum, doclf=pnum is None, projection='3d')
    pt.figure(fnum=fnum, pnum=pnum, doclf=pnum is None)

    # Convert our non-uniform grid into a uniform grid using gcd
    def compute_interpolation_grid(known_nd_data, pad_steps=0):
        """ use gcd to get the number of steps to take in each dimension """
        import fractions
        ug_steps = [reduce(fractions.gcd, np.unique(x_).tolist()) for x_ in known_nd_data.T]
        ug_min   = known_nd_data.min(axis=0)
        ug_max   = known_nd_data.max(axis=0)
        ug_basis = [
            np.arange(min_ - (step_ * pad_steps), max_ + (step_ * (pad_steps + 1)), step_)
            for min_, max_, step_ in zip(ug_min, ug_max, ug_steps)
        ]
        ug_shape = tuple([basis.size for basis in ug_basis][::-1])
        # ig = interpolated grid
        unknown_nd_data = np.vstack([_pts.flatten() for _pts in np.meshgrid(*ug_basis)]).T
        return unknown_nd_data, ug_shape

    def interpolate_error(known_nd_data, known_target_points, unknown_nd_data):
        """
        References:
            docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.interpolate.griddata.html
        """
        #method = 'cubic'  # {'linear', 'nearest', 'cubic'}
        method = 'linear'  # {'linear', 'nearest', 'cubic'}
        import scipy as sp
        interpolated_targets = sp.interpolate.griddata(known_nd_data,
                                                       known_target_points,
                                                       unknown_nd_data,
                                                       method=method)
        #interpolated_targets[np.isnan(interpolated_targets)] = known_target_points.max() * 2
        interpolated_targets[np.isnan(interpolated_targets)] = known_target_points.min()
        return interpolated_targets

    # Interpolate uniform grid positions
    if len(known_nd_data.T) == 1 or ut.allsame(known_nd_data.T[1]):
        xdata = known_nd_data.T[0]
        ydata = known_target_points
        pt.plot(xdata, ydata)
        ax = pt.gca()
        if len(known_nd_data.T) == 2:
            ax.set_xlabel(
                nd_labels[0] + ' (const:' + nd_labels[1] + '=%r)' % (known_nd_data.T[1][0],))
        else:
            ax.set_xlabel(nd_labels[0])
        ax.set_ylabel(target_label)
    else:
        unknown_nd_data, ug_shape = compute_interpolation_grid(known_nd_data, 0 * 5)
        interpolated_error = interpolate_error(known_nd_data, known_target_points, unknown_nd_data)
        import matplotlib as mpl

        label_fontprop = mpl.font_manager.FontProperties(weight='light', size=8)
        title_fontprop = mpl.font_manager.FontProperties(weight='light', size=10)
        labelkw = dict(labelpad=1000, fontproperties=label_fontprop)
        titlekw = dict(fontproperties=title_fontprop)

        ax = pt.plot_surface3d(
            unknown_nd_data.T[0].reshape(ug_shape),
            unknown_nd_data.T[1].reshape(ug_shape),
            interpolated_error.reshape(ug_shape),
            xlabel=nd_labels[0],
            ylabel=nd_labels[1],
            zlabel=target_label,
            labelkw=labelkw,
            titlekw=titlekw,
            rstride=1, cstride=1,
            pnum=pnum,
            #cmap=pt.plt.get_cmap('jet'),
            cmap=pt.plt.get_cmap('coolwarm'),
            #wire=True,
            #mode='wire',
            title=title,
            mode='surface',
            alpha=.7,
            contour=True,
            #mode='contour',
            #norm=pt.mpl.colors.Normalize(0, 1),
            #shade=False,
            #dark=False,
        )
        #ax.scatter(known_nd_data.T[0], known_nd_data.T[1], known_target_points, s=100, c=pt.YELLOW)
        ax.scatter(known_nd_data.T[0], known_nd_data.T[1], known_target_points, s=10, c=pt.YELLOW)
        ax.set_aspect('auto')
        #given_data_dims = [0]
        #assert len(given_data_dims) == 1, 'can only plot 1 given data dim'
        #xdim = given_data_dims[0]
        #xdim = 0
        #ydim = (xdim + 1) % (len(known_nd_data.T))
        #known_nd_min = known_nd_data.min(axis=0)
        #known_nd_max = known_nd_data.max(axis=0)
        #xmin, xmax = known_nd_min[xdim], known_nd_max[xdim]
        #ymin, ymax = known_nd_min[ydim], known_nd_max[ydim]
        #zmin, zmax = known_target_points.min(), known_target_points.max()

        ##ax.set_xlim(xmin, xmax * 1.05)
        ##ax.set_ylim(ymin, ymax * 1.05)
        ##ax.set_zlim(zmin, zmax * 1.05)
        ##ax.set_xlim(0, xmax + 1)
        ##ax.set_ylim(0, ymax + 1)
        ##ax.set_zlim(0, zmax + 1)
        for label in ax.get_xticklabels():
            label.set_fontsize(6)
        for label in ax.get_yticklabels():
            label.set_fontsize(6)
        for label in ax.get_zticklabels():
            label.set_fontsize(6)
        #import matplotlib.ticker as mtick
        #ax.zaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))
        #ax.zaxis.set_major_formatter(mtick.FormatStrFormatter('%d'))
        #ax.xaxis.set_major_formatter(mtick.FormatStrFormatter('%d'))
        #ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%d'))
    return ax


def draw_timedelta_pie(timedeltas, bins=None, fnum=None, pnum=(1, 1, 1), label=''):
    r"""
    Args:
        timedeltas (list):
        bins (None): (default = None)

    CommandLine:
        python -m plottool.plots --exec-draw_timedelta_pie --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> timedeltas = np.array([    1.,    14.,    17.,    34.,     4.,    36.,    34.,     2.,
        ...                         3268.,    34., np.nan,    33.,     5.,     2.,    16.,     5.,
        ...                           35.,    64.,   299.,    35.,     2.,     5.,    34.,    12.,
        ...                            1.,     8.,     6.,     7.,    11.,     5.,    46.,    47.,
        ...                           22.,     3.,  np.nan,    11.], dtype=np.float64) ** 2
        >>> bins = None
        >>> result = draw_timedelta_pie(timedeltas, bins)
        >>> ut.show_if_requested()
    """
    import datetime
    xdata = timedeltas[~np.isnan(timedeltas)]
    numnan = len(timedeltas) - len(xdata)
    max_time = xdata.max()

    if bins is None:
        bins = [
            datetime.timedelta(seconds=0).total_seconds(),
            datetime.timedelta(minutes=1).total_seconds(),
            datetime.timedelta(hours=1).total_seconds(),
            datetime.timedelta(days=1).total_seconds(),
            datetime.timedelta(weeks=1).total_seconds(),
            datetime.timedelta(days=356).total_seconds(),
            #np.inf,
            max(datetime.timedelta(days=356 * 10).total_seconds(), max_time + 1),
        ]

    freq = np.histogram(xdata, bins)[0]
    timedelta_strs = [ut.get_timedelta_str(datetime.timedelta(seconds=b), exclude_zeros=True)
                      for b in bins]
    bin_labels = [l + ' - ' + h for l, h in ut.iter_window(timedelta_strs)]
    bin_labels[-1] = '> 1 year'
    bin_labels[0] = '< 1 minute'

    WITH_NAN = True
    if WITH_NAN:
        freq = np.append(freq, [numnan])
        bin_labels += ['nan']

    # Convert to percent
    fnum = None
    import plottool as pt

    fnum = pt.ensure_fnum(fnum)
    pt.figure(fnum=fnum)
    bin_labels[0]

    colors = pt.distinct_colors(len(bin_labels))
    if WITH_NAN:
        colors[-1] = pt.GRAY
    #xints = np.arange(len(bin_labels))

    pt.figure(fnum=fnum, pnum=pnum)
    mask = freq > 0
    masked_freq   = freq.compress(mask, axis=0)
    size = masked_freq.sum()
    masked_lbls   = ut.compress(bin_labels, mask)
    masked_colors = ut.compress(colors, mask)
    explode = [0] * len(masked_freq)
    masked_percent = (masked_freq * 100 / size)
    pt.plt.pie(masked_percent, explode=explode, autopct='%1.1f%%',
               labels=masked_lbls, colors=masked_colors)
    #ax = pt.gca()
    pt.set_xlabel(label + '\nsize=%d' % (size,))
    pt.gca().set_aspect('equal')


def word_histogram2(text_list, weight_list=None, **kwargs):
    """
    Args:
        text_list (list):

    References:
        stackoverflow.com/questions/17430105/autofmt-xdate-deletes-x-axis-labels-of-all-subplots

    CommandLine:
        python -m plottool.plots --exec-word_histogram2 --show --lightbg

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> text_list = []
        >>> item_list = text_list = ['spam', 'eggs', 'ham', 'jam', 'spam', 'spam', 'spam', 'eggs', 'spam']
        >>> weight_list = None
        >>> #weight_list = [.1, .2, .3, .4, .5, .5, .4, .3, .1]
        >>> #text_list = [x.strip() for x in ut.lorium_ipsum().split()]
        >>> result = word_histogram2(text_list, weight_list)
        >>> ut.show_if_requested()
    """
    import plottool as pt
    text_hist = ut.dict_hist(text_list, weight_list=weight_list)
    text_vals = list(text_hist.values())
    sortx = ut.list_argsort(text_vals)[::-1]
    bin_labels = ut.take(list(text_hist.keys()), sortx)
    freq = np.array(ut.take(text_vals, sortx))
    xints = np.arange(len(bin_labels))

    width = .95
    ymax = freq.max() if len(freq) > 0 else 0
    print('ymax = %r' % (ymax,))

    if len(freq) == 0:
        freq_max = 1
    else:
        freq_max = freq.max()

    color = plt.cm.get_cmap('inferno')((freq / freq_max) * .6 + .3)
    pt.multi_plot(xints, [freq], xpad=0, ypad_high=.5,
                  #kind='plot',
                  kind='bar',
                  color=color,
                  width=width,
                  #xtick_rotation=90,
                  #num_yticks=ymax + 1,
                  xticklabels=bin_labels, xmin=-1, xmax=len(xints),
                  transpose=True,
                  ymax=ymax,
                  ylabel='Freq',
                  xlabel=kwargs.pop('xlabel', 'Word'),
                  **kwargs)
    #ax.autofmt_xdate()
    #plt.setp(plt.xticks()[1], rotation=30, ha='right')
    #pt.gcf().autofmt_xdate()


def draw_time_histogram(unixtime_list, **kwargs):
    import plottool as pt
    freq, bins = np.histogram(unixtime_list, bins=30)

    #meanshift = sklearn.cluster.MeanShift()
    #meanshift.fit(unixtime_list)

    bin_labels = [ut.unixtime_to_datetimeobj(b).strftime('%Y/%m/%d') for b in bins]
    xints = np.arange(len(bin_labels))
    freq_list = [np.array(freq, dtype=np.int)]
    width = .95

    #num_yticks = 1 + max([
    #    _freq.max() if len(_freq) > 0 else 0
    #    for _freq in freq_list])
    pt.multi_plot(xints, freq_list, xpad=0, ypad_high=.5,
                  #kind='plot',
                  kind='bar',
                  width=width,
                  xtick_rotation=30,
                  #num_yticks=num_yticks,
                  xticklabels=bin_labels, xmin=-1, xmax=len(xints),
                  #transpose=True,
                  #ymax=num_yticks - 1,
                  ylabel='Freq', xlabel='Time', **kwargs)
    pass


def draw_histogram(bin_labels, bin_values, xlabel='',  ylabel='Freq',
                   xtick_rotation=0, transpose=False,
                   **kwargs):
    r"""
    Args:
        bin_labels (?):
        bin_values (?):
        xlabel (unicode): (default = u'')
        ylabel (unicode): (default = u'Freq')
        xtick_rotation (int): (default = 0)
        transpose (bool): (default = False)

    Kwargs:
        fnum, pnum, kind, spread_list, title, titlesize, labelsize,
        legendsize, ticksize, num_xticks, num_yticks, yticklabels,
        xticklabels, ytick_rotation, xpad, ypad, xpad_factor, ypad_factor,
        ypad_high, ypad_low, xpad_high, xpad_low, xscale, yscale, legend_loc,
        legend_alpha, use_darkbackground, lightbg

    CommandLine:
        python -m plottool.plots --exec-draw_histogram --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> bin_labels = ['label1', 'label2']
        >>> bin_values = [.4, .6]
        >>> xlabel = ''
        >>> ylabel = 'Freq'
        >>> xtick_rotation = 0
        >>> transpose = False  # True
        >>> kwargs = dict(use_darkbackground=False)
        >>> result = draw_histogram(bin_labels, bin_values, xlabel, ylabel, xtick_rotation, transpose, **kwargs)
        >>> print(result)
        >>> ut.show_if_requested()
    """
    import plottool as pt
    xints = np.arange(len(bin_labels))
    width = .95
    kwargs = kwargs.copy()
    kwargs['autolabel'] = kwargs.get('autolabel', True)
    pt.multi_plot(xints, [bin_values], xpad=0, ypad_high=.5,
                  #kind='plot',
                  kind='bar',
                  width=width,
                  xtick_rotation=xtick_rotation,
                  #num_yticks=num_yticks,
                  xticklabels=bin_labels, xmin=-1, xmax=len(xints),
                  transpose=transpose,
                  #ymax=num_yticks - 1,
                  ylabel=ylabel, xlabel=xlabel, **kwargs)


def draw_time_distribution(unixtime_list):
    import vtool as vt
    import plottool as pt
    if len(unixtime_list) > 0:
        unixtime_domain = np.linspace(np.nanmin(unixtime_list), np.nanmax(unixtime_list), 1000)
        unixtime_pdf = vt.estimate_pdf(unixtime_list)
        unixtime_prob = unixtime_pdf.evaluate(unixtime_domain)
        xdata = [ut.unixtime_to_datetimeobj(unixtime) for unixtime in unixtime_domain]
    else:
        unixtime_prob = []
        xdata = []

    fnum = pt.ensure_fnum(None)
    pt.plot_probabilities([unixtime_prob], ['time'], xdata=xdata, fill=True,
                          use_legend=False, fnum=fnum, remove_yticks=True)
    #freq, bins = np.histogram(unixtime_list, bins=30, normed=True)
    #xints = np.arange(len(xdata))
    #ut.embed()
    #pt.multi_plot(xints, [freq],
    #              fnum=fnum,
    #              kind='bar', dark_background=False)
    #xtick_rotation=30,
    #num_yticks=num_yticks,
    #xticklabels=bin_labels,
    #xmin=-1,
    #xmax=len(xints),
    #transpose=True,
    #ymax=num_yticks - 1,
    #ylabel='Freq',
    #xlabel='Time',
    #**kwargs)


def wordcloud(text, fnum=None, pnum=None):
    """
    References:
        bioinfoexpert.com/?p=592
        sudo pip install git+git://github.com/amueller/word_cloud.git

    Args:
        text (str):
        fnum (int):  figure number(default = None)
        pnum (tuple):  plot number(default = None)

    CommandLine:
        python -m plottool.plots --exec-wordcloud --show
        python -m plottool.plots --exec-wordcloud --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.plots import *  # NOQA
        >>> text = '''
                Normally, Frost-Breath-type cards are only good in aggressive decks,
                but add an Eldrazi Scion into the mix and that all changes. I'm not
                adverse to playing a card that ramps my mana, can trade for an x/1, and
                does so while keeping me alive. I still would rather be beating down if
                I'm including this in my deck, but I think it does enough different
                things at a good rate that you are more likely to play it than not.
                Cards that swing a race this drastically are situationally awesome, and
                getting the Eldrazi Scion goes a long way toward mitigating the cost of
                drawing this when you aren't in a race (which is the reason
                non-aggressive decks tend to avoid this effect).
            '''
        >>> fnum = None
        >>> pnum = None
        >>> result = wordcloud(text, fnum, pnum)
        >>> ut.show_if_requested()
        >>> print(result)
    """
    import plottool as pt
    from wordcloud import WordCloud
    fnum = pt.ensure_fnum(fnum)
    pt.figure(fnum=fnum, pnum=pnum)
    if len(text) > 0:
        _wc = WordCloud(background_color='black' if is_default_dark_bg() else 'white')
        wordcloud = _wc.generate(text)
        pt.plt.imshow(wordcloud)
    else:
        pt.imshow_null('NO WORDCLOUD DATA')
    pt.plt.axis('off')


if __name__ == '__main__':
    """
    CommandLine:
        python -m plottool.plots
        python -m plottool.plots --allexamples
        python -m plottool.plots --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
