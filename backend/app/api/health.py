from fastapi import APIRouter

from app.db.database import check_database_connection


router = APIRouter()


@router.get("")
def health_check():
    """服务健康检查接口：只检查 FastAPI 是否正常启动。"""
    return {"status": "ok", "message": "FastAPI服务运行正常"}


@router.get("/db")
def database_health_check():
    """数据库健康检查接口：检查 FastAPI 是否能连接 MySQL。"""
    check_database_connection()
    return {"status": "ok", "message": "MySQL数据库连接正常"}
