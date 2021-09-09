## Taken From Rüssman philip:

import numpy as np
import matplotlib.pyplot as plt
from random import randint
from aiida.orm import load_node
from aiida_kkr.tools import plot_kkr
from aiida_kkr.calculations import VoronoiCalculation
from aiida_kkr.tools.combine_imps import create_combined_imp_info, combine_potentials, pos_exists_already
from aiida_kkr.workflows import kkr_imp_sub_wc
from aiida.orm import Dict, Int
from aiida_kkr.workflows import kkr_flex_wc
from aiida_kkr.calculations import KkrCalculation
from aiida.engine import submit, WorkChain, calcfunction
from aiida.engine import ToContext
from masci_tools.io.common_functions import get_alat_from_bravais
from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt
from random import randint
from aiida.orm import ArrayData
import numpy as np
from masci_tools.io.common_functions import get_Ry2eV
import tarfile
import matplotlib
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap


class combine_imps_multiple_V_Sb2Te3_surface_wc(WorkChain):
    """
    Dummy workchain to run combine imps calculations for random impurity positions
    """
    @classmethod
    def define(cls, spec):
        """
        Defines the outline of the workflow
        """

        # take define from AiiDA base class and extend it then
        super(combine_imps_multiple_V_Sb2Te3_surface_wc, cls).define(spec)
        
          # expose these inputs from sub-workflows
        spec.expose_inputs(kkr_imp_sub_wc, namespace='scf', include=('kkrimp', 'options', 'wf_parameters',))
        spec.expose_inputs(kkr_flex_wc,
                           namespace='host_gf',
                           include=('kkr', 'options', 'params_kkr_overwrite',), # expose only those port which are not set automatically
                           namespace_options={'required': False, 'populate_defaults': False}, # this makes sure the kkr code input is not needed if gf_host_remote is provided and the entire namespace is omitted
                          )

        # mandatory inputs
        spec.input("settings", valid_type=Dict, required=True, help="Dict node that contains the setting of the calculation")

        # structure of the workflow
        spec.outline(
            cls.start,                      # initialize workflow (set things in context and some consistency checks)
            cls.run_gf_writeout,            # run gf writeout step
            cls.run_kkrimp_scf,             # run the kkrimp_sub workflow to converge the host-imp startpot
            #cls.run_noco_scf,               # run noco scf step
            cls.run_Jij,                    # run Jij calculation step
            cls.return_results)             # check if the calculation was successful and return the result nodes


        # define the possible exit codes
        spec.exit_code(999, 'ERROR_SOMETHING_WENT_WRONG', message="ERROR: take a look!")

        # define the outputs of the workflow
        spec.output('results')
        spec.output('JijData')
        
        
    def start(self):
        """set up the calculation based on the scoef input"""
        # starting single imp calculations
        if self.inputs.settings['Rcut_singleimp']==4.0:
            calc_V_Sb1 = load_node('59956890-e25d-47c3-986a-2dc83e769111') # R = 4 (up to and exluding the next Sb shell)
            calc_V_Sb2 = load_node('c8f073b4-b45f-4137-ab21-33e77fe7f1e5') # R = 4 (up to and exluding the next Sb shell)
        elif self.inputs.settings['Rcut_singleimp']==4.8:
            calc_V_Sb1 = load_node('3ea35063-f3cf-400e-a863-8e03a56f3daf') # R = 4.8 (including next Sb shell), layer 12 (first Sb)
            calc_V_Sb2 = load_node('1fda4bd1-8b37-4a48-b5f5-fad2cf04ad19') # R = 4.8 (including next Sb shell), layer 16 (secon Sb)

        def get_pot_imp(impinfo):
            if impinfo['ilayer_center']==12:
                pot_imp = calc_V_Sb1.get_outgoing(node_class=kkr_imp_sub_wc).first().node.outputs.host_imp_pot
            elif impinfo['ilayer_center']==16:
                pot_imp = calc_V_Sb2.get_outgoing(node_class=kkr_imp_sub_wc).first().node.outputs.host_imp_pot
            return pot_imp
        
        scoef = np.array(self.inputs.settings['scoef'])
        R0 = self.inputs.settings['Rcut_singleimp']
        
        struc, _ = VoronoiCalculation.find_parent_structure(calc_V_Sb1.inputs.remote_data_gf)

        impinfo1 = Dict(dict={'Rcut':R0, 'ilayer_center': int(scoef[0,3]), 'Zimp': [23.0]})
        impinfo2 = Dict(dict={'Rcut':R0, 'ilayer_center': int(scoef[1,3]), 'Zimp': [23.0]})
        offset_imp2 = Dict(dict={'r_offset': scoef[1,:3]})

        pot_imp1 = get_pot_imp(impinfo1)
        pot_imp2 = get_pot_imp(impinfo2)

        nspin_node = Int(2)

        o = create_combined_imp_info(struc, impinfo1, impinfo2, offset_imp2, debug=False)

        imp_pot_combined = combine_potentials(o['kickout_info'], pot_imp1, pot_imp2, nspin_node)
        imp_info_combined = o['imp_info_combined']

        self.report(o['kickout_info'].get_dict())

        for iimp in range(2, len(scoef)):
            impinfo2 = Dict(dict={'Rcut':R0, 'ilayer_center': int(scoef[iimp,3]), 'Zimp': [23.0]})
            offset_imp2 = Dict(dict={'r_offset': scoef[iimp,:3]})

            o = create_combined_imp_info(struc, imp_info_combined, impinfo2, offset_imp2, debug=False)

            pot_imp2 = get_pot_imp(impinfo2)

            imp_pot_combined = combine_potentials(o['kickout_info'], imp_pot_combined, pot_imp2, nspin_node)
            imp_info_combined = o['imp_info_combined']
            self.report(o['kickout_info'].get_dict())

        self.report(len([i.split('exc')[0] for i in imp_pot_combined.get_content().split('\n') if 'exc' in i]))

        self.ctx.imp_info_combined = imp_info_combined
        self.ctx.imp_pot_combined = imp_pot_combined
        self.ctx.calc_V_Sb1 = calc_V_Sb1
    
        
    def run_gf_writeout(self):
        """run the GF writeout step"""


        # create process builder for gf_writeout workflow
        builder = kkr_flex_wc.get_builder()
        builder.impurity_info = self.ctx.imp_info_combined
        builder.kkr = self.inputs.host_gf.kkr

        if 'options' in self.inputs.host_gf:
            builder.options = self.inputs.host_gf.options

        if 'params_kkr_overwrite' in self.inputs.host_gf:
            self.report("INFO: using params_kkr_overwrite in host_gf step: {}".format(self.inputs.host_gf.params_kkr_overwrite.get_dict()))
            builder.params_kkr_overwrite = self.inputs.host_gf.params_kkr_overwrite

        # implement no-retrieve for GF?
        builder.wf_parameters = Dict(dict={'ef_shift': 0., 'retrieve_kkrflex': False}) # ef_shift: 0.0, -0.4                                          

        # find converged_host_remote input (converged potential of host system)
        gf_writeout_calc = None
        imp1_sub = self.ctx.calc_V_Sb1.get_outgoing(node_class=kkr_imp_sub_wc).first().node
        if gf_writeout_calc is None:
            gf_writeout_calc = imp1_sub.inputs.remote_data.get_incoming(node_class=KkrCalculation).first().node
            builder.remote_data = gf_writeout_calc.inputs.parent_folder

        # set label and description of the calc
        sub_label = 'GF writeout combined imps'
        sub_description = 'GF writeout sub workflow for combine_imps_wc '
        builder.metadata.label = sub_label # pylint: disable=no-member
        builder.metadata.description = sub_description # pylint: disable=no-member

        # now submit the workflow
        future = self.submit(builder)

        # change settings for EF shift
        builder.wf_parameters = Dict(dict={'ef_shift': -0.4, 'retrieve_kkrflex': False})
        builder.metadata.label = sub_label+' EFshift' # pylint: disable=no-member
        builder.metadata.description = sub_description+' with EFshift' # pylint: disable=no-member
        # now submit the workflow
        future2 = self.submit(builder)

        return ToContext(gf_writeout_combined = future, gf_writeout_combined_efshift = future2)


    def run_kkrimp_scf(self):
        """run the impurity scf step for the big (multi-imp) cluster"""

        wf_parameters = self.ctx.calc_V_Sb1.inputs.wf_parameters.get_dict()
        wf_parameters['hfield'] = [0.0, 0]
        wf_parameters['mag_init'] = False

        # construct process builder for kkrimp scf workflow
        builder = kkr_imp_sub_wc.get_builder()
        builder.metadata.label = 'kkrimp scf combined imps' # pylint: disable=no-member

        # add combined impurity-info and startpot
        builder.impurity_info = self.ctx.imp_info_combined
        builder.host_imp_startpot = self.ctx.imp_pot_combined

        # add host GF (either calculated or form input)
        if 'gf_host_remote' not in self.inputs:
            gf_remote = self.ctx.gf_writeout_combined.outputs.GF_host_remote
        else:
            gf_remote = self.inputs.gf_host_remote
        builder.remote_data = gf_remote
        if 'gf_host_remote_efshift' not in self.inputs:
            gf_remote2 = self.ctx.gf_writeout_combined_efshift.outputs.GF_host_remote
        else:
            gf_remote2 = self.inputs.gf_host_remote_efshift
        builder.remote_data_Efshift = gf_remote2

        # settings from scf namespace
        builder.kkrimp = self.inputs.scf.kkrimp
        if 'options' in self.inputs.scf:
            builder.options =  dict=self.inputs.scf.options
        if 'wf_parameters' in self.inputs.scf:
            builder.wf_parameters = self.inputs.scf.wf_parameters
        else:
            builder.wf_parameters = Dict(dict=wf_parameters)

        # take care of LDA+U settings
        #add_ldausettings, settings_LDAU_combined = self.get_ldau_combined()
        #self.report(f'add LDA+U settings? {add_ldausettings}')
        #if add_ldausettings:
        #    self.report(f'settings_combined: {settings_LDAU_combined.get_dict()}')
        #    builder.settings_LDAU = settings_LDAU_combined

        # submit calculations
        future = self.submit(builder)

        return ToContext(imp_scf_big = future)

    def run_Jij(self):
        """run a Jij calculation with the converged potential"""

        if not self.ctx.imp_scf_big.is_finished_ok:
            return self.exit_codes.ERROR_SOMETHING_WENT_WRONG

        last_calc = load_node(self.ctx.imp_scf_big.outputs.workflow_info['last_calc_nodeinfo']['uuid'])
        builder = last_calc.get_builder_restart()
        builder.pop('parent_calc_folder')
        builder.impurity_potential = self.ctx.imp_scf_big.outputs.host_imp_pot
        d = {k:v for k,v in builder.parameters.get_dict().items() if v is not None}
        d['CALCJIJMAT'] = 1 # activate Jij calculation, leave the rest as is
        builder.parameters = Dict(dict=d)
        builder.metadata.label = 'KKRimp_Jij ('+last_calc.label.split('=')[1][3:]

        future = self.submit(builder)
        self.report('submitted Jij calculation (uuid=%s)'%(future.uuid))
        
        return ToContext(imp_scf_big_jij = future)
        

    def return_results(self):
        """collect results and create additional output nodes"""

        # retrieve magnetic moments etc.

        last_calc = load_node(self.ctx.imp_scf_big.outputs.workflow_info['last_calc_nodeinfo']['uuid'])
        out_dict = collect_outputs(self.ctx.imp_scf_big.outputs.workflow_info, last_calc.outputs.output_parameters)
        self.out('results', out_dict)

        # retrieve_Jijs
        retrieved = self.ctx.imp_scf_big_jij.outputs.retrieved
        impurity_info = self.ctx.imp_scf_big_jij.inputs.impurity_info
        out = parse_Jij(retrieved, impurity_info)
        out_txt = out['info']['text']
        self.report(out['info']['text'])
        self.out('JijData', out['Jijdata'])
    
