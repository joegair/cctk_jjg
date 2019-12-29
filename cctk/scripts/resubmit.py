import sys, argparse
import re
import glob
import numpy as np

from cctk import GaussianFile, Molecule

#### This is a script to resubmit failed Gaussian files.
#### Parameters:
#### ``--type, -t``: which jobs to resubmit 
####     "failed": will resubmit jobs with no successes
####     "all": will resubmit all jobs
#### ``--perturb, -p``: whether or not to apply a random geometric perturbation to each job

#### Usage: ``python resubmit.py --type all --perturb "path/to/output/*.out"``
#### NOTE: It's crucial to wrap the wildcard-containing path in quotes!

#### NOTE: This file will reject any file that contains the string "slurm."

#### Corin Wagen and Eugene Kwan, 2019

parser = argparse.ArgumentParser(prog="resubmit.py")
parser.add_argument("--type", "-t", type=str)
parser.add_argument("--perturb", "-p", action="store_true")
parser.add_argument("filename")
args = vars(parser.parse_args(sys.argv[1:]))

assert args["filename"], "Can't resubmit files without a filename!"

for filename in glob.iglob(args["filename"], recursive=True):
    if re.search("slurm", filename):
        continue
    
    try:
        output_file = GaussianFile.read_file(filename)
        if args["perturb"]:
            output_file.get_molecule().perturb()
        success = output_file.success

        if ((success == 0) and (args["type"] == "failed")) or (args["type"] == "all") or (args["type"] is None):
            newfile = filename.rsplit('/',1)[1]
            newfile = re.sub(r"out$", "gjf", newfile)
            output_file.write_file(newfile)
            print(f"{filename} > {newfile}")

    except:
        print(f"can't read file {filename}!")