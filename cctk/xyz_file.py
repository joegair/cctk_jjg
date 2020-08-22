import re
import numpy as np

from cctk import File, Molecule
from cctk.helper_functions import get_symbol, get_number


class XYZFile(File):
    """
    Class representing plain ``.xyz`` files.

    Attributes:
        title (str): the title from the file
        molecule (Molecule): `Molecule` instance
    """

    def __init__(self, molecule, title=None):
        if molecule and isinstance(molecule, Molecule):
            self.molecule = molecule
        if title and (isinstance(title, str)):
            self.title = title

    @classmethod
    def read_file(cls, filename):
        """
        Factory method to create new XYZFile instances.
        """
        lines = super().read_file(filename)

        return cls.file_from_lines(lines)

    @classmethod
    def file_from_lines(cls, lines):
        num_atoms = 0
        try:
            num_atoms = int(lines[0])
        except:
            raise ValueError("can't get the number of atoms from the first line!")

        title = lines[1]

        atomic_numbers = np.zeros(shape=num_atoms, dtype=np.int8)
        geometry = np.zeros(shape=(num_atoms, 3))

        for index, line in enumerate(lines[2:]):
            # ignore blank lines
            if len(line.strip()) == 0:
                continue

            pieces = list(filter(None, line.split(" ")))
            try:
                if re.match("[0-9]", pieces[0]):
                    atomic_numbers[index] = int(pieces[0])
                else:
                    atomic_numbers[index] = int(get_number(pieces[0]))
                geometry[index][0] = float(pieces[1])
                geometry[index][1] = float(pieces[2])
                geometry[index][2] = float(pieces[3])
            except:
                raise ValueError(f"can't parse line {index+2}: {line}")

        assert num_atoms == len(atomic_numbers), "wrong number of atoms!"
        molecule = Molecule(atomic_numbers, geometry)
        return XYZFile(molecule, title)

    @classmethod
    def write_molecule_to_file(cls, filename, molecule, title="title"):
        """
        Write an ``.xyz`` file, using object attributes.

        Args:
            filename (str): path to the new file
            molecule (Molecule): molecule to write
            title (str): title of file
        """
        assert isinstance(molecule, Molecule), "molecule is not a valid Molecule object!"

        text = f"{molecule.num_atoms()}\n"
        text += f"{title}\n"

        for index, Z in enumerate(molecule.atomic_numbers, start=1):
            line = molecule.get_vector(index)
            text += f"{get_symbol(Z):>2}       {line[0]:>13.8f} {line[1]:>13.8f} {line[2]:>13.8f}\n"

        super().write_file(filename, text)

    def write_file(self, filename):
        """
        Write an ``.xyz`` file, using object attributes.
        """
        self.write_molecule_to_file(filename, self.molecule, title=self.title)

    @classmethod
    def read_trajectory(cls, filename):
        """
        Read an ``.xyz`` trajectory file, which is just a bunch of concatenated ``.xyz`` files.
        Currently the files must be separated by nothing (no blank line, just one after the other) although this may be changed in future.

        Args:
            filename (str): path to file

        Returns:
            list of ``cctk.XYZFile`` objects in the order they appear in the file
        """
        files = []
        lines = super().read_file(filename)

        current_lines = list()
        for line in lines:
            if re.search(r"^\d+$", line):
                if len(current_lines) > 0:
                    files.append(cls.file_from_lines(current_lines))
                    current_lines = list()
            current_lines.append(line)

        return files

    @classmethod
    def read_ensemble(cls, filename, conformational=False):
        """
        Alias for read_trajectory.
        """
        files = cls.read_trajectory(filename)

        ensemble = None
        if conformational:
            ensemble = cctk.ConformationalEnsemble()
        else:
            ensemble = cctk.Ensemble()

        for file in files:
            ensemble.add_molecule(file.molecule)

        return ensemble



