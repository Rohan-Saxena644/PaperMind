from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.models import User
from app.schemas.schemas import GraphInsights, GraphResponse
from app.services.ai.graph import get_knowledge_map, get_paper_graph
from app.services.ai.graph_layout import graph_summary, layout_graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/knowledge-map", response_model=GraphResponse)
def knowledge_map(current_user: User = Depends(get_current_user)):
    try:
        graph = get_knowledge_map(str(current_user.id))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Knowledge graph unavailable: {exc}") from exc

    return layout_graph(graph["nodes"], graph["edges"])


@router.get("/papers/{paper_id}", response_model=GraphResponse)
def paper_graph(paper_id: str, current_user: User = Depends(get_current_user)):
    try:
        graph = get_paper_graph(str(current_user.id), paper_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Knowledge graph unavailable: {exc}") from exc

    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail="Graph not found for this paper")

    return layout_graph(graph["nodes"], graph["edges"])


@router.get("/insights", response_model=GraphInsights)
def graph_insights(current_user: User = Depends(get_current_user)):
    try:
        graph = get_knowledge_map(str(current_user.id))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Knowledge graph unavailable: {exc}") from exc

    return graph_summary(graph["nodes"], graph["edges"])
