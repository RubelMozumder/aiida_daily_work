import numpy as np
from aiida.common.constants import elements as elmt
import math

def ExtractLastCalcData(group_pk, Average= True, **kargs):
    
    """
    param: group_pk : Only excepts the Identifier or label 
    param: kargs : key_pair_value1, key_pair_value2, to search for data from  the last_calc_output_param
                    e.i. last_calc_output_param[value1][value2].
    """
    import numpy as np
    from aiida.common.constants import elements as elmt
    import math

    sym_to_zimp = {elmt[zimp]['symbol']:zimp for zimp in elmt.keys()}
    
    combine_imps_group = load_group(group_pk)
    combine_nodes_list = list(combine_imps_group.nodes)
    plot_zimp_row_list = []  # list of imp along the y-axis
    plot_zimp_col_list = [0] # list of imp along the x-axis this extra '0' is indented for singel imp

    for node in combine_nodes_list[:]:
        ## Here to arrange the imps for once, intending for x-axis, plot_col_list, and for y-axis, plot_row_list 
        
        zimp1, zimp2 = sym_to_zimp[node.label.split(':')[0]], sym_to_zimp[node.label.split(':')[1]]
        ## Here only one imp will be consider for once
        if zimp1 not in plot_zimp_row_list:
            plot_zimp_row_list.append(zimp1)
        if zimp2 not in plot_zimp_col_list:
            plot_zimp_col_list.append(zimp2)

    plot_zimp_row_list.sort()
    plot_zimp_col_list.sort()
            
    # This is the list considered as the label for yticks
    plot_imp_row_list = [elmt[zimp]['symbol'] for zimp in plot_zimp_row_list]
    # This is the list considered as the label for xticks
    plot_imp_col_list = [elmt[zimp]['symbol'] for zimp in plot_zimp_col_list]

    print('len of plot_imp_row_list', len(plot_imp_row_list))
    print('len of plot_imp_col_list', len(plot_imp_col_list))

    # Extract all the total_spin_momentum from the combine_imps_wc as well as single impurity
    def extract_last_calc_data(combine_nodes_list, **kargs):
        node_list = combine_nodes_list
        extr_comb_dict = {}
        extr_single_dict = {}
        already_search_imp_list= []
        
        for nod in node_list[:]:
            single_imp_wc = nod.inputs.impurity1_output_node.get_incoming(node_class=kkr_imp_wc).first().node
            zimp= single_imp_wc.inputs.impurity_info.get_dict()['Zimp']
            if zimp not in already_search_imp_list:
                already_search_imp_list.append(zimp)
                ## Now collect the spin_data
                try:
                    out_dict = single_imp_wc.outputs.last_calc_output_parameters.get_dict()
                    for val in kargs.values():
                        out_dict =  out_dict[val]
                    single_imp_val = out_dict
                except:
                    single_imp_val = np.nan
                imp1_symbol= elmt[zimp]['symbol']
                extr_single_dict[imp1_symbol]= single_imp_val

            key= nod.label.split(':')[0] + nod.label.split(':')[1]
            
            try:
                out_dict = nod.outputs.last_calc_output_parameters.get_dict()
                for val in kargs.values():
                    out_dict =  out_dict[val]
                val = out_dict
            except:
                single_imp_val = np.nan
            extr_comb_dict[key]= val


        return extr_comb_dict, extr_single_dict

    # To fill the 2d plot data from the kkrimp_last_calc
    impcalc_data_array = np.zeros(shape= (len(plot_imp_row_list), len(plot_imp_col_list)), dtype= float)
    extr_comb_dict, extr_single_dict = extract_last_calc_data(combine_nodes_list, **kargs)
    row_index= 0
    col_index= 1 # Here the index '0' is skiped as it is fillled with empty string 'xx'
                 # and the coresponding column will be filles with the data extracted
                 # from the singel imp calc data

    for imp1 in plot_imp_row_list[:]:
        col_index = 1
        for imp2 in plot_imp_col_list[1:]:

            if col_index==1:
                ## Here the first column will be fullfiled with the single im_data
                impcalc_data_array[row_index, col_index-1] = extr_single_dict[imp1]
            search_key = plot_imp_row_list[row_index]  + plot_imp_col_list[col_index]
            if search_key in  extr_comb_dict.keys():
                impcalc_data_array[row_index, col_index] =  extr_comb_dict[search_key]
            else:
                impcalc_data_array[row_index, col_index] =  np.nan 

            col_index += 1
        row_index += 1

    plot_data_shape = np.shape(impcalc_data_array)
    if Average:
        CutCol= plot_imp_col_list[1:]
        ## Doing the transpose matrix
        ## In the single cut array first col will be removed from the array
        CutArr= impcalc_data_array[:, 1:]
        for imp1 in plot_imp_row_list:
            y_index= plot_imp_row_list.index(imp1)
            
            for imp2 in CutCol:
                x_index= CutCol.index(imp2)
                if math.isnan(CutArr[x_index,y_index]):
