#!/usr/bin/env python
# coding: uft-8

from __future__ import absolute_import
from __future__ import print_function
from aiida.orm import Group, load_node, load_group, Node, Dict, WorkChainNode
from aiida_kkr.workflows import combine_imps_wc, kkr_imp_sub_wc, kkr_flex_wc

"""
    In this module some methodes have been created for the submission of bunch_wc and the 
    intended workflows kkr_imp_wc, kkr_combine_wc.
"""


class submission_utils:
    def __int__(self):
        self.Voronoi = None 
        self.Kkr = None
        self.Kkrimp = None
        self.Options = None
        self.Is_submit_settings_done = False
##----------------------------------
    @classmethod
    def submit_settings (cls, Voronoi: Code, Kkr:Code, Kkrimp:Code, Option: Dict):
        cls = cls()
        cls.Voronoi = Voronoi
        cls.Kkr = Kkr
        cls.Kkrimp = Kkrimp
        cls.Option = Option
        cls.Is_submit_settings_done = True

##---------------------------------
    def group_not_exist_create(self, group_label: str, group_descr:str=''):
        from aiida.orm import load_group, Group
        """
            Check the group exist either must create
        """
        if group_descr==None:
            group_descr='No Description is added'

        try:
             group = load_group(group_label)
        except:
            print('Group named {} is not exist but is being created .'.format(group_label))
            group = Group(label=group_label, description=group_descr)
            group.store()
            print('Newly created group pk {}'.format(group.pk))
        return group

