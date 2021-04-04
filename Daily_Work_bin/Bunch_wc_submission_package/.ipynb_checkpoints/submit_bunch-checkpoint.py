#!/usr/bin/env python
# coding: uft-8

"
    In this module only bunch of wc will be submitted.
"

class bunch_wc:
    
    def __init__(self):
        self.Max_fail = 3
        self.Max_submit = 30
        self.Is_sumit_finished = False        
from aiida.orm import Code, Dict, RemoteData
from typing import Union
## --------------------------------------------
    @classmethod
    def combine_imps_bunch_settings(cls, si_imp_list1: list, si_imp_list2: list, kkr_code: Code= None, kkr_imp_code: Code=None,
                          builder_options: Dict = None, succ_group_label: str: None, succ_group_descr: str = None, 
                          offset_imp2:Union[dict, Dict] = {'index':1}, max_submission: int=30, settings: Union[dict, Dict] =None, 
                          gf_host_remote: RemoteData= None, scf_wf_parameters: Union[dict, Dict]=None, debug: bool= False, 
                          params_kkr_overwrite: Union[dict,Dict]= None, dry_run: bool= True, max_fail_wc: int= 3
                          ):
        "
            In this method set all the inputs as function parameters from the user.
        "

        #TODO: Change all the si_imp_list1 into si_imp1_list
        #TODO: 
        from Bunch_wc_submission_package.submission_utils import submission_utils as su
        self = cls()
        self.Si_imp1_list= si_imp_list1
        self.Si_imp2_list= si_imp_list2
        self.Kkr_code = kkr_code
        self.Kkr_imp_code = Kkr_imp_code 
        self.Options = builder_options

        # TODO: Think about codes kkr, kkr_imp, builder_options
        if succ_group_label == None:
            self.Succ_group_label= 'No_group_label_is_found'
        else:
            self.Succ_group_label= succ_group_label

        if succ_group_descr == None:
            self.Succ_group_desc= 'No_group_description_is_found'
        else:
            self.Succ_group_desc= succ_group_descr
            
        if fail_group_label == None:
            self.Fail_group_label= 'No_group_label_is_found_failed'
        else:
            self.Fail_group_label= str(succ_group_label) + '_failed'

        if fail_group_descr == None:
            self.Fail_group_desc= 'No_group_description_is_found_failed'
        else:
            self.Fail_group_desc= str(succ_group_descr) + '_failed'
       

        if isinstance(offset_imp2, dict):
            self.Offset_imp2= Dict(dict=offset_imp2)
        else:
            self.Offset_imp2= offset_imp2

        self.Max_submit= max_submission

        if isinstance(settings, dict):
            self.Settings = Dict(dict=settings)
        else:
            self.Settings = settings

        # TODO: If remote host gf is no given after the first the calc take it as from the first. Employ it later
        self.Gf_host_remote= gf_host_remote

        if isinstance(scf_wf_parameters, dict):
            self.Scf_wf_parameters= Dict(dict= scf_wf_parameters)
        else:
            self.Scf_wf_parameters= scf_wf_parameters
        
        self.Debug = debug

        if isinstance(params_kkr_overwrite, dict):
            self.Params_kkr_overwrite= Dict(dict=params_kkr_overwrite)
        else:
            self.Params_kkr_overwrite = params_kkr_overwrite

        self.Dry_run= dry_run

        self.Max_fail= max_fail_wc
        self.Si_submit = su.submit_combine_imp #The submit function

        self.All_combination_dict = su.create_combine_imps_combination(self.Si_imp1_list, self.Si_imp2_list)
        return self

        
    def submit(self):

        from Bunch_wc_submission_package.submission_utils import submission_utils as su

        # TODO: maybe 'part_1' can be added with the for loop summittion 
        ## Call required tools from the submission utils
        all_combination_dict = self.All_combination_dict.copy()
        all_resedue_dict = all_combination_dict.copy()# resedu dict for all the failed dict
        all_success_dict = {}
        all_submission_dict = {} #TODO change the all_submission dict as all running dict 
        all_failed_dict = {}
        ## some integer variables to track the numbers
        tot_wc_num = len(all_combination_dict)
        all_submission_num = 0
        all_success_num = 0
        all_failed_num = 0
        ## part_1---

        succ_group = su.group_not_exist_create(label = self.Succ_group_label, description= self.Succ_group_descr)
        fail_group = su.group_not_exist_create(label = self.Fail_group_label, description= self.Fail_group_descr)
        
        for key, val in all_combination_dict.items():

            label = all_combination_dict[key]['label']

            wc_pre_exist = su.wc_lbl_in_group(group=succ_group, node_label=label)
            if wc_pre_exist:
                print('Already one wc named as {} is exist in this group'.format(label))
                continue
         # TODO: In the docs add the keys in the all_combination_dict[dict_label]'submission' key as empty and 'label' key for each ubmited wc also mention that key in all_combination_dict[key] is for labeling and tracking all the combine dict
            submission = su.submit_combine_imp(key_value = val, obj=self)
            print(f"THe submitted combine Imps is : {submission.pk}")
            all_submission_dict[key] = all_combination_dict[key].copy()
            all_submission_dict[key]['submission'] = submission
            all_submission_num += 1
            while((all_submission_num - all_success_num - all_failed_num >= max_submission) or
                    (tot_wc_num - all_submission_num == 0) or (all_failed_num == max_fail_wc)):
                    t.sleep(60*2)

    #       --------------------------------------------------------------------------------
                    pop_list = []
                    for submit_key in all_submission_dict.keys():
                        submission = all_submission_dict[submit_key]['submission']
                        if submission.is_finished == True:
                            if submission.exit_status == 0 :
                                all_success_num +=1
                                if all_success_num%5==0:
                                    print('all_success_num : ', all_success_num)
                                all_success_dict[submit_key] = all_combination_dict[submit_key].copy()
                                all_resedue_dict.pop(submit_key)

                                succ_group.add_nodes(submission)
                                pop_list.append(submit_key)
                                su.del_node(node_pks=[submission.pk], dry_run=False, verbosity=0, debug=False, only_remote_dir=True)
                            else:
                                all_failed_num += 1
                                all_failed_dict[submit_key] = all_combination_dict[submit_key].copy()

                                print('INFO: all_failed_num : ', all_failed_num)
                                fail_group.add_nodes(submission)
                                pop_list.append(submit_key)

                        elif submission.is_excepted:
                            all_failed_num += 1
                            all_failed_dict[submit_key] = all_combination_dict[submit_key].copy()
                            print('all_failed_num : ', all_failed_num)
                            fail_group.add_nodes(submission)
                            pop_list.append(submit_key)

    #           -------------------------------------------------------------------------------
                    [all_submission_dict.pop(pop_key) for pop_key in pop_list[:]]
                   
                    # To break while loop here
                    if all_failed_num == max_fail_wc:
                            if (all_submission_num - all_success_num + all_failed_num) == 0 :
                                break
            # To break for loop here
            if all_failed_num == max_fail_wc:
                if (all_submission_num - all_success_num + all_failed_num) == 0:
                    break
        ## To save the success dict in the Bunch_wc 
        self.All_success_dict = all_success_dict.copy()
        self.All_resedue_dict = all_resedue_dict.copy()
        self.All_failed_dict = all_failed_dict.copy()
        self.Is_sumit_finished = True
    

    def ReSubmit(self):
        if self.Is_sumit_finished:
            resedu_dict = sef.All_resedue_dict
            self.All_combination_dict = resedu_dict.copy()
            self.submit() 
























        

