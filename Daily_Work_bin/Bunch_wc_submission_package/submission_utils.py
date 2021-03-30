#!/usr/bin/env python
# coding: uft-8
from __future__ import absolute_import
from __future__ import print_function
"""
    In this module some methodes have been created for the submission of bunch_wc and the 
    intended workflows kkr_imp_wc, kkr_combine_wc.
"""
class submission_util:
#    def __init__(self):
#
#        return self
    from aiida.orm import Group, load_node, load_group, Node
    def create_group_save_wc(self,group_label: str="", group_desc: str="", verbose: bool=False,
            wc_list: list = [], wc_dict: dict = {}, debug: bool = True
                            ) -> Group :
        from aiida.orm import load_group, load_node
        " A new group named as <group_label> wil be created if not exist is db and wc from <wc_list> or <wc_dict> will be store.
          wc_list: consists pk
          wc_dict: consists keys node pk, label, description
          Return the actual group
        "
        
        try:
            group = load_group(label= group_label)
        except:
            group = Group(label=group_label, description=group_desc)
            if debug:
                print(f"group is not exist in the db, A new group has been created with pk {group.pk}")
        
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

    def wc_lbl_in_group(self, node_pk: int = None, node: Node= None, group_pk: int=None, 
            group_label: str='', group: Group=None
                        )-> bool:
        """
         To check any node with the same label is exist or not!
         return: True, if the given node is exist otherwise 
                 False
        """
        if node_pk != None:
            node = load_node(node_pk)
        if group_pk != None:
            group = load_group(group_pk)
        if group_label != '':
            group = load_group(group_label)
        members_label = [i.label for i in group.nodes]
        
        if node.label in members_label:
            exist = True
           
        else:
            exist = False
 
        return exist

    def create_combine_imp_combination(self, imp_list1: list, imp_list2: list)->