@calcfunction
def collect_outputs(workflow_info, output_parameters):
    """collect results from impurty scf calculation"""
    last_calc = load_node(workflow_info['last_calc_nodeinfo']['uuid'])
    out_dict = {'last_calc_uuid:': last_calc.uuid}
    magmom_all = np.array(output_parameters['magnetism_group']['spin_moment_per_atom'], dtype=float)[:,-1]
    out_dict['magmoms'] = magmom_all
    return Dict(dict=out_dict)
    
@calcfunction
def parse_Jij(retrieved, impurity_info):
    """parser output of Jij calculation and return as ArrayData node"""

    _FILENAME_TAR = 'output_all.tar.gz'

    if _FILENAME_TAR in retrieved.list_object_names():
        # get path of tarfile
        with retrieved.open(_FILENAME_TAR) as tf:
            tfpath = tf.name
        # extract file from tarfile of retrieved to tempfolder
        with tarfile.open(tfpath) as tf:
            tar_filenames = [ifile.name for ifile in tf.getmembers()]
            filename = 'out_Jijmatrix'
            if filename in tar_filenames:
                tf.extract(filename, tfpath.replace(_FILENAME_TAR,'')) # extract to tempfolder

    jijdata = np.loadtxt(tfpath.replace(_FILENAME_TAR,'')+'out_Jijmatrix')

    pos = np.array(impurity_info['imp_cls'])
    z = np.array(impurity_info['imp_cls'])[:,4]
    Vpos = np.where(z==23)[0]

    Ry2eV = get_Ry2eV()

    # extract number of atoms
    natom = int(np.sqrt(jijdata.shape[0]/3/3))

    # reshape data
    jij_reshape = jijdata.reshape(3, natom, natom, 3, 3) # iter, i, j, k, l (Jij_k,l matrix)

    # now combine iterations to get full 3 by 3 Jij matrices for all atom pairs
    jij_combined_iter = np.zeros((natom, natom, 3, 3))
    for iatom in range(natom):
        for jatom in range(natom):
            for iiter in range(3):
                if iiter==0:
                    # first iteration with theta, phi = 0, 0
                    # take complete upper block from here since this calculation should be converged best
                    # (rotated moments only one-shot calculations)
                    jij_combined_iter[iatom, jatom, 0, 0] = jij_reshape[iiter, iatom, jatom, 0, 0]
                    jij_combined_iter[iatom, jatom, 0, 1] = jij_reshape[iiter, iatom, jatom, 0, 1]
                    jij_combined_iter[iatom, jatom, 1, 0] = jij_reshape[iiter, iatom, jatom, 1, 0]
                    jij_combined_iter[iatom, jatom, 1, 1] = jij_reshape[iiter, iatom, jatom, 1, 1]
                elif iiter==1:
                    # second iteraton with theta, phi = 90, 0
                    jij_combined_iter[iatom, jatom, 1, 2] = jij_reshape[iiter, iatom, jatom, 1, 2]
                    jij_combined_iter[iatom, jatom, 2, 1] = jij_reshape[iiter, iatom, jatom, 2, 1]
                    jij_combined_iter[iatom, jatom, 2, 2] = jij_reshape[iiter, iatom, jatom, 2, 2]
                else:
                    # from third iteration with theta, phi = 90, 90
                    jij_combined_iter[iatom, jatom, 0, 2] = jij_reshape[iiter, iatom, jatom, 0, 2]
                    jij_combined_iter[iatom, jatom, 2, 0] = jij_reshape[iiter, iatom, jatom, 2, 0]
                    # add this value to z-z component and average
                    jij_combined_iter[iatom, jatom, 2, 2] += jij_reshape[iiter, iatom, jatom, 2, 2]
                    jij_combined_iter[iatom, jatom, 2, 2] *= 0.5

    # finally convert to meV units (and sign change to have positive number indicate ferromagnetism and negative number antiferromagnetism)
    jij_combined_iter *= -1.*Ry2eV*1000

    jij_trace = (jij_combined_iter[:,:,0,0]+jij_combined_iter[:,:,1,1]+jij_combined_iter[:,:,2,2])/3
    Dij_vec = np.array([(jij_combined_iter[:,:,1,2]-jij_combined_iter[:,:,2,1]), (jij_combined_iter[:,:,2,0]-jij_combined_iter[:,:,0,2]), (jij_combined_iter[:,:,0,1]-jij_combined_iter[:,:,1,0])])

    plotdata = []

    #return jij_combined_iter
    out_txt = "Output Jij values between V impurities:\ni   j     Jij (meV)       Dij(meV)        D/J\n-----------------------------------------------\n"
    for iatom in range(natom):
        for jatom in range(natom):
            if iatom!=jatom and iatom in Vpos and jatom in Vpos:
                J = jij_trace[iatom, jatom]
                Dx, Dy, Dz = Dij_vec[0, iatom , jatom], Dij_vec[1, iatom , jatom], Dij_vec[2, iatom , jatom]
                D = np.sqrt(Dx**2 + Dy**2 + Dz**2)
                out_txt += '%3i %3i %15.5e %15.5e %15.5e\n'%(iatom, jatom, J, D, D/J)
                rdiff = pos[jatom] - pos[iatom]
                plotdata.append([rdiff[0], rdiff[1], rdiff[2], J, D, Dx, Dy, Dz])
    plotdata = np.array(plotdata)
    
    a = ArrayData()
    a.set_array('JijData', plotdata)
    
    return {'Jijdata': a, 'info': Dict(dict={'text': out_txt})}


