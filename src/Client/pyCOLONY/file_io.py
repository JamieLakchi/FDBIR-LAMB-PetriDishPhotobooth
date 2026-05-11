import os
import skimage

import pandas as pd

from pathlib import Path

def find_images(CWD: Path) -> list[Path]:
    """Find all images the tool can handle in the CWD"""
    
    img_files = []
    path_formula = "**/*.{}"
    for ext in ["jpg","jpeg", "png"]:
        img_files.extend(CWD.glob(path_formula.format(ext)))
        img_files.extend(CWD.glob(path_formula.format(ext.upper())))
        
    return img_files
    

def write_properties_to_file(props:list, outf=Path("results.tsv")):
    df = pd.concat(props)
    df.to_csv(outf, sep="\t", index=False)