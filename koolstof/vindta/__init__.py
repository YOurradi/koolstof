"""Import and parse the data files produced by the Marianda VINDTA 3C."""

__all__ = ['plot']
from . import plot

import re
import numpy as np
import pandas as pd

def addfunccols(df, func, *args):
    """Add results of `apply()` to a DataFrame as new columns."""
    return pd.concat([df, df.apply(lambda x: func(x, *args), axis=1)], axis=1,
                     sort=False)

def _dbs_datetime(dbsx):
    """Convert date and time from .dbs file into a NumPy datetime."""
    dspl = dbsx['date'].split('/')
    return pd.Series({'analysisdate':
        np.datetime64('-'.join(('20'+dspl[2], dspl[0], dspl[1])) + 'T' +
                      dbsx['time'])})

def read_dbs(filepath):
    """Import a .dbs file as a DataFrame."""
    headers = np.genfromtxt(filepath, delimiter='\t', dtype=str, max_rows=1)
    dbs = pd.read_table(filepath, header=0, names=headers, usecols=headers)
    dbs['filepath'] = filepath
    dbs = addfunccols(dbs, _dbs_datetime)
    return dbs

def read_logfile(filepath, methods=['3C standard']):
    """Import a logfile.bak as a DataFrame."""
    # Compile regexs for reading logfile
    re_method = re.compile(r'(' + r'|'.join(methods) +
                           r')\.mth run started '.format(methods))
    re_datetime = re.compile(r'started (\d{2})/(\d{2})/(\d{2})  (\d{2}):(\d{2})')
    re_bottle = re.compile(r'(bottle)?\t([^\t]*)\t')
    re_crm = re.compile(r'CRM\t([^\t]*)\t')
    re_increments = re.compile(r'(\d*)\t(\d*)\t(\d*)\t')
    # Import text from logfile
    with open(filepath, 'r') as f:
        logf = f.read().splitlines()
    # Initialise arrays
    logdf = {
        'logfileline': [],
        'analysisdate': np.array([], dtype='datetime64'),
        'bottle': [],
        'table': [],
        'totalcounts': [],
        'runtime': [],
        'method': [],
    }
    # Parse file line by line
    for i, line in enumerate(logf):
        if re_method.match(line):
            logdf['logfileline'].append(i)
            logdf['method'].append(re_method.findall(line)[0])
            # Get analysis date and time
            ldt = re_datetime.findall(line)[0]
            ldt = np.datetime64('{}-{}-{}T{}:{}'.format(
                '20'+ldt[2], ldt[0], ldt[1], ldt[3], ldt[4]))
            logdf['analysisdate'] = np.append(logdf['analysisdate'], ldt)
            # Get sample name
            lbot = 0
            if re_bottle.match(logf[i+1]):
                lbot = re_bottle.findall(logf[i+1])[0][1]
            elif re_crm.match(logf[i+1]):
                lbot = re_crm.findall(logf[i+1])[0]
            elif logf[i+1] == 'other':
                lbot = 'other_{}'.format(i+1)
            assert(type(lbot) == str), \
                'Logfile line {}: bottle name not found!'.format(i+1)
            logdf['bottle'].append(lbot)
            # Get coulometer data
            jdict = {'minutes': [0.0], 'counts': [0.0], 'increments': [0.0]}
            j = 4
            while re_increments.match(logf[i+j].strip()):
                jinc = re_increments.findall(logf[i+j].strip())[0]
                jdict['minutes'].append(float(jinc[0]))
                jdict['counts'].append(float(jinc[1]))
                jdict['increments'].append(float(jinc[2]))
                j += 1
            jdict = {k: np.array(v) for k, v in jdict.items()}
            logdf['table'].append(jdict)
            logdf['totalcounts'].append(jdict['counts'][-1])
            logdf['runtime'].append(j - 4.0)
    # Convert lists to arrays and put logfile into DataFrame
    logdf = {k: np.array(v) for k, v in logdf.items()}
    return pd.DataFrame(logdf)

def _logfile2dbs(x, logfile):
    if x.bottle in logfile.bottle.values:
        xix = np.where((x.bottle == logfile.bottle) &
                       (x.analysisdate == logfile.analysisdate))[0]
        assert len(xix) == 1, \
            ('More than one (or no) name/date matches found between dbs and ' +
              'logfile! @ dbs iloc {}'.format(x.name))
        xix = xix[0]
    else:
        xix = np.nan
    return pd.Series({'logfile_iloc': xix})

def logfile2dbs(dbs, logfile):
    """Get index in `logfile` corresponding to each row in `dbs`."""
    dbs = addfunccols(dbs, _logfile2dbs, logfile)
    return dbs

def _get_blanks(x, logfile, usefrom):
    assert 'logfile_iloc' in x.index, \
        'You must first run `ks.vindta.logfile2dbs()`.'
    assert usefrom > 0, '`usefrom` must be positive.'
    lft = logfile.iloc[x.logfile_iloc].table
    L = lft['minutes'] >= usefrom
    blank = np.mean(lft['increments'][L])
    return pd.Series({'blank_here': blank})

def get_blanks(dbs, logfile, usefrom=6):
    """Get sample-by-sample blank values."""
    dbs = addfunccols(dbs, _get_blanks, logfile, usefrom)
    return dbs