###############################################################################################################################

def prepare_geometry(struc):
    """helper function to get lattice information"""
    cell = np.array(struc.cell)
    pos_Sb1 = np.array(struc.sites[12].position)
    pos_Sb2 = np.array(struc.sites[16].position)
    a = cell[0]
    b = cell[1]
    c = (pos_Sb2-pos_Sb1)
    
    pos_base = np.array([i.position for i in struc.sites[10:20]])
    name_base = np.array([i.kind_name for i in struc.sites[10:20]])
    zat = np.array([52,0,51,0,52,0,51,0,52,0])
    ilayer = np.arange(10,21)
    
    return a, b, c, pos_base, name_base, zat, ilayer


def check_pos_is_in(pos, R00=None, xlim=None, ylim=None, a=None, b=None):
    """Check if position is in circle or box around the center"""
    if R00 is not None:
        is_in = np.sqrt(np.sum(pos[:2]**2))<R00
    else:
        is_in = True
        if pos[0]<xlim[0] or pos[0]>xlim[1]:
            is_in = False
        if pos[1]<ylim[0] or pos[1]>ylim[1]:
            is_in = False
    return is_in


def create_random_positions(struc, R00=None, cimp=0.1, R0=0, plotting=True, verbose=True, xlim=None, ylim=None, Sb_only=False, return_bravais=False):
    """create a set of random impurities"""
    
    a, b, c, pos_base, name_base, zat, ilayer = prepare_geometry(struc)
    
    if Sb_only:
        pos_base = pos_base[[2,6]]
        name_base = name_base[[2,6]]
        ilayer = ilayer[[2,6]]
        zat = zat[[2,6]]

    pos_box_big0 = []
    pos_box_big = []
    ipos_small = []
    jjj = -1
    NmaxSb = 0
    
    if R00 is not None:
        for i in tqdm(range(-40, 41)):
            for j in range(-40, 41):
                for k in range(len(pos_base)):
                    pos = pos_base[k]+i*a+j*b
                    if check_pos_is_in(pos, R00=R00+10):
                        pos_box_big0.append([pos[0], pos[1], pos[2], ilayer[k], zat[k], name_base[k]])
                        jjj+=1
                    if check_pos_is_in(pos, R00=R00):
                        pos_box_big.append([pos[0], pos[1], pos[2]])
                        if name_base[k]=='Sb':
                            ipos_small.append(jjj)
                            NmaxSb+=1
    else:
        for i in tqdm(range(xlim[0], xlim[1])):
            for j in range(ylim[0], ylim[1]):
                for k in range(len(pos_base)):
                    pos = pos_base[k]+i*a+j*b
                    pos_box_big0.append([pos[0], pos[1], pos[2], ilayer[k], zat[k], name_base[k]])
                    jjj+=1
                    pos_box_big.append([pos[0], pos[1], pos[2]])
                    if name_base[k]=='Sb':
                        ipos_small.append(jjj)
                        NmaxSb+=1

    pos_box_big = np.array(pos_box_big)

    Nmax = len(pos_box_big0)
    if verbose: print('Npos, NSb:', Nmax, NmaxSb)

    Nimp = int(cimp*NmaxSb)
    if verbose: print('Nimp', Nimp)

    dd = np.array([np.sqrt(np.sum(np.array(pos_box_big0[i][:3])**2)) for i in ipos_small])
    i00 = ipos_small[np.where(dd==dd.min())[0][0]]

    iimppos = [i00]
    # randomly place impurities into the box
    for i in tqdm(range(Nimp-1)): #
        tmp = i00    
        #if verbose: print(tmp in iimppos, tmp not in ipos_small, pos_box_big0[tmp][-1]!='Sb')
        while (tmp in iimppos
               or tmp not in ipos_small
               or pos_box_big0[tmp][-1]!='Sb'
              ):
            tmp = randint(0, Nmax-1)

        iimppos.append(tmp)
    iimppos = np.array(iimppos)


    scoef = []

    pos_all0 = np.array([i[:5] for i in pos_box_big0])
    for i in tqdm(iimppos[:]):
        p = np.array(pos_box_big0[i][:3])
        dd = (np.sqrt(np.sum((pos_all0[:,:3]-p)**2, axis=1)))
        mm = dd.argsort()
        dd, pos_all = dd[mm], pos_all0[mm]
        jj = 0
        while dd[jj]<=0.1: #R0:
        #while dd[jj]<=R0:
            scoef.append(pos_all[jj])
            jj+=1
    scoef = np.array(scoef)

    if verbose: print('num in cls:', len(set(scoef[:,0]+100*scoef[:,1]+100**2*scoef[:,2])))


    imppos = np.array([pos_box_big0[i][:3] for i in iimppos])

    imppos[:,:3] = imppos[:,:3] - scoef[0,:3]
    scoef[:,:3] = scoef[:,:3] - scoef[0,:3]

    if plotting:
        plt.figure(figsize=(12,8))
        #plt.scatter(scoef[:,0], scoef[:,1], 50*(scoef[:,4]-50), c=scoef[:,4], vmin=51);
        #plt.colorbar()
        #plt.plot(imppos[:,0], imppos[:,1], k*', ms=20);
        plt.plot(imppos[imppos[:,2]>0.1][:,0], imppos[imppos[:,2]>0.1][:,1], 'o', color='C0')
        plt.plot(imppos[imppos[:,2]<0.1][:,0], imppos[imppos[:,2]<0.1][:,1], 'o', color='C1')
        plt.plot(imppos[0,0], imppos[0,1], 'x');

        theta = np.linspace(0, 2*np.pi, 100)
        for i in imppos:
            ra = R0*np.cos(theta)+i[0]
            rb = R0*np.sin(theta)+i[1]
            axes = plt.gca()
            axes.plot(ra, rb, color='b', lw=0.2)

        if R00 is not None:
            theta = np.linspace(0, 2*np.pi, 100)
            ra = R00*np.cos(theta)
            rb = R00*np.sin(theta)
            axes = plt.gca()
            axes.plot(ra, rb, color='k')
        else:
            a00 = a*xlim[0]+b*ylim[0]
            a01 = a*xlim[0]+b*ylim[1]
            a10 = a*xlim[1]+b*ylim[0]
            a11 = a*xlim[1]+b*ylim[1]
            box = np.array([a00, a01, a11, a10, a00])
            plt.plot(box[:,0], box[:,1], 'k')
        
        plt.axis('equal')
        
    alat = get_alat_from_bravais(np.array(struc.cell), struc.pbc[2])
    scoef[:,:3] *= 1/alat

    if not return_bravais:
        return scoef, NmaxSb
    else:
        return scoef, NmaxSb, alat, a, b, c


