# from ddt import ddt, data
#
# from app import helpers
# from tests.base import TestCase
#
#
# @ddt
# class Test(TestCase):
#     @data((70, 100, 60.0, '#e05d44'),
#           (70, 100, 70.0, '#e05d44'),
#           (70, 100, 80.0, '#efa41b'),
#           (70, 100, 90.0, '#a3b114'),
#           (70, 100, 100.0, '#4c1'),
#           (70, 100, 99.99999, '#48cc10'))
#     def test_coverage_to_color(self, (r1, r2, cov, result)):
#         assert helpers.coverage_to_color(r1, r2)(cov).hex == result
#         assert helpers.coverage_to_color(r1, r2)(float(cov)).hex == result
#         assert helpers.coverage_to_color(r1, r2)(str(cov)).hex == result
#         assert helpers.coverage_to_color(r1, r2)(str(cov)+'000').hex == result

from src.helpers.color import coverage_to_color

def test_color():
    assert coverage_to_color(70, 100)(60.0).hex == '#e05d44'
