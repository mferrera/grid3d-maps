import os
import pytest

from xtgeo.common import XTGeoDialog

import xtgeo_utils2.avghc.grid3d_average_map as xxx

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__)

if not xtg.testsetup():
    raise SystemExit

td = xtg.tmpdir
testpath = xtg.testpath

skiplargetest = pytest.mark.skipif(xtg.bigtest is False,
                                   reason="Big tests skip")

# =============================================================================
# Do tests
# =============================================================================


def test_average_map2a():
    """Test HC thickness with YAML config example 2a ECL based with filters"""
    dump = os.path.join(td, 'avg2a.yml')
    xxx.main(['--config', 'tests/yaml/avg2a.yml', '--dump', dump])