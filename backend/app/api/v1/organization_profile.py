"""Router de perfil extendido: /api/organizations/{id}/locations, /contacts,
/media, /industries, /territories.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUserId
from app.schemas.organization_profile import (
    AddTerritoryRequest,
    ContactOut,
    CreateContactRequest,
    CreateLocationRequest,
    CreatedOut,
    EconomicActivityOut,
    IndustryOut,
    LocationOut,
    MediaOut,
    SetEconomicActivityRequest,
    SetIndustryRequest,
    SetLogoShapeRequest,
    TerritoryOut,
    UpdateContactRequest,
    UpdateLocationRequest,
)
from app.services import organization_profile as profile_service

router = APIRouter(
    prefix="/organizations/{organization_id}", tags=["organization-profile"]
)

_STATUS_BY_ERROR = {
    profile_service.ProfilePermissionError: status.HTTP_403_FORBIDDEN,
    profile_service.ProfileNotFoundError: status.HTTP_404_NOT_FOUND,
    profile_service.ProfileValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: profile_service.ProfileError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


# ─── Ubicaciones ─────────────────────────────────────────────────────────────


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(
    organization_id: UUID, user_id: CurrentUserId
) -> list[LocationOut]:
    rows = await profile_service.list_locations(
        user_id=user_id, organization_id=organization_id
    )
    return [LocationOut.model_validate(r) for r in rows]


@router.post(
    "/locations", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_location(
    organization_id: UUID, payload: CreateLocationRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        location_id = await profile_service.create_location(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=location_id)


@router.put(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def update_location(
    organization_id: UUID,
    location_id: UUID,
    payload: UpdateLocationRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await profile_service.update_location(
            user_id=user_id,
            organization_id=organization_id,
            location_id=location_id,
            **payload.model_dump(),
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/locations/{location_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def deactivate_location(
    organization_id: UUID, location_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.deactivate_location(
            user_id=user_id, organization_id=organization_id, location_id=location_id
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


# ─── Contactos ───────────────────────────────────────────────────────────────


@router.get("/contacts", response_model=list[ContactOut])
async def list_contacts(
    organization_id: UUID, user_id: CurrentUserId
) -> list[ContactOut]:
    rows = await profile_service.list_contacts(
        user_id=user_id, organization_id=organization_id
    )
    return [ContactOut.model_validate(r) for r in rows]


@router.post(
    "/contacts", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_contact(
    organization_id: UUID, payload: CreateContactRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        contact_id = await profile_service.create_contact(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=contact_id)


@router.put(
    "/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def update_contact(
    organization_id: UUID,
    contact_id: UUID,
    payload: UpdateContactRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await profile_service.update_contact(
            user_id=user_id,
            organization_id=organization_id,
            contact_id=contact_id,
            **payload.model_dump(),
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/contacts/{contact_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def deactivate_contact(
    organization_id: UUID, contact_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.deactivate_contact(
            user_id=user_id, organization_id=organization_id, contact_id=contact_id
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


# ─── Media (logo / banner) ────────────────────────────────────────────────────


@router.get("/media", response_model=list[MediaOut])
async def list_media(organization_id: UUID, user_id: CurrentUserId) -> list[MediaOut]:
    rows = await profile_service.list_media(
        user_id=user_id, organization_id=organization_id
    )
    return [MediaOut(**r) for r in rows]


@router.post("/media", status_code=status.HTTP_201_CREATED, response_model=MediaOut)
async def upload_media(
    organization_id: UUID,
    user_id: CurrentUserId,
    media_type: str = Form(...),
    alt_text: str | None = Form(default=None),
    logo_shape: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> MediaOut:
    content = await file.read()
    try:
        result = await profile_service.upload_media(
            user_id=user_id,
            organization_id=organization_id,
            media_type=media_type,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            alt_text=alt_text,
            logo_shape=logo_shape,
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc
    return MediaOut(**result)


@router.delete(
    "/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_media(
    organization_id: UUID, media_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.delete_media(
            user_id=user_id, organization_id=organization_id, media_id=media_id
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


@router.put(
    "/media/{media_id}/logo-shape",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def set_logo_shape(
    organization_id: UUID,
    media_id: UUID,
    payload: SetLogoShapeRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await profile_service.set_logo_shape(
            user_id=user_id,
            organization_id=organization_id,
            media_id=media_id,
            shape=payload.shape,
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


# ─── Industrias ──────────────────────────────────────────────────────────────


@router.get("/industries", response_model=list[IndustryOut])
async def list_industries(
    organization_id: UUID, user_id: CurrentUserId
) -> list[IndustryOut]:
    rows = await profile_service.list_industries(
        user_id=user_id, organization_id=organization_id
    )
    return [IndustryOut.model_validate(r) for r in rows]


@router.put("/industries", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def set_industry(
    organization_id: UUID, payload: SetIndustryRequest, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.set_industry(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


@router.delete(
    "/industries/{industry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_industry(
    organization_id: UUID, industry_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.remove_industry(
            user_id=user_id, organization_id=organization_id, industry_id=industry_id
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


# ─── Giros SII ────────────────────────────────────────────────────────────────


@router.get("/economic-activities", response_model=list[EconomicActivityOut])
async def list_economic_activities(
    organization_id: UUID, user_id: CurrentUserId
) -> list[EconomicActivityOut]:
    rows = await profile_service.list_economic_activities(
        user_id=user_id, organization_id=organization_id
    )
    return [EconomicActivityOut.model_validate(r) for r in rows]


@router.put(
    "/economic-activities", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def set_economic_activity(
    organization_id: UUID, payload: SetEconomicActivityRequest, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.set_economic_activity(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


@router.delete(
    "/economic-activities/{sii_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_economic_activity(
    organization_id: UUID, sii_code: str, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.remove_economic_activity(
            user_id=user_id, organization_id=organization_id, sii_code=sii_code
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc


# ─── Territorios ─────────────────────────────────────────────────────────────


@router.get("/territories", response_model=list[TerritoryOut])
async def list_territories(
    organization_id: UUID, user_id: CurrentUserId
) -> list[TerritoryOut]:
    rows = await profile_service.list_territories(
        user_id=user_id, organization_id=organization_id
    )
    return [TerritoryOut.model_validate(r) for r in rows]


@router.post(
    "/territories", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def add_territory(
    organization_id: UUID, payload: AddTerritoryRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        territory_id = await profile_service.add_territory(
            user_id=user_id,
            organization_id=organization_id,
            admin_division_id=payload.admin_division_id,
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=territory_id)


@router.delete(
    "/territories/{territory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_territory(
    organization_id: UUID, territory_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await profile_service.remove_territory(
            user_id=user_id, organization_id=organization_id, territory_id=territory_id
        )
    except profile_service.ProfileError as exc:
        raise _as_http_exception(exc) from exc
