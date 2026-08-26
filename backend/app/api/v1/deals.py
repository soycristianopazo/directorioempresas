"""Router del panel de Ofertas: /api/organizations/{id}/deals — todas las
ofertas (vigentes e históricas) de la organización, a través de todo su
catálogo. La creación/edición de cada oferta sigue viviendo bajo su
publicación (/organizations/{id}/offerings/{offering_id}/deals/*, ver
api/v1/offerings.py); esto es solo el listado agregado para el dashboard.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.offerings import OrgDealOut
from app.services import offerings as offerings_service

router = APIRouter(prefix="/organizations/{organization_id}/deals", tags=["offerings"])


@router.get("", response_model=list[OrgDealOut])
async def list_org_deals(
    organization_id: UUID, user_id: CurrentUserId
) -> list[OrgDealOut]:
    try:
        rows = await offerings_service.list_org_deals(
            user_id=user_id, organization_id=organization_id
        )
    except offerings_service.OfferingError as exc:
        status_by_error = {
            offerings_service.OfferingPermissionError: status.HTTP_403_FORBIDDEN,
        }
        raise HTTPException(
            status_code=status_by_error.get(type(exc), status.HTTP_400_BAD_REQUEST),
            detail=str(exc),
        ) from exc
    return [OrgDealOut(**r) for r in rows]