###############################################################################################################################

def get_mindist(last_calc):
    scoef = np.array(last_calc.inputs.impurity_info['imp_cls'])
    pos_imps = scoef[scoef[:,4]==23.0][:,:3]
    
    dist_min = []
    for p in pos_imps:
        dists = np.sqrt(np.sum((p-pos_imps)**2, axis=1))
        dists = np.sort(dists)
        #print(np.round(dists[1:], 4))
        dmin = np.round(dists[1], 4)
        dist_min.append(dmin)
        
    return dist_min

def get_moments_imps(last_calc):    
    scoef = np.array(last_calc.inputs.impurity_info['imp_cls'])
    
    pos_imps1 = scoef[scoef[:,4]==23.0][scoef[scoef[:,4]==23.0][:,3]==13, :]
    pos_imps2 = scoef[scoef[:,4]==23.0][scoef[scoef[:,4]==23.0][:,3]==17, :]
    
    magmom_all = np.array(last_calc.outputs.output_parameters['magnetism_group']['spin_moment_per_atom'], dtype=float)[:,-1]
    m_imps = magmom_all[scoef[:,4]==23.0]
    m_imps1 = m_imps[scoef[scoef[:,4]==23.0][:,3]==13]
    m_imps2 = m_imps[scoef[scoef[:,4]==23.0][:,3]==17]
    
    orbmom_all = np.array(last_calc.outputs.output_parameters['magnetism_group']['orbital_moment_per_atom'], dtype=float)[:,-1]
    om_imps = orbmom_all[scoef[:,4]==23.0]
    om_imps1 = om_imps[scoef[scoef[:,4]==23.0][:,3]==13]
    om_imps2 = om_imps[scoef[scoef[:,4]==23.0][:,3]==17]

    return m_imps, m_imps1, m_imps2, om_imps1, om_imps2, magmom_all

