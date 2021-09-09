from aiida.orm import Node
from typing import List
import math as m
## This module is for single node data parse
## for multiple data parse we will use __add__()methode

class CoupleImpurityData(object):
    """A impurity couple.
    
    Extract all the magnetic data for a pair of impurities.
    """
    
    def __init__(self, node: Node, imp_orders: dict, ) -> None:
        """Instantiate
        node: kkr_combine_imp wf node.
        imp_orders: Order of impurities to extract data.
                For example, for two impurities from 4-impurities
                calculation{key1: 1, key2: 2}
                ordering: imp_order1, imp_order2 (1, 2 stands for 
                second imp and third imp.)
        """
        
        self.imp1: int = None
        self.imp2: int = None
        self.offset1: int = None
        self.offset2: int = None
        self.il1: int = None
        self.il2: int = None
        self.J_ij: float = None
        self.Dx: float = None
        self.Dy: float = None
        self.Dz: float = None
        self.D: float = None
        self.rx: float = None
        self.ry: float = None
        self.rz: float = None
        self.r: float = None
        self.mom1: float = None
        self.mom2: float = None
        self.tot_mom: float = None
        
        self.imp_order1: int = list(imp_orders.values())[0]
        self.imp_order2: int = list(imp_orders.values())[1]
        
        # To fill all the attributes
        self.ExtractData(node)
    
