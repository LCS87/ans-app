from pathlib import Path
from typing import Optional
import zipfile

import pandas as pd


def save_csv(df: pd.DataFrame, out_csv_path: Path, encoding: str = "utf-8-sig") -> Path:
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv_path, index=False, encoding=encoding)
    return out_csv_path


def zip_file(input_file: Path, out_zip_path: Path, arcname: Optional[str] = None) -> Path:
    out_zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(input_file, arcname=arcname or input_file.name)

    return out_zip_path