def get_mag_moms_all(calcs_ok):
    """
    extract and collect the spin and orbital moments of the impurities
    """    
    mimps1, mimps2, oimps1, oimps2 = [], [], [], []
    mimps_all = []
    dists = []

    for calc in tqdm(calcs_ok[:-1]):
        last_calc = load_node(calc.outputs.results['last_calc_uuid:'])
        scoef = np.array(last_calc.inputs.impurity_info['imp_cls'])

        moms = get_moments_imps(last_calc)
        mimps_all += list(moms[0])
        if len(moms[1])>0: mimps1 += list(moms[1])
        if len(moms[2])>0: mimps2 += list(moms[2])
        if len(moms[3])>0: oimps1 += list(moms[3])
        if len(moms[4])>0: oimps2 += list(moms[4])
        dists += get_mindist(last_calc)

    mimps_all = np.array(mimps_all)
    mimps1, mimps2, oimps1, oimps2 = np.array(mimps1), np.array(mimps2), np.array(oimps1), np.array(oimps2)
    dists = np.array(dists)

    return mimps_all, mimps1, mimps2, oimps1, oimps2, scoef, moms

def get_jijdata(calc):
    jijdata = calc.outputs.JijData.get_array('JijData')
    return jijdata

def get_jijs_all(calcs_ok):
    """
    collect the jij infos for all configurations
    """
    jijs = []
    for calc in tqdm(calcs_ok):
         jijs += list(get_jijdata(calc))
    jijs = np.array(jijs)
    #[rdiff[0], rdiff[1], rdiff[2], J, D, Dx, Dy, Dz])
    
    return jijs

def plot_j_d_vs_r(jijs):
    """
    create a plot to sho Jij(r) and |Dij|(r) as well as the D/J ratio
    """
    plt.figure(figsize=(12,12))

    plt.subplot(3,1,1)
    plt.axhline(0, color='grey', ls=':')
    x=np.round(np.sqrt(np.sum(jijs[:,:3]**2, axis=1)),2)
    meds = []
    for xi in np.sort(list(set(x))):
        d = jijs[:,3][x==xi]
        o = plt.boxplot(d, positions=[xi], manage_ticks=False)
        meds.append([xi, np.median(d)])
    meds = np.array(meds)
    plt.plot(x, jijs[:,3], '.', label='Jij')
    #plt.plot(meds[:,0], meds[:,1], '--', label='Jij', lw=3)
    #plt.xlabel('distance ($a_{lat}$)', fontsize='x-large')
    plt.ylabel('$J_{ij}$ (meV)', fontsize='x-large')
    plt.xlim(0.9,5.3)


    plt.subplot(3,1,2)
    plt.axhline(0, color='grey', ls=':')
    meds = []
    for xi in np.sort(list(set(x))):
        d = np.sqrt(np.sum(jijs[:,5:8]**2, axis=1))[x==xi]
        o = plt.boxplot(d, positions=[xi], manage_ticks=False)
        meds.append([xi, np.median(d)])
    meds = np.array(meds)
    plt.plot(x, np.sqrt(np.sum(jijs[:,5:8]**2, axis=1)), '.', label='Dij')
    #plt.plot(meds[:,0], meds[:,1], '--', label='Dij', lw=3)
    plt.xlabel('distance ($a_{lat}$)', fontsize='x-large')
    plt.ylabel('$|D_{ij}|$ (meV)', fontsize='x-large')
    plt.xlim(0.9,5.3)


    plt.subplot(3,1,3)
    plt.plot(x, abs(np.sqrt(np.sum(jijs[:,5:8]**2, axis=1))/jijs[:,3]), '.', label='D/J')
    plt.xlim(0.9,5.3)
    plt.ylim(0, 10)
    plt.xlabel('distance ($a_{lat}$)', fontsize='x-large')
    plt.ylabel('|$D$ / $J$|', fontsize='x-large')

    plt.subplots_adjust(hspace=0.1, top=0.95, right=0.99, left=0.1, bottom=0.1)

    plt.show()
    
