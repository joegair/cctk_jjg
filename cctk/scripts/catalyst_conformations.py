import sys
import os
import numpy as np

sys.path.append(os.path.relpath('../cctk'))

from cctk import GaussianOptOutputFile, Molecule, GaussianInputFile

output_file = GaussianOptOutputFile('cctk/scripts/thiourea_catalyst.out')

if output_file.successful is False: 
    print("not successful!")

molecule = Molecule(output_file.atoms, output_file.get_final_geometry())
molecule.assign_connectivity()

if not os.path.exists('cctk/scripts/scan_angle'):
    os.makedirs('cctk/scripts/scan_angle')

angles = [0, 30, 60, 90, 120, 180]
molecule.set_dihedral(43, 27, 10, 12, 0)
for angle in angles:    
    molecule.set_dihedral(49, 9, 27, 43, angle)

    input_file = GaussianInputFile(molecule.atoms, molecule.geometry, header='#p opt b3lyp/midix') 
    input_file.write_file(filename=f"cctk/scripts/scan_angle/catalyst_{angle}.gjf")
