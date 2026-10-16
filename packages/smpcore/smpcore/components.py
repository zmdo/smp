"""Load installable server components from the components directory.

The install and detect commands live in those files. This module only reads
the directory so a new component can be added without changing the program.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Component:
    id: str
    name: str
    summary: str
    order: int
    requires: tuple[str, ...]
    directory: Path

    @property
    def detect_script(self) -> Path:
        return self.directory / "detect.sh"

    @property
    def install_script(self) -> Path:
        return self.directory / "install.sh"


def components_dir() -> Path:
    override = os.environ.get("COMPONENTS_DIR")
    if override:
        path = Path(override)
        if not path.is_dir():
            raise FileNotFoundError(f"组件目录不存在：{path}")
        return path
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "components"
        if candidate.is_dir() and any(candidate.glob("*/component.json")):
            return candidate
    raise FileNotFoundError("没有找到组件目录")


def load_catalog(root: Path | None = None) -> list[Component]:
    base = root or components_dir()
    found: list[Component] = []
    for path in sorted(base.iterdir()):
        meta_path = path / "component.json"
        if not path.is_dir() or not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        component_id = str(meta["id"])
        if component_id != path.name:
            raise ValueError(f"{meta_path} 的 id 必须和目录名一致")
        requires = tuple(str(item) for item in meta.get("requires") or [])
        component = Component(
            id=component_id,
            name=str(meta["name"]),
            summary=str(meta.get("summary") or ""),
            order=int(meta.get("order") or 0),
            requires=requires,
            directory=path,
        )
        if not component.detect_script.is_file() or not component.install_script.is_file():
            raise ValueError(f"{component_id} 缺少 detect.sh 或 install.sh")
        found.append(component)
    found.sort(key=lambda item: (item.order, item.id))
    return found


def normalize_selection(component_ids: list[str], root: Path | None = None) -> list[str]:
    catalog = load_catalog(root)
    by_id = {item.id: item for item in catalog}
    chosen: list[str] = []
    for component_id in component_ids:
        if component_id not in by_id:
            raise ValueError("有无法识别的组件")
        if component_id not in chosen:
            chosen.append(component_id)
    for component_id in chosen:
        component = by_id[component_id]
        for required in component.requires:
            if required not in chosen:
                raise ValueError(f"{component.name} 需要同时选择 {by_id[required].name}")
    order = {item.id: index for index, item in enumerate(catalog)}
    chosen.sort(key=lambda item: order[item])
    return chosen
