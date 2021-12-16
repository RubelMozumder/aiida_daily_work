# CPA Calculation

## Impurity calculation:

### V vs (V, Cr, Mn, Mo)
imp1 il1 conc1   imp2 il2 conc file_name
V    3     0.5   V    4   0.5   V_V_CPA
V    3     0.1   Cr   4   0.5   V_Cr_CPA
V    3     0.1   Mn   4   0.5   V_Mn_CPA
V    3     0.1   Mo   4   0.5   V_Mo_CPA


### Cr Vs (V, Cr, Mn, Mo)
imp1 il1 conc1   imp2 il2 conc file_name
Cr   3     0.5   Cr   4   0.5   Cr_Cr_CPA
Cr   3     0.1   Mn   4   0.5   Cr_Mn_CPA
Cr   3     0.1   Mo   4   0.5   Cr_Mo_CPA
    Cr   3     0.1   V    4   0.5   Cr_V_CPA (Not exist)


### Mn Vs (V, Cr, Mn, Mo)
imp1 il1 conc1   imp2 il2 conc file_name
Mn   3     0.5   Mn   4   0.5   Mn_Mn_CPA
Mn   3     0.1   Mo   4   0.5   Mn_Mo_CPA    
    Mn   3     0.1   V    4   0.5   Mn_V_CPA (Not exist)
    Mn   3     0.1   Cr   4   0.5   Mn_Cr_CPA (Not exist)


### Mo vs (V, Cr, Mn, Mo)
imp1 il1 conc1   imp2 il2 conc file_name
Mo    3     0.5   Mo    4   0.5   Mo_Mo_CPA
    Mo    3     0.1   Cr   4   0.5   Mo_Cr_CPA  (Not exist)
    Mo    3     0.1   Mn   4   0.5   Mo_Mn_CPA  (Not exist)
    Mo    3     0.1   V   4   0.5   Mo_V_CPA  (Not exist)