#    @classmethod
#    def CoupleImpurityData(cls, node: Node, **data_keys):
#        """Collect user needed data.
#        data_keys: {key:empty_value}
#        """
    
    def __str__(self):
        print_str = (f'Zimp1: {self.imp1}, Zimp2: {self.imp2},\n'
                     f'offset1: {self.offset1}, offset2: {self.offset2},\n'
                     f'ilayer1: {self.il1}, ilayer2: {self.il2},\n'
                     f'J_ij: {self.J_ij},\n'
                     f'D_ij: {self.D}, Dx: {self.Dx}, Dy: {self.Dy},'
                     f' Dz:{self.Dz},\n'
                     f'r_ij: {self.r}, rx: {self.rx}, ry: {self.ry}, '
                     f'rz: {self.rz},\n'
                     f'magnetic moment-1: {self.mom1},'
                     f' magnetic moment-2: {self.mom2},\n'
                     f'total moment: {self.tot_mom}')
        return print_str 
    
    def ExtractData(self, node: Node):
        
        imp_order1 = self.imp_order1
        imp_order2 = self.imp_order2
        workflow_info = node.outputs.workflow_info.get_dict()
        
        try:
            imps_info_in_exact_cluster = (workflow_info[
                                        'imps_info_in_exact_cluster'])
        except KeyError:
            imps_info_in_exact_cluster = self.ExtractImpInfo(node)
            
            
        try:
            jij_data = node.outputs.JijData.get_array('JijData')
        except KeyError:
            raise KeyError(f'The combine_impurity_calculation uuid: {node.uuid}'
                      f' did execute the Jij calculation.')
            
        else:
            jij_info = node.outputs.JijInfo.get_dict()['text']

        impurity_info = (node.get_outgoing(node_class=kkr_imp_sub_wc).all()
                        [0].node.inputs.impurity_info.get_dict())
        zimp = impurity_info['Zimp']
        imp_cls = impurity_info['imp_cls']
        
        # To collect the impurity index from cluster 
        zimp_index_cluster = [ind for ind, cluster_atom_info in 
                              enumerate(imp_cls) if cluster_atom_info[-2] in zimp]
        
        self.imp1 = int(imp_cls[zimp_index_cluster[imp_order1]][-2])
        self.imp2 = int(imp_cls[zimp_index_cluster[imp_order2]][-2])
        # for old version of 
        if len(zimp) != len(imps_info_in_exact_cluster['offset_imps']):
            self.offset1 = 0
            self.offset2 = imps_info_in_exact_cluster['offset_imps'][
                                                       imp_order2-1]
        else:
            self.offset1 = imps_info_in_exact_cluster['offset_imps'][imp_order1]
            self.offset2 = imps_info_in_exact_cluster['offset_imps'][imp_order2]

        self.il1 = imps_info_in_exact_cluster['ilayers'][imp_order1]
        self.il2 = imps_info_in_exact_cluster['ilayers'][imp_order2]
        
        jij_info_arr = ([[float(data.strip()) for data in dataline.split(' ')
                         if data != ''] 
                         for dataline in jij_info.split('\n')[3:-1]])
        
        jij_pairs = [[data[0], data[1]] for data in jij_info_arr]
        jij_pair = [float(zimp_index_cluster[imp_order1]),
                    float(zimp_index_cluster[imp_order2])]
        jij_pair_index = jij_pairs.index(jij_pair)
        r_j_d = jij_data[jij_pair_index][:]
        
        self.J_ij = r_j_d[3]
        
        self.D = r_j_d[4]
        self.Dx = r_j_d[5]
        self.Dy = r_j_d[6]
        self.Dz = r_j_d[7]
        
        self.rx = r_j_d[0]
        self.ry = r_j_d[1]
        self.rz = r_j_d[2]
        self.r = m.sqrt(sum([i**2 for i in r_j_d[0:3]]))
        
        # To collect the output data
        spin_moment_per_atom = (node.outputs.last_calc_output_parameters
                            .get_dict()['magnetism_group']
                             ['spin_moment_per_atom'])
        self.mom1 = spin_moment_per_atom[int(jij_pair[0])][2]
        self.mom2 = spin_moment_per_atom[int(jij_pair[1])][2]
        self.tot_mom = self.mom1 + self.mom2
        
        
    def ExtractImpInfo(self, node):
        """Extract impurity info from single kkrimpm calc.
        
            This construct a python dict keeping info about two single 
            inpurities with respect to the original host structure e.i.
            before transforming the center to the first impurity position.
        """
        
        input_node_1 = node.inputs.impurity1_output_node
        input_node_2 = node.inputs.impurity1_output_node
        offset_imp2 = node.inputs.offset_imp2
        
        single_imp1_wc = self.get_imp_node_from_input(input_node_1)
        single_imp2_wc = self.get_imp_node_from_input(input_node_2)
        
        impinfo1 = single_imp1_wc.inputs.impurity_info
        impinfo2 = single_imp2_wc.inputs.impurity_info
        # imp_info_in_exact_cluster keeps the exact data before
        #creating the cluster will help to add more imps later.
        imps_info_in_exact_cluster = ({'Zimps':[], 'ilayers':[], 
                                      'offset_imps': [0]} ) 
        #offset_imp contains offset_index for imps 2nd, 3rd so on
        zimp_1= impinfo1.get_dict().get('Zimp') 
        zimp_2= impinfo2.get_dict().get('Zimp')
        if isinstance(zimp_1, list):
            zimp_1 = zimp_1[0]
        if isinstance(zimp_2, list):
            zimp_2 = zimp_2[0]
            
        imps_info_in_exact_cluster['Zimps'].append(zimp_1)
        imps_info_in_exact_cluster['Zimps'].append(zimp_2)
        imps_info_in_exact_cluster['ilayers'].append(
            impinfo1.get_dict().get('ilayer_center'))
        imps_info_in_exact_cluster['ilayers'].append(
            impinfo2.get_dict().get('ilayer_center'))
        imps_info_in_exact_cluster['offset_imps'].append(
            offset_imp2.get_dict().get('index'))
        
        return imps_info_in_exact_cluster
                         
        
    def get_imp_node_from_input(self, impurity_output_node=None):
        """
        extract impurty calculation from impurity_output_node as inputs
        """
        imp_out = impurity_output_node

        kkrimpcalc_parents = imp_out.get_incoming(node_class=KkrimpCalculation).all()
        if len(kkrimpcalc_parents) > 0:
            parent_imp1_wc_or_calc = kkrimpcalc_parents[0].node
        else:
            inc = imp_out.get_incoming(link_label_filter='workflow_info').all()
            if len(inc)!=1:
                raise ValueError('More input WorkChainNodes are found.')
            parent_imp1_wc_or_calc = inc[0].node
        
        return parent_imp1_wc_or_calc

    
