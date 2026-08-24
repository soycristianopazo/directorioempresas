"""Router de preguntas y respuestas del evento de sourcing:
/api/organizations/{id}/sourcing-events/{event_id}/questions/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.qa import AnswerQuestionRequest, AskQuestionRequest, QuestionOut
from app.schemas.sourcing import CreatedOut
from app.services import qa as qa_service

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/questions",
    tags=["qa"],
)

_STATUS_BY_ERROR = {
    qa_service.QaPermissionError: status.HTTP_403_FORBIDDEN,
    qa_service.QaNotFoundError: status.HTTP_404_NOT_FOUND,
    qa_service.QaValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: qa_service.QaError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[QuestionOut])
async def list_questions(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[QuestionOut]:
    try:
        rows = await qa_service.list_questions(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except qa_service.QaError as exc:
        raise _as_http_exception(exc) from exc
    return [QuestionOut(**r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def ask_question(
    organization_id: UUID,
    event_id: UUID,
    payload: AskQuestionRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        question_id = await qa_service.ask_question(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            **payload.model_dump(),
        )
    except qa_service.QaError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=question_id)


@router.post(
    "/{question_id}/answer",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def answer_question(
    organization_id: UUID,
    event_id: UUID,
    question_id: UUID,
    payload: AnswerQuestionRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await qa_service.answer_question(
            user_id=user_id,
            organization_id=organization_id,
            question_id=question_id,
            **payload.model_dump(),
        )
    except qa_service.QaError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{question_id}/publish",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def publish_answer(
    organization_id: UUID, event_id: UUID, question_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await qa_service.publish_answer(
            user_id=user_id, organization_id=organization_id, question_id=question_id
        )
    except qa_service.QaError as exc:
        raise _as_http_exception(exc) from exc
