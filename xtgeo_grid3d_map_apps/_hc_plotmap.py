# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import sys
import logging
import getpass
from time import localtime, strftime
import numpy as np
from collections import OrderedDict

from xtgeo.common import XTGeoDialog
from xtgeo.surface import RegularSurface
from xtgeo.xyz import Polygons

xtg = XTGeoDialog()

logger = xtg.functionlogger(__name__)


def check_mapsettings(config, grd):
    """Check if given map settings looks sane compared with actual grid

    It returns a 'pscore' which is a measure of problems. Everything
    greater than 0 is a problem, and > 0 is critical
    """

    ggeom = grd.get_geometrics(return_dict=True, cellcenter=False)

    # Compute the geometrics values from the mapsettings:
    cfmp = config['mapsettings']
    xmin = cfmp['xori']  # since unrotated map
    xmax = xmin + (cfmp['ncol'] - 1) * cfmp['xinc']
    ymin = cfmp['yori']  # since unrotated map
    ymax = ymin + (cfmp['nrow'] - 1) * cfmp['yinc']

    # problems score pscore is 0 if all is OK
    pscore = 0
    if xmax < ggeom['xmin'] or xmin > ggeom['xmax']:
        pscore += 10

    if ymax < ggeom['ymin'] or ymin > ggeom['ymax']:
        pscore += 10

    return pscore


def do_hc_mapping(config, initd, hcpfzd, zonation, zoned):
    """Do the actual map gridding, for zones and groups of zones"""

    layerlist = (1, zonation.shape[2])

    mapzd = OrderedDict()

    for zname, zrange in zoned.items():

        usezonation = zonation
        usezrange = zrange

        # in case of super zones:
        if isinstance(zrange, list):
            usezonation = zonation.copy()
            usezonation[:, :, :] = 0
            logger.debug(usezonation)
            for zr in zrange:
                logger.debug('ZR is {}'.format(zr))
                usezonation[zonation == zr] = 888

            usezrange = 888

        if zname == 'all':
            usezonation = zonation.copy()
            usezonation[:, :, :] = 999
            usezrange = 999

            if config['computesettings']['all'] is not True:
                logger.info('Skip <{}> (cf. computesettings: all)'.
                            format(zname))
                continue
        else:
            if config['computesettings']['zone'] is not True:
                logger.info('Skip <{}> (cf. computesettings: zone)'.
                            format(zname))
                continue

        mapd = dict()

        for date, hcpfz in hcpfzd.items():
            logger.info('Mapping <{}> for date <{}> ...'.format(zname, date))

            ncol = config['mapsettings'].get('ncol')
            nrow = config['mapsettings'].get('nrow')

            xmap = RegularSurface(
                xori=config['mapsettings'].get('xori'),
                yori=config['mapsettings'].get('yori'),
                ncol=config['mapsettings'].get('ncol'),
                nrow=config['mapsettings'].get('nrow'),
                xinc=config['mapsettings'].get('xinc'),
                yinc=config['mapsettings'].get('yinc'),
                values=np.zeros((ncol, nrow))
            )

            xmap.hc_thickness_from_3dprops(xprop=initd['xc'],
                                           yprop=initd['yc'],
                                           hcpfzprop=hcpfz,
                                           zoneprop=usezonation,
                                           zone_minmax=(usezrange, usezrange),
                                           layer_minmax=layerlist)

            filename = _hc_filesettings(config, zname, date)
            xtg.say('Map file to {}'.format(filename))
            xmap.to_file(filename)

            mapd[date] = xmap

        mapzd[zname] = mapd

    # return the map dictionary: {zname: {date1: map_object1, ...}}

    logger.debug('The map objects: {}'.format(mapzd))

    return mapzd