#                    print(f'imp1:imp2= {imp1}:{imp2}, index= {x_index, y_index}, exch_index= {y_index, x_index}')
                    exch_row_col_val= CutArr[y_index,x_index]
                    CutArr[x_index, y_index]= exch_row_col_val
        
        
        CutArrTrans= CutArr.T
        CutArr+= CutArrTrans
        impcalc_data_array[:,1:]= CutArr
        impcalc_data_array = impcalc_data_array/2
    
    print(plot_imp_col_list)
    print(plot_imp_row_list)
    
    return impcalc_data_array, plot_imp_col_list, plot_imp_row_list

## To extract the data from jij calcculation
def ExtractJijData(group_pk, jij_data_position:int=None, D_dev_J=None, atoms_info: bool= True, Average= True):
    from aiida_kkr.calculations import KkrCalculation
    import math

    """
    param: group_pk : Only excepts the ID
    
    jij_data_position: (0: dr_1, 1:dr_2, 2:dr_3)distance between atoms, 3:J, 4:D(abs value),
                        5:Dx, 6:Dy, 7:Dz  
    D_dev_J: True, to calculate the D J ratio
    atoms_info: To get the atom indices
    Average: To average the ndarray specialy for 
    param: kargs : key_1, key2, to search for data from  the last_calc_output_param 
    """
    import numpy as np
    from aiida.common.constants import elements as elmt
    sym_to_zimp = {elmt[zimp]['symbol']:zimp for zimp in elmt.keys()}
    
    combine_imps_group = load_group(group_pk)
    combine_nodes_list = list(combine_imps_group.nodes)
    plot_zimp_row_list = []  # This is the list considered as zimp along the y-axis
    plot_zimp_col_list = []  # This is the list considered as zimp along the x-axis

    for node in combine_nodes_list[:]:
        ## Here to arrange the imps for once, intending for x-axis, 
        ## plot_col_list, and y-axis, plot_row_list 
        
        zimp1, zimp2 = sym_to_zimp[node.label.split(':')[0]], sym_to_zimp[node.label.split(':')[1]]
        ## Here only one imp will be consider for once
        if zimp1 not in plot_zimp_row_list:
            plot_zimp_row_list.append(zimp1)
        if zimp2 not in plot_zimp_col_list:
            plot_zimp_col_list.append(zimp2)
    
    plot_zimp_row_list.sort()
    plot_zimp_col_list.sort()

    # This is the list considered as the label for yticks
    plot_imp_row_list = [elmt[zimp]['symbol'] for zimp in plot_zimp_row_list]
    # This is the list considered as the label for yticks
    plot_imp_col_list = [elmt[zimp]['symbol'] for zimp in plot_zimp_col_list]

    print('len of plot_imp_row_list', len(plot_imp_row_list))
    print('len of plot_imp_col_list', len(plot_imp_col_list))

    # Extract the JijData and JijInfo from the list of combined_imps_node_list
    def extract_jij(combine_nodes_list, jij_data_position:int=None, D_dev_J=None, atoms_info: bool= True):
        node_list = combine_nodes_list
        extr_comb_dict = {}
