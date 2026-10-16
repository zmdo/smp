from fastapi import APIRouter, Depends

from smp_web.deps import require_user
from smpcore.components import load_catalog

router = APIRouter(prefix="/api/components", dependencies=[Depends(require_user)])


@router.get("")
@router.get("/", include_in_schema=False)
def list_components() -> list[dict]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "summary": item.summary,
            "requires": list(item.requires),
        }
        for item in load_catalog()
    ]
