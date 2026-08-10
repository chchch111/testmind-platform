from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
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
    delete_knowledge_source,
    import_case_set_as_source,
    list_knowledge_bases,
    list_knowledge_sources,
    search_knowledge_base,
    upload_knowledge_source_file,
)


router = APIRouter(prefix="/api/rag", tags=["RAG知识库"])


@router.post("/knowledge-bases", response_model=KnowledgeBaseOut)
def api_create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return create_knowledge_base(db, data)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseOut])
def api_list_knowledge_bases(db: Session = Depends(get_db)):
    return list_knowledge_bases(db)


@router.post("/knowledge-bases/{knowledge_base_id}/sources/manual", response_model=KnowledgeSourceOut)
def api_add_manual_source(
    knowledge_base_id: int,
    data: ManualSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return add_manual_source(db, knowledge_base_id, data)


@router.post("/knowledge-bases/{knowledge_base_id}/sources/upload", response_model=KnowledgeSourceOut)
def api_upload_knowledge_source_file(
    knowledge_base_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return upload_knowledge_source_file(db, knowledge_base_id, file, current_user.user_id)


@router.post("/knowledge-bases/{knowledge_base_id}/sources/import-case-set", response_model=KnowledgeSourceOut)
def api_import_case_set_as_source(
    knowledge_base_id: int,
    case_set_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return import_case_set_as_source(db, knowledge_base_id, case_set_id, current_user.user_id)


@router.get("/knowledge-bases/{knowledge_base_id}/sources", response_model=list[KnowledgeSourceOut])
def api_list_knowledge_sources(knowledge_base_id: int, db: Session = Depends(get_db)):
    return list_knowledge_sources(db, knowledge_base_id)


@router.delete("/sources/{source_id}")
def api_delete_knowledge_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return delete_knowledge_source(db, source_id, current_user.user_id)


@router.post("/knowledge-bases/{knowledge_base_id}/build-index", response_model=BuildIndexOut)
def api_build_faiss_index(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return build_faiss_index(db, knowledge_base_id, current_user.user_id)


@router.post("/knowledge-bases/{knowledge_base_id}/search", response_model=RagSearchOut)
def api_search_knowledge_base(knowledge_base_id: int, data: RagSearchRequest, db: Session = Depends(get_db)):
    return search_knowledge_base(db, knowledge_base_id, data)