# del         extr_single_dict = {}
# del         already_search_imp_list= []
# TODO: delete the line with #del 

        Jij_data = None
        some_info_dict = {}
        for nod in node_list[:]:
            key= nod.label.split(':')[0] + nod.label.split(':')[1]
        
            if jij_data_position in [3,4]:
                Jij_data = nod.outputs.JijData.get_array('JijData')[0,:]
                Jij_info = nod.outputs.JijInfo.get_dict()['text'].split('\n')[3].split()
                extr_comb_dict[key]= Jij_data[jij_data_position]
            elif  D_dev_J==True:
                Jij_data = nod.outputs.JijData.get_array('JijData')[0,:]
                Jij_info = nod.outputs.JijInfo.get_dict()['text'].split('\n')[3].split()
                d_j = Jij_data[4]/Jij_data[3]
                extr_comb_dict[key] = d_j
            else:
                print('provide valid input in the funcion ExtractJijData.')
        try:
            kkr_calc= combine_nodes_list[0].outputs.remote_data_gf.get_incoming(node_class=KkrCalculation).all()[0].node
        except:
            kkr_calc= combine_nodes_list[0].inputs.gf_host_remote.get_incoming(node_class=KkrCalculation).all()[0].node
        kkr_output_dict= kkr_calc.outputs.output_parameters.get_dict()
        
# TODO: Add a if statement to take into account only jij_position or D_div_J

## This section regarding for two impurities 
        if atoms_info:
            dist = np.sqrt(np.sum([i**2 for i in Jij_data[0:3]]))
            imps_index = (int(Jij_info[0]), int(Jij_info[1]))
            some_info_dict = {'some_info':{'imp_indices' : imps_index ,
                                            'atom_distance' : dist,
                                            'alat' :kkr_output_dict['alat_internal'],
                                            'alat_unit': 'Bohr'
                                            }
                             }

        return extr_comb_dict, some_info_dict #, extr_single_dict

    # To fill the 2d plot data here
    jij_data_array = np.zeros(shape= (len(plot_imp_row_list), len(plot_imp_col_list)), dtype= float)
    extr_comb_dict, some_info_dict = extract_jij(combine_nodes_list, jij_data_position=jij_data_position, D_dev_J=D_dev_J, atoms_info=atoms_info)
    row_index= 0
    col_index= 0 # Here the index '0' is skiped as it is fillled with empty string 'xx'
                 # and the coresponding column will be filles with the data extracted
                 # from the singel imp calc data

    for imp1 in plot_imp_row_list[:]:
        col_index = 0
        for imp2 in plot_imp_col_list[:]:

            search_key = plot_imp_row_list[row_index]  + plot_imp_col_list[col_index]
            if search_key in  extr_comb_dict.keys():
                jij_data_array[row_index, col_index] =  extr_comb_dict[search_key]
            else:
                jij_data_array[row_index, col_index] =  np.nan 

            col_index += 1
        row_index += 1
## Average the map 
    if Average:
        
        for imp1 in plot_imp_row_list:
            y_index= plot_imp_row_list.index(imp1)
            for imp2 in plot_imp_col_list:
                x_index= plot_imp_col_list.index(imp2)
                if math.isnan(jij_data_array[x_index,y_index]):
                    exch_row_col_val= jij_data_array[y_index,x_index]
                    jij_data_array[x_index, y_index]= exch_row_col_val
        
        JijDataTr= jij_data_array.T
        jij_data_array += JijDataTr
        jij_data_array = jij_data_array/2

    plot_data_shape = np.shape(jij_data_array)
    
    return jij_data_array, plot_imp_col_list, plot_imp_row_list, some_info_dict

