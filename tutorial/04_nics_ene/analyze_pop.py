import sys, re, glob
import numpy as np
import matplotlib.pyplot as plt

from cctk import GaussianFile, Molecule
import cctk.parse_gaussian as parse

#### Usage: ``python analyze_pop.py "path/to/output/*.out"``
#### NOTE: It's crucial to wrap the wildcard-containing path in quotes!

#### NOTE: This file will reject any file that contains the string "slurm."

#### Corin Wagen and Eugene Kwan, 2019

filenames = sys.argv[1]

energies = {}
C1_charge = {}
O7_charge = {}
C8_charge = {}
C9_charge = {}
C12_charge = {}

for filename in sorted(glob.glob(filenames, recursive=True)):
    if re.search("slurm", filename):
        continue

    (output_file, lines) = GaussianFile.read_file(filename, return_lines=True)
    dist = int(round(output_file.get_molecule().get_distance(1, 8) * 1000))

    energies[dist] = output_file.energies[-1]

    #### extract charges
    try:
        C1_charge[dist] = parse.find_parameter(lines, "     1  C", 8, 2)[-1]
        O7_charge[dist] = parse.find_parameter(lines, "     7  O", 8, 2)[-1]
        C8_charge[dist] = parse.find_parameter(lines, "     8  C", 8, 2)[-1]
        C9_charge[dist] = parse.find_parameter(lines, "     9  C", 8, 2)[-1]
        C12_charge[dist] = parse.find_parameter(lines, "    12  C", 8, 2)[-1]
    except:
        pass

min_energy = np.min(list(energies.values()))
energies = {k: (e - min_energy) * 627.509 for k, e in energies.items()}

fig = plt.figure(figsize=(10,7))
ax1 = fig.gca()
ax1.scatter(list(energies.keys()), list(energies.values()), c='black', alpha=0.8, label="Energy")
ax1.set_ylim(top=30, bottom=0)
ax1.set_xlabel("C1-C5 Distance (mÅ)")
ax1.set_ylabel("Energy (kcal/mol; M06-2X)")

ax2 = ax1.twinx()
ax2.scatter(list(C1_charge.keys()), list(C1_charge.values()), c='blue', alpha=0.8, label="C1")
ax2.scatter(list(O7_charge.keys()), list(O7_charge.values()), c='red', alpha=0.8, label="O7")
ax2.scatter(list(C8_charge.keys()), list(C8_charge.values()), c='orange', alpha=0.8, label="C8")
ax2.scatter(list(C9_charge.keys()), list(C9_charge.values()), c='green', alpha=0.8, label="C9")
ax2.scatter(list(C12_charge.keys()), list(C12_charge.values()), c='purple', alpha=0.8, label="C12")
ax2.set_ylabel("Hirshfeld Charge (M06-2X)")

plt.legend(loc="best")
plt.title("Change in NICS(0) over IRC")

plt.show()
plt.savefig('pop_graph.png')