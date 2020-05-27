import numpy as np
import re

from cctk.helper_functions import get_symbol
from cctk import OneIndexedArray, LazyLineObject

"""
Functions to help with parsing Gaussian files
"""

def read_geometries_and_energies(lines_obj):
    """
    A large and unwieldy method - reads geometries, symbol lists, and energies from the file.

    Args:
        lines (list): the list of lines in the file

    Returns:
        array of geometries (each of which itself is an array of arrays)
        list of atomic symbols
        array of energies
        array containing the number of SCF iterations per step
    """

    file_geometries = []
    file_symbol_lists = []
    file_energies = []
    file_scf_iterations = []

    this_geometry = []
    this_symbol_list = []
    this_energy = None

    i = 0

    #### we'll read this into memory to speed this up
    lines = list(lines_obj)

    in_geometry_block = False
    while i < len(lines):
        # read the current line
        line = lines[i].strip()

        # detect geometry block
        if (line == "Standard orientation:") or (re.search("Cartesian Coordinates", line) or re.search("Input orientation:", line)):
            i += 5
            in_geometry_block = True
            continue
        elif in_geometry_block and line.startswith("------"):
            i += 1
            in_geometry_block = False
            continue

        # read geometry if applicable
        if in_geometry_block:
            fields = re.split(" +", line)
            if len(fields) == 6:
                if len(this_geometry) > 0 and fields[0] == "1":
                    # reset fields
                    this_geometry = []
                    this_symbol_list = []
                    this_energy = None
                try:
                    x, y, z = float(fields[3]), float(fields[4]), float(fields[5])
                    this_geometry.append([x, y, z])
                    symbol = get_symbol(fields[1])
                    this_symbol_list.append(symbol)
                except:
                    print("error parsing >>> %s" % line)
                    print(fields)
                    raise ValueError("error parsing geometry")

            elif len(fields) == 5:
                if len(this_geometry) > 0 and fields[0] == "1":
                    # reset fields
                    this_geometry = []
                    this_symbol_list = []
                    this_energy = None
                try:
                    x, y, z = float(fields[2]), float(fields[3]), float(fields[4])
                    this_geometry.append([x, y, z])
                    symbol = get_symbol(fields[1])
                    this_symbol_list.append(symbol)
                except:
                    print("error parsing >>> %s" % line)
                    print(fields)
                    raise ValueError("error parsing geometry")

            else:
                print("error parsing >>> " + line)
                raise ValueError("unexpected number of fields on geometry line")
        # read energy if applicable
        if not in_geometry_block and line.startswith("SCF Done"):
            fields = re.split(" +", line)
            if len(fields) != 9:
                print("error parsing >>> " + line)
                raise ValueError("unexpected number of fields on energy line")
            this_energy = float(fields[4])
            num_cycles = int(fields[7])

            if len(this_geometry) == 0:
                raise ValueError("energy without geometry")

            # store results
            file_geometries.append(this_geometry)
            file_symbol_lists.append(this_symbol_list)
            file_energies.append(this_energy)
            file_scf_iterations.append(num_cycles)

            # reinitialize arrays
            this_geometry = []
            this_symbol_list = []
            this_energy = None

        # go to next line
        i += 1

    # return result
    if len(file_symbol_lists) > 0:
        return file_geometries, file_symbol_lists[0], file_energies, file_scf_iterations
    else:
        (geometry, symbol_list) = extract_initial_geometry(lines_obj)
        return [geometry], symbol_list, [], []

def read_bonds(lines):
    """
    Reads bonding information from the output file.

    Args:
        lines (list): the list of lines in the file

    Returns:
        array of atoms that are bonded to each other
    """

    bond_array = []
    current_array = []

    i = 0
    in_bonding_section = False

    #### we'll read this into memory to speed this up
    lines = list(lines)

    while i < len(lines):
        # read the current line
        line = lines[i].strip()

        if in_bonding_section == False:
            if re.search(r"Initial Parameters", line):
                i += 5
                in_bonding_section = True
                continue
            else:
                i += 1
                continue
        else:
            if re.search(r"! R", line):
                pieces = list(filter(None, line.split(" ")))
                atoms = pieces[2].replace("R", "").replace("(", "").replace(")", "").split(",")
                try:
                    current_array.append([int(atoms[0]), int(atoms[1])])
                except:
                    raise ValueError(f"error parsing line {i} - can't extract atoms!")
                i += 1
                continue
            elif (re.search(r"! A", line)) or (re.search("----", line)):
                in_bonding_section = False
                bond_array.append(current_array)
                current_array = []
                i += 1
                continue
            else:
                raise ValueError(f"can't parse line {i} for bonding!")

    if len(bond_array):
        return bond_array[0]
    else:
        return None

def extract_initial_geometry(lines):
    """
    Helper method to search through the output file and find the initial geometry/symbol list, in cases where no SCF iterations finished.

    Args:
        lines (list): list of lines in file

    Returns:
        initial geometry (list)
        symbol list (list)
    """
    initial_geom_block = lines.search_for_block("Symbolic Z-matrix:", "^ $", join="\n", max_len=1000)

    if initial_geom_block is not None:
        atom_lines = initial_geom_block.split("\n")[2:]
        geometry = [None] * len(atom_lines)
        symbols = [None] * len(atom_lines)

        for idx, line in enumerate(atom_lines):
            frags = line.split()
            assert len(frags) == 4, f"too many fragments (more than 4) on line {line}"
            geometry[idx] = frags[1:]
            symbols[idx] = frags[0]
        return geometry, symbols

    else:
        initial_geom_block = lines.search_for_block("Standard orientation:", "Rotational", join="\n", max_len=1000)

        if initial_geom_block is None:
            raise ValueError("can't find valid geometry")

        atom_lines = initial_geom_block.split("\n")[5:-1]
        geometry = [None] * len(atom_lines)
        symbols = [None] * len(atom_lines)

        for idx, line in enumerate(atom_lines):
            frags = line.split()
            assert len(frags) == 6, f"too many fragments (more than 6) on line {line}"
            geometry[idx] = frags[3:]
            symbols[idx] = frags[1]

            return geometry, [get_symbol(z) for z in symbols]