def do_hc_plotting(config, mapzd):
    """Do plotting via matplotlib to PNG (etc) (if requested)"""

    xtg.say('Plotting ...')

    for zname, mapd in mapzd.items():

        for date, xmap in mapd.items():

            plotfile = _hc_filesettings(config, zname, date, mode='plot')

            pcfg = _hc_plotsettings(config, zname, date)

            xtg.say('Plot to {}'.format(plotfile))

            usevrange = pcfg['valuerange']
            if len(date) > 10:
                usevrange = pcfg['diffvaluerange']

            faults = None
            if pcfg['faultpolygons'] is not None:
                try:
                    fau = Polygons(pcfg['faultpolygons'], fformat='zmap')
                    faults = {'faults': fau}
                except Exception as e:
                    xtg.say(e)
                    faults = None

            xmap.quickplot(filename=plotfile,
                           title=pcfg['title'],
                           infotext=pcfg['infotext'],
                           xlabelrotation=pcfg['xlabelrotation'],
                           minmax=usevrange,
                           colortable=pcfg['colortable'],
                           faults=faults)


def _hc_filesettings(config, zname, date, mode='map'):
    """Local function for map or plot file name"""

    delim = '--'

    if config['output']['lowercase']:
        zname = zname.lower()

    phase = config['computesettings']['mode']

    if config['output']['tag']:
        tag = config['output']['tag'] + '_'
    else:
        tag = ''

    date = date.replace('-', '_')

    path = config['output']['mapfolder'] + '/'
    xfil = (zname + delim + tag + phase + 'thickness' + tag + delim +
            str(date) + '.gri')

    if mode == 'plot':
        path = config['output']['plotfolder'] + '/'
        xfil = xfil.replace('gri', 'png')

    return path + xfil


def _hc_plotsettings(config, zname, date):
    """Local function for plot additional info."""

    phase = config['computesettings']['mode']
    rock = 'net'
    if config['computesettings']['mode'] == 'dz_only':
        rock = 'bulk'

    title = (phase.capitalize() + ' ' + rock + ' thickness for ' +
             zname + ' ' + date)

    showtime = strftime("%Y-%m-%d %H:%M:%S", localtime())
    infotext = getpass.getuser() + ' ' + showtime
    if config['output']['tag']:
        infotext = infotext + ' (tag: ' + config['output']['tag'] + ')'

    xlabelrotation = None
    valuerange = (None, None)
    diffvaluerange = (None, None)
    colortable = 'rainbow'
    xlabelrotation = 0
    fpolyfile = None

    if 'xlabelrotation' in config['plotsettings']:
        xlabelrotation = config['plotsettings']['xlabelrotation']

    if 'valuerange' in config['plotsettings']:
        valuerange = tuple(config['plotsettings']['valuerange'])

    if 'diffvaluerange' in config['plotsettings']:
        diffvaluerange = tuple(config['plotsettings']['diffvaluerange'])

    if 'faultpolygons' in config['plotsettings']:
        fpolyfile = config['plotsettings']['faultpolygons']

    # there may be individual plotsettings for zname
    if zname is not None and zname in config['plotsettings']:

        zfg = config['plotsettings'][zname]

        if 'valuerange' in zfg:
            valuerange = tuple(zfg['valuerange'])

        if 'diffvaluerange' in zfg:
            diffvaluerange = tuple(zfg['diffvaluerange'])

        if 'xlabelrotation' in zfg:
            xlabelrotation = zfg['xlabelrotation']

        if 'colortable' in zfg:
            colortable = zfg['colortable']

        if 'faultpolygons' in zfg:
            fpolyfile = zfg['faultpolygons']

    # assing settings to a dictionary which is returned
    plotcfg = {}
    plotcfg['title'] = title
    plotcfg['infotext'] = infotext
    plotcfg['valuerange'] = valuerange
    plotcfg['diffvaluerange'] = diffvaluerange
    plotcfg['xlabelrotation'] = xlabelrotation
    plotcfg['colortable'] = colortable
    plotcfg['faultpolygons'] = fpolyfile

    return plotcfg
