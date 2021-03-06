import unittest
import random
import sys
sys.path.append('/Users/mozumder/JupyterHub/Daily_Work_bin')
from ImpurityDataExtraction.ImpData import CoupleImpurityData, MultiImpuritiesData
from aiida.orm import load_node
from aiida import load_profile
profile = load_profile()
import pandas as pd


class TestImpurityData(unittest.TestCase):

    # Input data node [2,3,4] in group 102
    data_list_1 = ['22d72273-676a-4243-9d41-f20273d7941b',
                   '5f8bf3a8-fc7d-45d5-8140-9a1e7f566207',
                   '7ce9e9dc-3891-4922-88ae-0a63e5893026']
    data_list_1 = [load_node(i) for i in data_list_1]

    # Input data node [2,3,4] in group 104
    data_list_2 = ['967ecb19-75b9-4f72-9ef8-04da8b7376f0',
                   'f3669dc2-a94d-4eee-962e-2720dcd444cd',
                   'cc2de321-52ce-482d-962d-76bbf0ed7d84']
    data_list_2 = [load_node(i) for i in data_list_2]
 
    # Input data node [2,3,4] in group 115
    data_list_3 = ['f53c729d-df31-4b37-b8b0-28b313b95af3',
                   '9904cc5f-fa09-4752-ad4c-579839e09c69',
                   'e596fb38-eef3-4975-b040-737b797f050e']
    data_list_3 = [load_node(i) for i in data_list_3]
    
    # Result validation nodes
    node_1 = data_list_1[0]
    node_2 = data_list_1[2]
    node_3 = data_list_2[1]
    node_4 = data_list_3[1]
    
    def test_MultiImpuritiesDataFrame(self):
        
        #By the process of initiation the MultiImpuritiesData and apped node
        data_aggr_1 = MultiImpuritiesData(self.node_1)
        data_aggr_1.AppendDataMultipleNode(self.data_list_1[1:])
        data_frame_1 = pd.DataFrame(data_aggr_1.GetDataDict())

        # By the class method ExtractDictMultipleNode
        data_aggr_2 = MultiImpuritiesData.ExtractDictMultipleNode(self.data_list_1[::-1])
        data_frame_2 = pd.DataFrame(data_aggr_2.GetDataDict())

        # By the class method ExtractDictMultipleNode and append nodes
        data_aggr_3 = MultiImpuritiesData.ExtractDictMultipleNode(self.data_list_2)
        data_aggr_3.AppendDataMultipleNode(self.data_list_1)
        data_frame_3 = pd.DataFrame(data_aggr_3.GetDataDict())

        def test_unit(self_obj, data_frame):
            
            panda_df = data_frame
            
            # data validation from '22d72273-676a-4243-9d41-f20273d7941b'

            calc_imps = 2
            J_data_uuid = '5c5cff9f-f037-4ab2-ad48-f4ce3743c3df'

            imp0 = 21
            offset0 = 0
            ilayer0 = 3
            
            imp1 = 22
            offset1 = 1
            ilayer1 = 3

            i = 0
            j = 1
            Z_i = 21
            Z_j = 22

            J = 1.24270853e-02
            D = 2.95299862e-03
            Dx = -3.34314299e-04
            Dy = -2.02302285e-03
            Dz = -2.12504431e-03

            rx = -0.41851489357247
            ry = 0.0
            rz = 0.0
            r = abs(rx)

            mom1 = 1.8567015891424e-06
            mom2 = 0.81527563023296
            tot_mom = mom1+mom2

            probing_data = panda_df.loc[panda_df['J_data_uuid']=='5c5cff9f-f037-4ab2-ad48-f4ce3743c3df'].iloc[0]
            
            self_obj.assertEqual(probing_data['calc_imps'], calc_imps)
            self_obj.assertEqual(probing_data['imp0'], imp0)
            self_obj.assertEqual(probing_data['offset0'], offset0)
            self_obj.assertEqual(probing_data['ilayer0'], ilayer0)
            self_obj.assertEqual(probing_data['imp1'], imp1)
            self_obj.assertEqual(probing_data['offset1'], offset1)
            self_obj.assertEqual(probing_data['ilayer1'], ilayer1)
            self_obj.assertEqual(probing_data['i'], i)
            self_obj.assertEqual(probing_data['j'], j)
            self_obj.assertEqual(probing_data['Z_i'], Z_i)
            self_obj.assertEqual(probing_data['Z_j'], Z_j)
            self_obj.assertAlmostEqual(probing_data['J'], J, 7)
            self_obj.assertAlmostEqual(probing_data['D'], D, 7)
            self_obj.assertAlmostEqual(probing_data['Dx'], Dx, 7)
            self_obj.assertAlmostEqual(probing_data['Dy'], Dy, 7)
            self_obj.assertAlmostEqual(probing_data['Dz'], Dz, 7)
            self_obj.assertAlmostEqual(probing_data['rx'], rx, 7)
            self_obj.assertAlmostEqual(probing_data['ry'], ry, 7)
            self_obj.assertAlmostEqual(probing_data['rz'], rz, 7)
            self_obj.assertAlmostEqual(probing_data['r'], r, 7)
            self_obj.assertAlmostEqual(probing_data['mom1'], mom1, 7)
            self_obj.assertAlmostEqual(probing_data['mom2'], mom2, 7)
            self_obj.assertAlmostEqual(probing_data['tot_mom'], tot_mom, 7)

        
        print('Starting the first data group test............')
        test_unit(self, data_frame_1)
        print('Starting the second data group test...........')
        test_unit(self, data_frame_2)
        print('Starting the third data group tesst ...........')
        test_unit(self, data_frame_3)


if __name__ == '__main__':
    unittest.main()
