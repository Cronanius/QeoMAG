"""Regression checks using the real function bodies without GUI/GIS imports.
Run: python -B -m unittest discover -s tests -v
Desktop integration still requires the application dependencies.
"""
import ast
import contextlib
import copy
import io
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def functions(filename, class_name=None):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    nodes = tree.body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    namespace = {'np': np, 'math': math, 'traceback': SimpleNamespace(print_exc=lambda: None)}
    exec(compile(ast.Module(body=[n for n in nodes if isinstance(n, ast.FunctionDef)], type_ignores=[]), filename, 'exec'), namespace)
    return namespace

MATH = functions('QeoMATH.py')
GUI = functions('QeoMAG.py', 'MainWindow')
PLOT = functions('QeoMAG.py', 'dataPlot')

def gem_rows():
    headers = ['time', 'nT'] + ['c' + str(i) for i in range(2, 20)]
    headers[14:16] = ['utmE', 'utmN']
    headers[19] = 'laser'
    row = ['1'] * 20
    row[16], row[18] = '123.45', '15.01'
    #Preserve the existing two footer records before the end marker.
    return [headers, row, row.copy(), ['footer'], ['footer'], ['end']]

class StabilizationTests(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_conversion_preserves_all_samples(self):
        for rows in ([['time', 'nT'], ['1', '100'], ['2', '200']],
                     [['1', '100'], ['2', '200']], [[1, 100], [2, 200]]):
            with self.subTest(rows=rows):
                np.testing.assert_array_equal(MATH['dataConvert'](rows), [[1, 100], [2, 200]])

    def test_conversion_rejects_empty_and_malformed_data(self):
        for rows in ([], [[]], [['time']], [['time', 'nT'], ['1']], [['1', 'bad']], [['1'], []]):
            with self.subTest(rows=rows):
                self.assertEqual(MATH['dataConvert'](rows), 'False')

    def test_cleanup_removes_adjacent_bad_rows_without_mutating_input(self):
        raw = gem_rows()
        raw[2:2] = [[], [], ['bad'], ['bad']]
        before = copy.deepcopy(raw)
        clean = MATH['dataClean'](raw, 'GEMsys', '', '')
        self.assertEqual(len(clean), 3)
        self.assertEqual(raw, before)
        clean[1][0] = 'changed'
        self.assertEqual(raw, before)

    def test_cleanup_failure_preserves_input(self):
        raw = gem_rows()
        raw[1][18] = '15?'
        before = copy.deepcopy(raw)
        with self.assertRaises(KeyError): MATH['dataClean'](raw, 'GEMsys', '', '')
        self.assertEqual(raw, before)

    def window(self):
        return SimpleNamespace(localData=np.array([[5., 6.]]), dataHeaders=['utmE', 'utmN'],
            masterData=np.array([[]]), masterHeaders=[], masterDataType=None,
            dataType='GEMsys', isArrayFulfilled=True, masterArrayLabelSetText=Mock(),
            datafilename='test', currentCRS='', targetCRS='', listData=gem_rows(),
            headingBox=SimpleNamespace(text=lambda: '90'),
            headingToleranceBox=SimpleNamespace(text=lambda: '3'),
            dateCollectedBox=SimpleNamespace(text=lambda: '20260911'),
            pushCRS=Mock(), ledToGreen=Mock(), writeDataToTextWidget=Mock(),
            plotRotatedData=Mock(), toggleWriteToText=False)

    def test_master_owns_data_and_headers(self):
        w = self.window()
        GUI['loadToMasterArray'](w)
        w.localData[0, 0] = 99
        w.dataHeaders[0] = 'other'
        np.testing.assert_array_equal(w.masterData, [[5, 6]])
        self.assertEqual(w.masterHeaders, ['utmE', 'utmN'])

    def test_master_rejects_different_schema_or_sensor(self):
        for change in ('headers', 'sensor'):
            w = self.window()
            GUI['loadToMasterArray'](w)
            if change == 'headers': w.dataHeaders.reverse()
            else: w.dataType = 'MagArrow2'
            GUI['loadToMasterArray'](w)
            self.assertEqual(w.masterData.shape, (1, 2))
            self.assertEqual(w.masterLoadSuccess, 'Upload Error')

    def test_master_appends_compatible_data(self):
        w = self.window()
        GUI['loadToMasterArray'](w)
        GUI['loadToMasterArray'](w)
        np.testing.assert_array_equal(w.masterData, [[5, 6], [5, 6]])

    def test_auto_failure_preserves_dataset_and_does_not_plot(self):
        for stage in ('dataClean', 'headingPurge', 'basicPurge', 'headingRotationTransform', 'addDateChannel'):
            w = self.window()
            old = w.localData
            raw = copy.deepcopy(w.listData)
            qm = SimpleNamespace(**{name: value for name, value in MATH.items() if callable(value)})
            setattr(qm, stage, Mock(side_effect=ValueError('test failure')))
            with patch.dict(GUI, qm=qm): GUI['autoEvaluation'](w)
            self.assertIs(w.localData, old)
            self.assertEqual(w.dataHeaders, ['utmE', 'utmN'])
            self.assertEqual(w.listData, raw)
            w.plotRotatedData.assert_not_called()
            w.ledToGreen.assert_not_called()

    def test_auto_success_uses_current_signatures(self):
        w = self.window()
        qm = SimpleNamespace(**{name: value for name, value in MATH.items() if callable(value)})
        with patch.dict(GUI, qm=qm): GUI['autoEvaluation'](w)
        self.assertEqual(w.localData.shape[1], len(w.dataHeaders))
        self.assertIn('date', w.dataHeaders)
        w.plotRotatedData.assert_called_once()
        w.ledToGreen.assert_called_once()

    def test_auto_invalid_inputs_and_unsupported_sensor_do_not_process(self):
        for value in ('', 'nan', '361'):
            w = self.window()
            w.headingBox.text = lambda: value
            GUI['autoEvaluation'](w)
            w.pushCRS.assert_not_called()
        w = self.window()
        w.dataType = 'MagArrow2'
        GUI['autoEvaluation'](w)
        w.pushCRS.assert_not_called()

    def test_manual_cleanup_sets_ready_after_success(self):
        w = self.window()
        with patch.dict(GUI, qm=SimpleNamespace(**MATH)): GUI['dataCleanConnect'](w)
        self.assertEqual(w.localData.shape, (2, 20))
        w.ledToGreen.assert_called_once()

    def test_master_plot_and_unselected_plot_cannot_delete(self):
        for editable, extents in ((False, (0, 10, 0, 10)), (True, None)):
            w = SimpleNamespace(editable=editable, rectExtents=extents)
            PLOT['ondelete'](w, SimpleNamespace(key='delete'))

    def test_plot_preserves_selected_sensor(self):
        w = SimpleNamespace(plotIt=Mock())
        PLOT['__init__'](w, np.ones((1, 3)), ['utmE', 'utmN', 'nT'], 'GEMsys')
        self.assertEqual(w.instrumentType, 'GEMsys')

if __name__ == '__main__':
    unittest.main()
