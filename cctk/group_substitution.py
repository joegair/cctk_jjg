import numpy as np
import math
import re
import copy

from cctk import Molecule, Group
from cctk.helper_functions import get_covalent_radius, compute_angle_between, compute_rotation_matrix

#### Helper file to deal with group substitution, since the code gets a bit hairy

def add_group_to_molecule(molecule, group, add_to):
    """
    Adds a `Group` object to a `Molecule` at the specified atom, and returns a new `Molecule` object (generated using `copy.deepcopy()`).
    Automatically attempts to detect clashes by rotating group until no clashes are found

    The atom in `group` that replaces `add_to` in `molecule` will inherit the number of `add_to` - however, the other atoms in `group` will be appended to the atom list.

    Args:
        molecule (Molecule): the molecule to change
        group (Group): the group to affix
        add_to (int): the 1-indexed atom number on `molecule` to add `group` to
    """
    #### this code can be a bit complex: for an example, let's imagine converting benzene to toluene by adding methane (Group) to benzene (Molecule)
    ####     add_to would be the benzene H (atom on Molecule you replace with the new group)
    ####     adjacent_atom would be the benzene C
    ####     group.attach_to would be the methane H
    ####     group.adjacent would be the methane C

    #### prevent in-place modification of molecule - could lead to pernicious errors!
    molecule = copy.deepcopy(molecule)
    molecule._check_atom_number(add_to)

    adjacent_atom = molecule.get_adjacent_atoms(add_to)
    assert (len(adjacent_atom) == 1), "can't substitute an atom with more than one adjacent atom!"
    adjacent_atom = adjacent_atom[0]

    attach_to = group.attach_to
    other_indices = np.ones_like(group.atomic_numbers).astype(bool)
    other_indices[attach_to-1] = False
    other_indices[group.adjacent-1] = False

    #### we need to change the bond length somewhat to prevent strange behavior
    old_radius = get_covalent_radius(molecule.atomic_numbers[add_to-1])
    new_radius = get_covalent_radius(group.atomic_numbers[group.adjacent-1])
    delta_rad = new_radius - old_radius

    #### make the swap! (this only adds the atoms, still have to get the geometry right)
    molecule.atomic_numbers[add_to-1] = group.atomic_numbers[group.adjacent-1]
    new_indices = [i + molecule.num_atoms() for i in range(1,np.sum(other_indices)+1)]
    molecule.atomic_numbers.extend(np.array(group.atomic_numbers)[other_indices])

    #### have to keep track of what all the new indices are, to carry over connectivity
    new_indices.insert(group.adjacent-1, add_to)
    new_indices.insert(attach_to-1, adjacent_atom)

    #### adjust the bond length by moving add_to
    molecule.set_distance(adjacent_atom, add_to, molecule.get_distance(adjacent_atom, add_to) + delta_rad)

    #### rotate group to match the new positioning
    v_g = group.get_vector(group.attach_to, group.adjacent)
    v_m = molecule.get_vector(add_to, adjacent_atom)
    theta = compute_angle_between(v_g, v_m)

    #### rotate each atom and add it...
    new_center = molecule.get_vector(add_to)
    rot = compute_rotation_matrix(np.cross(v_g,v_m), -(180-theta))
    for vector in group.geometry[other_indices]:
        new_v = np.dot(rot, vector) + new_center
        molecule.geometry = np.vstack((molecule.geometry, new_v))

    #### now we have to merge the new bonds
    for (atom1, atom2) in group.bonds.edges():
        molecule.add_bond(new_indices[atom1-1], new_indices[atom2-1])

    assert (len(molecule.atomic_numbers) == len(molecule.geometry)), f"molecule has {len(molecule.atomic_numbers)} atoms but {len(molecule.geometry)} geometry elements!"

    #### now we want to find the "lowest" energy conformation, defined as the rotamer which minimizes the RMS distance between all atoms
    adjacent_on_old_molecule = molecule.get_adjacent_atoms(adjacent_atom)[0]
    adjacent_on_new_molecule = molecule.get_adjacent_atoms(add_to)[-1]
    molecule.optimize_dihedral(adjacent_on_old_molecule, adjacent_atom, add_to, adjacent_on_new_molecule)

    try:
        molecule.check_for_conflicts()
    except ValueError as error_msg:
        raise ValueError(f"molecule contains conflicts: {str(error_msg)}!")

    return molecule