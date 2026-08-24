"""Router de organizaciones: /api/organizations/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.organization import (
    CreateOrganizationRequest,
    OrganizationOut,
    SwitchOrganizationRequest,
    UpdateOrganizationRequest,
)
from app.services import organizations as org_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: CreateOrganizationRequest, user_id: CurrentUserId
) -> dict:
    try:
        organization_id = await org_service.create_organization(
            created_by=user_id,
            legal_name=payload.legal_name,
            trade_name=payload.trade_name,
            rut=payload.rut,
            capabilities=payload.capabilities,
            country_code=payload.country_code,
        )
    except org_service.OrganizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return {"organization_id": str(organization_id)}


@router.get("/{organization_id}", response_model=OrganizationOut)
async def get_organization(
    organization_id: UUID, user_id: CurrentUserId
) -> OrganizationOut:
    detail = await org_service.get_organization_detail(
        user_id=user_id, organization_id=organization_id
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada"
        )
    return OrganizationOut(**detail)


@router.put(
    "/{organization_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def update_organization(
    organization_id: UUID, payload: UpdateOrganizationRequest, user_id: CurrentUserId
) -> None:
    try:
        await org_service.update_organization(
            user_id=user_id,
            organization_id=organization_id,
            legal_name=payload.legal_name,
            trade_name=payload.trade_name or None,
            short_description=payload.short_description or None,
            description=payload.description or None,
            value_proposition=payload.value_proposition or None,
            website_url=payload.website_url or None,
            linkedin_url=payload.linkedin_url or None,
            general_email=payload.general_email or None,
            general_phone=payload.general_phone or None,
            founded_year=payload.founded_year,
            company_size=payload.company_size,
            employee_count=payload.employee_count,
            visibility=payload.visibility,
        )
    except org_service.OrganizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.post(
    "/{organization_id}/publish",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def publish_organization(organization_id: UUID, user_id: CurrentUserId) -> None:
    try:
        await org_service.publish_organization(
            user_id=user_id, organization_id=organization_id
        )
    except org_service.OrganizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/switch", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def switch_organization(
    payload: SwitchOrganizationRequest, user_id: CurrentUserId
) -> None:
    try:
        await org_service.switch_organization(
            user_id=user_id, organization_id=payload.organization_id
        )
    except org_service.OrganizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
