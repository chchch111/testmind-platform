from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.rag import (
    BuildIndexOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeSourceOut,
    ManualSourceCreate,
    RagSearchOut,
    RagSearchRequest,
)
from app.services.rag_service import (
    add_manual_source,
    build_faiss_index,
    create_knowledge_base,
    list_knowledge_bases,
    search_knowledge_base,
)


router = APIRouter(prefix="/api/rag", tags=["RAG知识库"])


@router.post("/knowledge-bases", response_model=KnowledgeBaseOut)
def api_create_knowledge_base(data: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    return create_knowledge_base(db, data)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseOut])
def api_list_knowledge_bases(db: Session = Depends(get_db)):
    return list_knowledge_bases(db)


@router.post("/knowledge-bases/{knowledge_base_id}/sources/manual", response_model=KnowledgeSourceOut)
def api_add_manual_source(knowledge_base_id: int, data: ManualSourceCreate, db: Session = Depends(get_db)):
    return add_manual_source(db, knowledge_base_id, data)


@router.post("/knowledge-bases/{knowledge_base_id}/build-index", response_model=BuildIndexOut)
def api_build_faiss_index(
    knowledge_base_id: int,
    operator_id: int = Query(default=1),
    db: Session = Depends(get_db),
):
    return build_faiss_index(db, knowledge_base_id, operator_id)


@router.post("/knowledge-bases/{knowledge_base_id}/search", response_model=RagSearchOut)
def api_search_knowledge_base(knowledge_base_id: int, data: RagSearchRequest, db: Session = Depends(get_db)):
    return search_knowledge_base(db, knowledge_base_id, data)
