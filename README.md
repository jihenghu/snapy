# jupiter_gcm x1 face lists for chengcli/snapy#280

Data-only branch. These are stretched x1 grids for the jupiter_gcm column, with every cell satisfying dz <= H(z)/n:

| file | n | faces | cells | sha256 |
|---|---|---|---|---|
| `jupiter_gcm_faces_n5.csv` | 5 | 31 | 30 | `70e36e8503fb9651912faaf159bdfc51c22f985e594e8d85e1d2f02f141f8c7e` |
| `jupiter_gcm_faces_n10.csv` | 10 | 60 | 59 | `5eff3ab4b4c936049d8cca145f4ce7e29d5da6a4993db3a80f058cef09c15811` |

Source:
- chengcli/snapy main `2d9fa419be56513159c695267b68753d5b223b31`, deck `examples/jupiter_gcm.yaml`: x1 69911000-70211000 m (:59-60), grav1 -22 (:126-128), Ps 100e5 Pa, Ts 600 K, Tmin 110 K (:183-189).
- T(z) follows `examples/run_hydro.cpp:95-131`, generated with pip kintera 2.6.7. H = R T / (mu_gas g).
- Faces are built top-down so each cell satisfies dz <= H(centre)/n.

Columns: face index `i`, absolute `x1f_m`, height `z_face_m`. The remaining columns describe the cell between face i-1 and face i: `dz_below_m`, `z_centre_below_m`, `T_centre_K`, `H_centre_m`, `dz_over_H`, `r_dz_i_over_dz_i_minus_1`.