def average_jd(jijs, plotting=False):
    """
    calculate average values by finding equivalent pairs and taking the average value
    """

    # rotation matrices for 120 and 240 degree rotation
    rotmat0 = np.matrix([[1, 0], [0, 1]])
    a = 120./180.*np.pi
    rotmat1 = np.matrix([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
    a = 240./180.*np.pi
    rotmat2 = np.matrix([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
    
    #mirror = np.matrix([[-1, 0], [0, 1]])
    
    #print(rotmat0)
    #print(rotmat1)
    #print(rotmat2)
    
    def add_to_list(jij_aver, dists, j1):
        if dists.min()>1e-3:
            # append this entry to the output list
            jij_aver.append(list(j1)+[1])
            jij_aver[-1][0] = r[0]
            jij_aver[-1][1] = r[1]
        else:
            # foiund position already, sum the values for averaging
            m = dists.argsort()[0]
            for k in range(3, len(j1)):
                # sum up J and D values
                jij_aver[m][k] += j1[k]
            # sum count index for averaging
            jij_aver[m][-1] += 1
            jij_aver[m][0] = r[0]
            jij_aver[m][1] = r[1]
        return jij_aver
    
    def get_dist(jij_aver, r):
        # take care of first iteration
        if len(jij_aver)==0:
            dists = np.array([1])
        else:
            dists = np.sqrt(np.sum((r-np.array(jij_aver)[:,:2])**2, axis=1))
        return dists
    
    # now do 120 and 240 degree rotations
    jij_aver = []
    for j in tqdm(jijs):
        r0 = j[:2]
        for irot, rotmat in enumerate([rotmat0, rotmat1, rotmat2]):
            # take into account 120 and 240 degree rotation
            r = np.array((rotmat*np.matrix(r0).transpose()).transpose())[0]
            
            # rotate DMI vector, since we rotate around z we only transform x,y
            dvec = j[5:7]
            dvec_rot = np.array((rotmat*np.matrix(dvec).transpose()).transpose())[0]
            j1 = j.copy(); j1[5:7] = dvec_rot
            #print(irot, dvec, dvec_rot)
            
            dists = get_dist(jij_aver, r)
            jij_aver = add_to_list(jij_aver, dists, j1)
            
    # divide by number of pairs that were summed to do the averaging
    jij_aver = np.array(jij_aver)
    for k in range(3, len(j)):
        jij_aver[:,k] *= 1/jij_aver[:,-1]
        
    if plotting:
        plt.figure(figsize=(16,9))

        n = np.sqrt(jij_aver[:,5]**2+jij_aver[:,6]**2) #+jij_aver[:,7]**2)
        #n = np.log(n); n = (n-n.min())/(n.max()-n.min()); 
        #n[n>0.9] *= 0.8
        #print(np.sort(n))

        plt.quiver(jij_aver[:,0], jij_aver[:,1], jij_aver[:,5], jij_aver[:,6], jij_aver[:,7], pivot='middle', cmap='RdYlGn', scale=20)#scale=20/n)
        plt.axis('equal')
        cbar = plt.colorbar()
        cbar.set_label('$D_{ij}^z$ (meV)', fontsize=20)
    
    # return averaged values
    return jij_aver


def get_jij_cmap(vmin, vmax):
    """
    make blue-white-red cmap for jij plot
    """
    newcmp = LinearSegmentedColormap.from_list('my_cmap', [[0.0, 'blue'], [abs(vmin)/(vmax-vmin), 'white'], [1.0, 'red']])
    return newcmp


def plot_jij_dij_maps(jij_aver, vmin=-10, vmax=15):
    """
    plot the jij and dij maps
    """
    s = 330
    newcmp = get_jij_cmap(vmin, vmax)

    plt.figure(figsize=(16,12))
    plt.subplot(2,2,1)
    #plt.hexbin(jij_aver[:,0], jijs_aver[:,1], C=jij_aver[:,3], gridsize=101)
    #plt.hexbin(jij_aver[:,0], jij_aver[:,1], C=jij_aver[:,3], gridsize=101)

    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=jij_aver[:,3], s=s, marker='H', cmap=newcmp, vmin=vmin, vmax=vmax, ec='lightgrey', )
    plt.axis('equal')
    cbar = plt.colorbar()
    cbar.set_label('$J_{ij}$ (meV)', fontsize='x-large')
    plt.ylabel('y ($a_{lat}$)', fontsize='x-large')


    plt.subplot(2,2,2)
    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=np.sqrt(jij_aver[:,5]**2+jij_aver[:,6]**2+jij_aver[:,7]**2),
                s=s, marker='H', ec='lightgrey', norm=matplotlib.colors.LogNorm(), vmin=0.1)
    plt.axis('equal')
    cbar = plt.colorbar()
    cbar.set_label('$|D_{ij}|$ (meV)', fontsize='x-large')


    plt.subplot(2,2,3)
    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=abs(jij_aver[:,3]), s=s, marker='H', ec='lightgrey', norm=matplotlib.colors.LogNorm(), vmin=0.1)
    plt.axis('equal')
    cbar = plt.colorbar()
    cbar.set_label('$|J_{ij}|$ (meV)', fontsize='x-large')
    plt.xlabel('x ($a_{lat}$)', fontsize='x-large')
    plt.ylabel('y ($a_{lat}$)', fontsize='x-large')

    plt.subplot(2,2,4)
    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=jij_aver[:,-1], s=s, marker='H', ec='lightgrey', norm=matplotlib.colors.LogNorm())
    plt.axis('equal')
    cbar = plt.colorbar()
    cbar.set_label('count', fontsize='x-large')
    plt.xlabel('x ($a_{lat}$)', fontsize='x-large')
    """
    plt.subplot(2,2,4)
    n = np.sqrt(jij_aver[:,5]**2+jij_aver[:,6]**2+jij_aver[:,7]**2)
    plt.quiver(jij_aver[:,0], jij_aver[:,1], jij_aver[:,5]/n, jij_aver[:,6]/n, jij_aver[:,7], )
    plt.axis('equal')
    cbar = plt.colorbar()
    cbar.set_label('$D_{ij}^z$ (meV)', fontsize=20)
    """

    plt.subplots_adjust(wspace=0.1, hspace=0.1, top=0.95, right=0.99, left=0.1, bottom=0.1)
    
    
    plt.figure(figsize=(8,8))
    n = np.sqrt((jij_aver[:,4])**2+(jij_aver[:,3])**2)
    n = (n-n.min())/(n.max()-n.min())
    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=abs(jij_aver[:,4]/jij_aver[:,3])*n,
                s=s, marker='H', ec='lightgrey', norm=matplotlib.colors.LogNorm(), vmin=1e-4)
    plt.axis('equal')
    cbar = plt.colorbar()
    cbar.set_label('D/J normed', fontsize='x-large')
    plt.xlabel('x ($a_{lat}$)', fontsize='x-large')
    plt.ylabel('y ($a_{lat}$)', fontsize='x-large')
    
    
    theta = np.linspace(0, 2*np.pi, 100)
    ra = 3.5 * np.cos(theta)
    rb = 3.5 * np.sin(theta)
    axes = plt.gca()
    axes.plot(ra, rb, color='k')

    plt.show()
    
    