##---------------------------------
   def create_group_save_wc(self,group_label: str="", group_descr: str="", verbose: bool=False,
            wc_list: list = [], wc_dict: dict = {}, debug: bool = True
                            ) -> Group :
        from aiida.orm import load_group, load_node
        " A new group named as <group_label> wil be created if not exist is db and wc from <wc_list> or <wc_dict> will be store.
          wc_list: consists pk
          wc_dict: consists keys node pk, label, description
          Return the actual group
        "

        
        group = self.group_not_exist_create(group_label=group_label, group_descr=group_descr)      
        members_list = group.nodes
        members_label = [i.label for i in nodes_list[:]]
        if wc_list != []:
            for ID in wc_list[:]:
                node = load_node(ID)
                if node.label not in members_label:
                    group.add_nodes(ID)
                else:
                    val = input(f"Node-{ID} is already exist in group-{group.pk}. 
                            Do you want to store this node in the mentioned group? (Y/N)")
                    if val == 'y' or val == 'Y':
                        group.add_nodes(ID)


        if wc_dict != {}:
            for i in wc_dict.keys():
                node = load_node(wc_dict[i]['pk'])
                if node.label not in members_label:
                    group.add_nodes(ID)
                else:
                    val = input(f"Node-{ID} is already exist in group-{group.pk}. 
                            Do you want to store this node in the mentioned group? (Y/N)")
                    if val == 'y' or val == 'Y':
                        group.add_nodes(ID)

        return group

##-----------------------------------------
    def wc_in_group(self, node_pk: int = None, node: Node= None,  node_label: str =None, group_pk: int=None, 
            group_label: str='', group: Group=None
                        )-> bool:
        """
         To check any node with the same label is exist or not!
         return: True, if the given node is exist otherwise 
                 False
        """
        if node_pk != None:
            node = load_node(node_pk)
            node_label= node.label
        elif node != None:
            node_label = node.label

        if group_pk != None:
            group = load_group(group_pk)
        elif group_label != '':
            group = load_group(group_label)
        
        members_label = [i.label for i in group.nodes]
        
        if node_label in members_label:
            exist = True
           
        else:
            exist = False
 
        return exist
##-------------------------------------------

    def create_combine_imps_combination(self, imp_list1: list, imp_list2: list)-> dict :
        "
            imp1_list1; imp2_list2 are the wc node lists.
            Create all possible combinations from two given lists.
            Returns dict consists of dict <wc_num> consist of <label>, and empty <submission node>. 
            The label for each combine_imps_wc is also create here.
        "
        if not isinstance(si_imp_list1, list):
            print('The given impurity wc list 1 is not the list type.')
            return print('Please provide single_imp1_list.')
        if not isinstance(si_imp_list2, list):
            print('The given impurity wc list 2 is not the list type.')
            return print('Please provide single_imp2_list.')
        
        for i in si_imp_list1[:]:
            for j in si_imp_list2[:]:
                node_truple = (i, j)
                pk_truple = (i.pk, j.pk)
                imp1_info = i.inputs.impurity_info.get_dict()
                imp2_info = j.inputs.impurity_info.get_dict()
                ilayer1 = str(imp1_info['ilayer_center'])
                ilayer2 = str(imp2_info['ilayer_center'])
                try:
                    label= i.label.split(':')[0] + ':'+ j.label+'_il_'+ilayer1+'_il_'+ilayer2
                else:
                    #print(f"INFO: Single_imp_wc does not have any label ")
                    label = f"pk:{i.pk}:{j.pk}"

                all_combination_dict[tot_wc_num] = {'label' : label,
                                                    'submission': None}
        return all_combination_dict


    from aiida.orm import Code
    from typing import Union

##---------------------------------
    def submit_combine_imp_old_atempt(self, imp1_wc_node: Node, imp2_wc_node: Node, offset_imp2:Union[dict, Dict],
                           settings:Union[dict, Dict]=None , dry_run: bool=False, label:str = '', 
                           gf_host_remote: Dict = None, scf_wf_parameters: Union[Dict, dict] = None, 
                           params_kkr_overwrite: Union[Dict, dict]=None, verbose: bool=False) -> Union[WorkChainNode, str]:
    "
        One combine_imps will be submited here.
        Here one wc will be submitted for each combination from the all_combiantion_dict. And all the required inputs will be taken from the given object.
    "

# TODO: Add node_tuple, pk_tuple in the create_combine_imps_combination
        if not self.Is_submit_settings_done:
            if verbose:
                print('No settings from submission_util has been found, Therefore the needed info is extracted from imp_1 node.'
            # extract code and option from the imp1_wc_node
            kkr_code = imp1_wc_node.inputs.kkr
            kkr_imp_code = imp1_wc_node.inputs.kkrimp
            options = imp1_wc_node.inputs.options
        elif self.Is_submit_settings_done:
            kkr_code = self.Kkr
            kkr_imp_code = self.Kkrimp
            options = self.Options
            if isinstance(options, dict):
                options = Dict(dict=options)

        imp1_output = imp1_wc_node.outputs.workflow_info
        imp2_output = imp2_wc_node.outputs.workflow_info
        if scf_wf_parameters==None:
            sub_wc1_node = imp1_wc_node.get_outgoing(node_class=kkr_imp_sub_wc).first().node
            scf_wf_parameters = sub_wc1_node.inputs.wf_parameters
        if params_kkr_overwrite==None:
            sub_gf_write_out = imp1_wc_node.get_outgoing(node_class=kkr_flex_wc).first().node
            params_kkr_overwrite = sub_gf_write_out.inputs.params_kkr_overwrite
        if settings==None:
            settings = imp1_wc_node.inputs.wf_parameters_overwrite
        if label==None:
            label = 'pk' + str(imp1_wc_node.pk)+':'+ str(imp1_wc_node.pk)

        builder = combine_imps_wc.get_builder()
        builder.impurity1_output_node = imp1_output
        builder.impurity2_output_node = imp2_output
        if isinstance(offset_imp2, dict):
            builder.offset_imp2 = Dict(dict=offset_imp2)
        else:
            builder.offset_imp2 = offset_imp2

        builder.scf.kkrimp = kkr_imp_code
        builder.scf.options = options
        builder.scf.wf_parameters = scf_wf_parameters

        if gf_host_remote==None:
            builder.host_gf.kkr = kkr_code
            builder.host_gf.options = options
            builder.host_gf.params_kkr_overwrite = params_kkr_overwrite #host_gf.inputs.wf_parameters
        else:
            builder.gf_host_remote = gf_host_remote
        if settings!=None:
            if isinstance(settings, dict):
                builder.wf_parameters_overwrite = Dict(dict=settings)
            else:
                builder.wf_parameters_overwrite = settings

        builder.metadata.label = label
        if not dry_run:
            submission = submit(builder)
            return submission
        else:
            msg = f'This is dry_run. WC label {label}'
            return msg

##---------------------------------
    def submit_combine_imp(self, key_value: dict, obj: object)->Node:
    "
        One combine_imps will be submited here.
        Here one wc will be submitted for each combination from the all_combiantion_dict. And all the required inputs will be taken from the given object.
        param: key_value from the 'all_combination_dict' to call the wc as mentioned there.
    "
# TODO: Add node_tuple(must_node), pk_tuple in the create_combine_imps_combination
        if not self.Is_submit_settings_done:
            if verbose:
                print('No settings from submission_util has been found, Therefore the needed info is extracted from imp_1 node.'
            # extract code and option from the imp1_wc_node
            kkr_code = obj.Kkr
            kkr_imp_code = obj.Kkrimp
            options = obj.Options

        if self.Is_submit_settings_done:
            kkr_code = self.Kkr
            kkr_imp_code = self.Kkrimp
            options = self.Options
            if isinstance(options, dict):
                options = Dict(dict=options)

        imp1_output = dict_value['node_truple'][0].outputs.workflow_info
        imp2_output = dict_value['node_truple'][1].outputs.workflow_info
        if obj.Scf_wf_parameters==None:
            sub_wc1_node = imp1_wc_node.get_outgoing(node_class=kkr_imp_sub_wc).first().node
            scf_wf_parameters = sub_wc1_node.inputs.wf_parameters
        if obj.Params_kkr_overwrite==None:
            sub_gf_write_out = imp1_wc_node.get_outgoing(node_class=kkr_flex_wc).first().node
            params_kkr_overwrite = sub_gf_write_out.inputs.params_kkr_overwrite
        if obj.Settings==None:
            settings = imp1_wc_node.inputs.wf_parameters_overwrite
        if dict_value['label']==None:
            label = 'pk' + str(imp1_wc_node.pk)+':'+ str(imp1_wc_node.pk)

        builder = combine_imps_wc.get_builder()
        builder.impurity1_output_node = imp1_output
        builder.impurity2_output_node = imp2_output
        if isinstance(obj.Offset_imp2, dict):
            builder.offset_imp2 = Dict(dict=obj.Offset_imp2)
        else:
            builder.offset_imp2 = obj.Offset_imp2

        builder.scf.kkrimp = kkr_imp_code
        builder.scf.options = options
        builder.scf.wf_parameters = scf_wf_parameters

        if obj.Gf_host_remote==None:
            builder.host_gf.kkr = kkr_code
            builder.host_gf.options = options
            builder.host_gf.params_kkr_overwrite = params_kkr_overwrite #host_gf.inputs.wf_parameters
        else:
            builder.gf_host_remote = obj.Gf_host_remote
        if obj.Settings!=None:
            if isinstance(obj.Settings, dict):
                builder.wf_parameters_overwrite = Dict(dict=obj.Settings)
            else:
                builder.wf_parameters_overwrite = obj.Settings

        builder.metadata.label = label
        if not obj.Dry_run:
            submission = submit(builder)
            return submission
        else:
            msg = f'This is dry_run. WC label {label}'
            return msg
 
