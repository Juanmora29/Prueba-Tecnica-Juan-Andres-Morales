from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    document: str
    content: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


class ErrorResponse(BaseModel):
    detail: str