def find_host_positions(struc):
    """
    find number of Sb neighbors (i.e. possible V positions) for normalization
    """
    cell = np.array(struc.cell)
    pos_Sb1 = np.array(struc.sites[12].position)
    pos_Sb2 = np.array(struc.sites[16].position)
    a = cell[0]
    b = cell[1]
    c = (pos_Sb2-pos_Sb1)
    alat = np.sqrt(np.sum(a**2))

    pos_all = []
    for i in tqdm(range(-20, 21)):
        for j in range(-20,21):
            for k in range(2):
                p = i*a+j*b+k*c
                if np.sqrt(np.sum(p**2))<5.5*alat:
                    pos_all.append(list(p)+[k])
    pos_all = np.array(pos_all)

    #plt.figure(figsize=(15,8))
    #plt.scatter(pos_all[:,0]/alat, pos_all[:,1]/alat, c=pos_all[:,2]/alat, s=60, marker='H', ec='lightgrey', )
    #plt.axis('equal')

    return pos_all, alat

def plot_imp_distribution(jij_aver, pos_all, alat):
    """
    visualize impurity distribution
    """

    bins = 25
    drange = (0.9, 5.3)

    plt.figure(figsize=(12,12))
    plt.subplot(3,1,1)
    h1 = plt.hist(np.sqrt(np.sum(jij_aver[:,:3]**2, axis=1)), weights=jij_aver[:,-1], bins=bins, range=drange, density=True, width=0.15)
    #plt.xlabel('distance ($a_{lat}$)')
    plt.ylabel('frequency', fontsize='x-large')
    #plt.title('')

    plt.subplot(3,1,2)
    h2 = plt.hist(np.sqrt(np.sum(pos_all[:,:3]**2, axis=1))/alat, bins=bins, range=drange, density=False, width=0.15)
    #plt.xlabel('distance ($a_{lat}$)')
    plt.ylabel('number of neighbors', fontsize='x-large')

    plt.subplot(3,1,3)
    plt.bar((h1[1][:-1]+h1[1][1:])/2, h1[0]/h2[0], width=0.15)
    plt.ylabel('normalized frequency', fontsize='x-large')
    plt.xlabel('distance ($a_{lat}$)', fontsize='x-large')

    plt.suptitle('Distribution of impurity distances', fontsize='x-large')
    plt.subplots_adjust(hspace=0.1, top=0.95, right=0.99, left=0.1, bottom=0.1)
    plt.show()
    
    return h1, h2

