from fastapi import Depends, FastAPI

from app.api.auth import router as auth_router
from app.api.ai import router as ai_router
from app.api.canvas import router as canvas_router
from app.api.case import router as case_router
from app.api.health import router as health_router
from app.api.permission import router as permission_router
from app.api.rag import router as rag_router
from app.api.task import router as task_router
from app.api.xmind import router as xmind_router
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.core.handlers import register_exception_handlers


# 创建 FastAPI 应用对象。
# 后续所有接口都会挂载到这个 app 上。
app = FastAPI(
    title=settings.app_name,
    description="基于大模型与RAG的思维导图测试用例自动生成与管理平台",
    version="0.1.0",
)

# 注册统一异常处理，避免把底层异常细节直接回显给前端。
register_exception_handlers(app)


# 注册健康检查接口。
# 现在先放 /health 和 /health/db，方便确认项目是否启动成功、数据库是否连接成功。
app.include_router(health_router, prefix="/health", tags=["健康检查"])
app.include_router(auth_router)
app.include_router(permission_router)
app.include_router(case_router, dependencies=[Depends(get_current_active_user)])
app.include_router(canvas_router, dependencies=[Depends(get_current_active_user)])
app.include_router(xmind_router, dependencies=[Depends(get_current_active_user)])
app.include_router(task_router, dependencies=[Depends(get_current_active_user)])
app.include_router(rag_router, dependencies=[Depends(get_current_active_user)])
app.include_router(ai_router, dependencies=[Depends(get_current_active_user)])


@app.get("/")
def root():
    """项目首页测试接口。"""
    return {
        "message": "RAG思维导图测试用例平台后端启动成功",
        "app_name": settings.app_name,
        "env": settings.app_env,
    }
