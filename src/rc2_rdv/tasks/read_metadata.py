# + tags=["parameters"]
upstream = []
product = None
input4import = None
# -

import os
import glob
from pathlib import Path
import pandas as pd 
import zipfile

def list_files_recursively_except(directory, exclude_extension=["xlsx","zip"]):
    """
    List files recursively in a directory, excluding files with a specific extension.

    Args:
        directory (str): The directory to search.
        exclude_extension (str): The extension to exclude.

    Returns:
        list: A list of file paths.
    """
    files = []
    basename = []
    extension = []
    pattern = os.path.join(directory, '**', '*.*')
    for file_path in glob.iglob(pattern, recursive=True):
        if os.path.isfile(file_path):
            _base = os.path.basename(file_path)
            _name, _extension = os.path.splitext(_base)
            if _extension in exclude_extension:
                continue            
            files.append(os.path.dirname(file_path))
            basename.append(_name)
            extension.append(_extension)


    return pd.DataFrame({
    'folder': files,
    'basename': basename,
    'extension': extension
    })

Path(os.path.dirname(product["data"])).mkdir(parents=True, exist_ok=True)
df = list_files_recursively_except(input4import, [".xlsx",".zip"] )

df.to_excel(product["data"],index=False)