def read_nmr_shifts(lines, num_atoms):
    """
    Helper method to search through output file and read NMR shifts.

    Args:
        lines (list): list of lines in file
        num_atoms (int): number of atoms expected

    Returns:
        list of isotropic NMR shifts (np.ndarray)
    """
    # assumes that lines only come from one Link1 section
    shieldings = []
    for line in lines:
        fields = line.split()
        if len(fields) == 8 and fields[2] == "Isotropic" and fields[5] == "Anisotropy":
            fields = line.split()
            assert len(fields) == 8, f"Expected 8 fields on an NMR shielding output line but found {len(fields)} instead!"
            try:
                shielding = float(fields[4])
            except:
                raise ValueError(f"Error parsing NMR shielding output line:\n{line}")
            shieldings.append(shielding)
    assert len(shieldings) == num_atoms, f"Expected {num_atoms} shieldings but found {len(shieldings)}!"
    return np.asarray(shieldings)

def split_link1(filename):
    """
    Splits ``filename`` into blocks by searching for "Entering Link 1".

    Args:
        filename (str): path to file

    Returns:
        list of list of lines by Link1 section; so a file with one Link1 specification would return [lines1, lines2]
    """
    link1_blocks = []

    start_block = 0
    with open(filename, "r") as lines:
        for idx, line in enumerate(lines):
            if re.search("Entering Link 1", line):
                link1_blocks.append(LazyLineObject(file=filename, start=start_block, end=idx))
                start_block = idx
    link1_blocks.append(LazyLineObject(file=filename, start=start_block, end=idx))

    return link1_blocks[1:] #### the first block is just a few lines

def extract_link0(lines):
    """
    Extracts Link 0 commands from ``lines``.

    Args:
        lines (list): list of lines in file

    Returns:
        dictionary of link 0 commands
    """
    output = {}

    #### read first 200 lines of file to memory
    lines = [x for _, x in zip(range(200), lines)]

    #### find where the header starts
    for idx, line in enumerate(lines):
        if re.match(" #p", line):
            break
    end_idx = idx - 1


    ##### then go back until the big header that says "GAUSSIAN 16"
    while not re.match(" \*\*\*\*\*\*\*\*", lines[idx]):
        idx += -1
        if idx < 10:
            raise ValueError("missed the termination point somehow")
    start_idx = idx

    #### and search within that little block for lines matching the right description
    for line in lines[start_idx:end_idx]:
        if re.match(" \%", line):
            pieces = line[2:].split("=")
            output[pieces[0]] = pieces[1]

    return output

def read_forces(lines):
    """
    Reads forces from a Gaussian ``force`` job.

    Args:
        lines (list): list of lines in file

    Returns:
        (n x 3) ``cctk.OneIndexedArray`` of forces
    """
    forces = []
    force_block = lines.search_for_block("Forces \(Hartrees/Bohr\)", "Cartesian Forces", join="\n", max_len=1000)
    for line in force_block.split("\n")[2:]:
        fields = re.split(" +", line)
        fields = list(filter(None, fields))

        if len(fields) == 5:
            forces.append([float(fields[2]), float(fields[3]), float(fields[4])])

    return OneIndexedArray(forces)

def read_mulliken_charges(lines):
    """
    Reads charges from a Gaussian ``pop`` job.

    Args:
        lines (list): list of lines in file

    Returns:
        ``cctk.OneIndexedArray`` of charges
    """
    charges = []
    charge_block = lines.search_for_block(" Mulliken charges:", " Sum of Mulliken charges", join="\n", max_len=1000)
    if charge_block is not None:
        for line in charge_block.split("\n")[2:]:
            fields = re.split(" +", line)
            fields = list(filter(None, fields))

            if len(fields) == 3:
                charges.append(float(fields[2]))

    return OneIndexedArray(charges)

def read_hirshfeld_charges(lines):
    """
    Reads charges from a Gaussian ``pop`` job.

    Args:
        lines (list): list of lines in file

    Returns:
        ``cctk.OneIndexedArray`` of charges
        ``cctk.OneIndexedArray`` of spin densities
    """
    charges = []
    spins = []
    charge_block = lines.search_for_block("Hirshfeld charges, spin densities, dipoles, and CM5 charges", " Hirshfeld charges", join="\n", max_len=1000)
    for line in charge_block.split("\n")[2:]:
        fields = re.split(" +", line)
        fields = list(filter(None, fields))

        if len(fields) == 8:
            charges.append(float(fields[2]))
            spins.append(float(fields[3]))

    return OneIndexedArray(charges), OneIndexedArray(spins)

def read_dipole_moment(lines):
    """
    Reads dipole moment from a Gaussian job.

    Args:
        lines (list): list of lines in file

    Returns:
        dipole moment (magnitude only)
    """
    dipole_block = lines.search_for_block(" Electronic spatial extent", " Quadrupole moment", join="\n")
    for line in dipole_block.split("\n")[1:]:
        fields = re.split(" +", line)
        fields = list(filter(None, fields))

        if len(fields) == 8:
            return float(fields[7])