class MultiImpuritiesData(object):
    """Multiple impurity data extraction.
    
    """
    def __init__(self, node: Node):
        """Tnstantiate MultiImpurityData.
        inputs:
        node: aiida node. It should be combine impurity calculation node.
        """
        workflow_info = node.outputs.workflow_info.get_dict()
        self.zimps = workflow_info['imp_info_combined']['Zimp']
        
        self.node = node
        

        self.DataDictConstruct()
        self.DataDictFill()
        
    
    def DataDictConstruct(self):
        imp_num = len(self.zimps)
        multi_impurity_dict = dict()
        
        for imp_no in range(imp_num):
            multi_impurity_dict['imp'+str(imp_no)] = []
            multi_impurity_dict['offset'+str(imp_no)] = []
            multi_impurity_dict['ilayer'+str(imp_no)] = []
            
        multi_impurity_dict['i'] = []
        multi_impurity_dict['j'] = []
        multi_impurity_dict['Z_i'] = []
        multi_impurity_dict['Z_j'] = []
        multi_impurity_dict['J'] = []
        multi_impurity_dict['D'] = []
        multi_impurity_dict['Dx'] = []
        multi_impurity_dict['Dy'] = []
        multi_impurity_dict['Dz'] = []
        multi_impurity_dict['rx'] = []
        multi_impurity_dict['ry'] = []
        multi_impurity_dict['rz'] = []
        multi_impurity_dict['r'] = []
        multi_impurity_dict['mom1'] = []
        multi_impurity_dict['mom2'] = []
        multi_impurity_dict['tot_mom'] = []
        
        self.multi_impurity_dict = multi_impurity_dict
    
    def DataDictFill(self):
        
        multi_impurity_dict = self.multi_impurity_dict
        couple_imp_data_obj_list = []
        
        
        couple_imp_data_obj = None
        last_imp_order = None  
        # Fill all the impurity filled but not interaction
        for imp1_order in range(len(self.zimps))[:-1]:
            couple_imp_data_obj = None
            for imp2_order in range(len(self.zimps))[imp1_order+1:]:
                couple_imp_data_obj = CoupleImpurityData(self.node, 
                                      imp_orders={'imp_order1':imp1_order,
                                      'imp_order2': imp2_order})
                couple_imp_data_obj_list.append(couple_imp_data_obj)
                
                last_imp_order = imp2_order
                ## TODO: add the object in couple_inp_data_obj_list
                ## TODO: fill the imp data in multi_impurity_dict dict not the interaction data
                ## Include also __add__ to the class method to extend the data
                
            multi_impurity_dict['imp'+str(imp1_order)].append( couple_imp_data_obj.imp1)
            multi_impurity_dict['ilayer'+str(imp1_order)].append(couple_imp_data_obj.il1)
            multi_impurity_dict['offset'+str(imp1_order)].append(couple_imp_data_obj.offset1)
            
        multi_impurity_dict['imp'+str(last_imp_order)].append(couple_imp_data_obj.imp2)
        multi_impurity_dict['ilayer'+str(last_imp_order)].append(couple_imp_data_obj.il2)
        multi_impurity_dict['offset'+str(last_imp_order)].append(couple_imp_data_obj.offset2)
        
        
        # Here to fill up the data
        for enum, obj in enumerate(couple_imp_data_obj_list):
            multi_impurity_dict['i'].append(obj.imp_order1)
            multi_impurity_dict['j'].append(obj.imp_order2)
            multi_impurity_dict['Z_i'].append(obj.imp1)
            multi_impurity_dict['Z_j'].append(obj.imp2)
            multi_impurity_dict['J'].append(obj.J_ij)
            multi_impurity_dict['D'].append(obj.D)
            multi_impurity_dict['Dx'].append(obj.Dx)
            multi_impurity_dict['Dy'].append(obj.Dy)
            multi_impurity_dict['Dz'].append(obj.Dz)
            multi_impurity_dict['rx'].append(obj.rx)
            multi_impurity_dict['ry'].append(obj.ry)
            multi_impurity_dict['rz'].append(obj.rz)
            multi_impurity_dict['r'].append(obj.r)
            multi_impurity_dict['mom1'].append(obj.mom1)
            multi_impurity_dict['mom2'].append(obj.mom2)
            multi_impurity_dict['tot_mom'].append(obj.tot_mom)
            
            # To extend the impurity coloumn by one row not interaction
            if enum != len(couple_imp_data_obj_list)-1:
                for imp_order in range(len(self.zimps)):
                    
                    imp = multi_impurity_dict['imp'+str(imp_order)][-1]
                    il = multi_impurity_dict['ilayer'+str(imp_order)][-1]
                    offset = multi_impurity_dict['offset'+str(imp_order)][-1]
                    
                    multi_impurity_dict['imp'+str(imp_order)].append(imp)
                    multi_impurity_dict['ilayer'+str(imp_order)].append(il)
                    multi_impurity_dict['offset'+str(imp_order)].append(offset)

        self.multi_impurity_dict = multi_impurity_dict
                    
    def ExtractDataMultipleNode(self, node_list: List[Node]):
        if isinstance(node_list, list):
            for node in node_list:
                self.node = node
                self.DataDictFill()
        else:
            raise TypeError('Parameter node_list should be list of node.')
            
        
        
    def GetDataDict(self):
        return self.multi_impurity_dict
    
    def __repr__(self):
        
        import pandas as pd
        multi_impurity_dict = self.multi_impurity_dict
        print_str = (f'multi impurity dict: \n{multi_impurity_dict}')
        return print_str
        
