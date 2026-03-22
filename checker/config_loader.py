import os
import re

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: str = "config.yml") -> dict:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    resolved = re.sub(
        r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), raw
    )
    return yaml.safe_load(resolved)
