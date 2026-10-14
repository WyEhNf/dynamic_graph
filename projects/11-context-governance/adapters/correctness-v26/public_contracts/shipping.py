import copy
import unittest
import solution
import config
class PublicContract(unittest.TestCase):
    def test_configured_boundary_and_negative(self):
        for weight in (0,max(0,config.FREE_FROM_KG-1),config.FREE_FROM_KG,config.FREE_FROM_KG+2):
            self.assertEqual(solution.shipping_fee(weight),0 if weight>=config.FREE_FROM_KG else config.BASE_FEE+config.PER_KG*weight)
        with self.assertRaises(ValueError): solution.shipping_fee(-1)