def gauss(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def gauss0(x,a,sigma):
    return gauss(x,a,0,sigma)

def gauss1(x,a,sigma):
    return gauss(x,a,1,sigma)
    
def fit_gauss(h1, h2):
    """
    fit gaussian function to values of histogram
    """
    from scipy.optimize import curve_fit

    x = (h1[1][:-1]+h1[1][1:])/2
    y = np.nan_to_num(h1[0]/h2[0]/sum(np.nan_to_num(h1[0]/h2[0])))
    # remove nans
    x = x[y>0]
    y = y[y>0]

    n = len(x)
    mean = 1
    sigma = sum(y*(x-mean)**2)/n

    #popt,pcov = curve_fit(gauss,x,y,p0=[1,0,sigma])
    #print(popt, pcov)
    #popt0,pcov0 = curve_fit(gauss0,x,y,p0=[1,sigma])
    #print(popt0, pcov0)
    popt1,pcov1 = curve_fit(gauss1,x,y,p0=[1,sigma])
    print(popt1, pcov1)

    xd = np.linspace(0.7, 6, 1000)

    plt.figure()
    plt.plot(x,y, 'o', label='data')
    #plt.plot(xd, gauss(xd, popt[0], popt[1], popt[2]), '-', label='fit')
    #plt.plot(xd, gauss0(xd, popt0[0], popt0[1]), '-', label='fit 0')
    plt.plot(xd, gauss1(xd, popt1[0], popt1[1]), '-', label='fit')
    plt.legend()
    plt.show()
    
    return xd, popt1


def plot_summary(cimp, pos_all, alat, R00, scoef, moms, mimps1, mimps2, l_calcs_ok, mimps_all, oimps1, oimps2, jij_aver, jijs, h1, h2, xd, popt1, newcmp, vmin, vmax):
    """
    make publication-ready figure
    """

    fig = plt.figure(figsize=(20,12))
    gs = fig.add_gridspec(6,6)

    anno_opts = dict(xy=(-0.10, 0.98), xycoords='axes fraction', weight='bold',
                     va='center', ha='center', fontsize='xx-large')
    
    
    # convert to array
    pos_all = np.array(pos_all)
    scoef = np.array(scoef)
    moms = np.array(moms)
    mimps1 = np.array(mimps1)
    mimps2 = np.array(mimps2)
    mimps_all = np.array(mimps_all)
    oimps1 = np.array(oimps1)
    oimps2 = np.array(oimps2)
    jij_aver = np.array(jij_aver)
    jijs = np.array(jijs)
    xd = np.array(xd)
    
    ###############################################   a   #################################################
    # example plot of impurity configuration
    ax01 = fig.add_subplot(gs[:2,:2])
    #plt.scatter(pos_all[:,0]/alat, pos_all[:,1]/alat, c=pos_all[:,2], marker='H', s=150, cmap=cm.RdBu, alpha=0.2)
    plt.scatter(pos_all[pos_all[:,-1]==0][:,0]/alat, pos_all[pos_all[:,-1]==0][:,1]/alat, marker='H', s=150, color='r', alpha=0.2, label='Sb1')
    plt.scatter(pos_all[pos_all[:,-1]==1][:,0]/alat, pos_all[pos_all[:,-1]==1][:,1]/alat, marker='H', s=150, color='b', alpha=0.2, label='Sb2')
    plt.legend(fontsize='large', loc=4)

    theta = np.linspace(0, 2*np.pi, 100)
    ra = R00*np.cos(theta)/alat
    rb = R00*np.sin(theta)/alat
    axes = plt.gca()
    axes.plot(ra, rb, color='k')
    plt.scatter(scoef[scoef[:,4]==23.][:,0], scoef[scoef[:,4]==23.][:,1], c=moms[0], ec='k', s=200)
    #n = np.log10(abs(moms[-1])); n = (n-n.min())/(n.max()-n.min())
    #plt.scatter(scoef[:,0], scoef[:,1], 500*n, c=moms[-1], ec='grey', norm=matplotlib.colors.LogNorm())
    cbar = plt.colorbar()
    cbar.set_label('$m^{imp}$ ($\mu_B$)', fontsize='x-large', rotation=270, labelpad=25)
    plt.axis('equal')
    plt.ylim(-3,3)
    plt.xlim(-3+0.8,3+0.8)
    plt.text(2.6, 2., s='$c_{imp}$=%.2f'%(cimp), fontsize='x-large', bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'grey'})
    plt.xlabel('x ($a_{lat}$)', fontsize='large')
    plt.ylabel('y ($a_{lat}$)', fontsize='large')
    plt.annotate('a', **anno_opts)

    ###############################################   b   #################################################
    # spin moments histogram
    ax02 = fig.add_subplot(gs[2:4,:2])
    bins=20
    plt.hist(list(mimps1)+list(mimps2), edgecolor='k', bins=bins, width=0.005)
    plt.axvline(np.mean(list(mimps1)+list(mimps2)), ls='--', label='mean', color='C1')
    plt.axvline(np.median(list(mimps1)+list(mimps2)), ls=':', label='median', color='C2')
    plt.legend(loc=1, fontsize='large')
    plt.xlabel('spin moment ($\mu_B$)', fontsize='x-large')
    plt.ylabel('count', fontsize='large')
    plt.text(0.05, 0.75, s='%i configurations\n%i impurities\n%i @ Sb1\n%i @ Sb2'%(l_calcs_ok, len(mimps_all), len(mimps1), len(mimps2)),
             fontsize='large', bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'grey'}, transform=plt.gca().transAxes)
    plt.annotate('b', **anno_opts)

    ###############################################   c   #################################################
    # orbital moments histogram
    ax03 = fig.add_subplot(gs[4:,:2])
    plt.hist(list(oimps1)+list(oimps2), edgecolor='k', bins=bins, width=0.006)
    plt.axvline(np.mean(list(oimps1)+list(oimps2)), ls='--', label='mean', color='C1')
    plt.axvline(np.median(list(oimps1)+list(oimps2)), ls=':', label='median', color='C2')
    plt.legend(loc=1, fontsize='large')
    plt.xlabel('orbital moment ($\mu_B$)', fontsize='x-large')
    plt.ylabel('count', fontsize='large')
    plt.annotate('c', **anno_opts)

    ###############################################   d   #################################################
    # Jij map
    ax1 = fig.add_subplot(gs[:3,2:4])
    s = 400
    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=jij_aver[:,3], s=s, marker='H', cmap=newcmp, vmin=vmin, vmax=vmax, ec='lightgrey', )
    plt.axis('equal')
    plt.xlim(-5, 5)
    plt.ylim(-6,6)
    cbar = plt.colorbar()
    cbar.set_label('$J_{ij}$ (meV)', fontsize='large', rotation=270, labelpad=20)
    plt.ylabel('y ($a_{lat}$)', fontsize='large')
    plt.annotate('d', **anno_opts)

    ###############################################   e   #################################################
    # Dij map
    ax2 = fig.add_subplot(gs[3:,2:4])
    plt.scatter(jij_aver[:,0], jij_aver[:,1], c=np.sqrt(np.sum(jij_aver[:,5:8]**2, axis=1)), s=s, marker='H', ec='lightgrey', )#norm=matplotlib.colors.LogNorm())
    plt.axis('equal')
    plt.xlim(-5, 5)
    plt.ylim(-6,6)
    cbar = plt.colorbar()
    cbar.set_label('$|D_{ij}|$ (meV)', fontsize='large', rotation=270, labelpad=20)
    plt.ylabel('y ($a_{lat}$)', fontsize='large')
    plt.xlabel('x ($a_{lat}$)', fontsize='large')
    plt.annotate('e', **anno_opts)


    ###############################################   f   #################################################
    ax3 = fig.add_subplot(gs[:2,4:])
    plt.axhline(0, color='grey', ls=':')
    x=np.round(np.sqrt(np.sum(jijs[:,:3]**2, axis=1)),2)
    for xi in np.sort(list(set(x))):
        d = jijs[:,3][x==xi]
        o = plt.boxplot(d, positions=[xi], manage_ticks=False)
    plt.plot(x, jijs[:,3], '.', label='Jij')
    plt.ylabel('$J_{ij}$ (meV)', fontsize='large')
    plt.xlim(0.9,5.3)
    plt.annotate('f', **anno_opts)


    ###############################################   g   #################################################
    ax4 = fig.add_subplot(gs[2:4,4:])
    plt.axhline(0, color='grey', ls=':')
    for xi in np.sort(list(set(x))):
        d = np.sqrt(np.sum(jijs[:,5:8]**2, axis=1))[x==xi]
        o = plt.boxplot(d, positions=[xi], manage_ticks=False)
    plt.plot(x, np.sqrt(np.sum(jijs[:,5:8]**2, axis=1)), '.', label='Dij')
    plt.ylabel('$|D_{ij}|$ (meV)', fontsize='large')
    plt.xlim(0.9,5.3)
    plt.annotate('g', **anno_opts)

    ###############################################   h   #################################################
    # impurity distance distribution
    ax5 = fig.add_subplot(gs[4:,4:])
    plt.bar((h1[1][:-1]+h1[1][1:])/2, h1[0]/h2[0]/sum(np.nan_to_num(h1[0]/h2[0])), width=0.15, edgecolor='k')
    plt.plot(xd, gauss1(xd, popt1[0], popt1[1]), '-', label='gaussian fit', color='C1', lw=2)
    plt.legend(loc=1, fontsize='large')
    plt.ylabel('normalized frequency', fontsize='large')
    plt.xlabel('distance ($a_{lat}$)', fontsize='large')
    plt.xlim(0.9,5.3)
    plt.annotate('h', **anno_opts)

    # some formatting
    plt.subplots_adjust(hspace=0.4, wspace=0.45, top=0.99, bottom=0.05, left=0.05, right=0.99)
    plt.show()

    """
    a
    """
    




