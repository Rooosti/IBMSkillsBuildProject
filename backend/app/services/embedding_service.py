from langchain_ibm import WatsonxEmbeddings
from app.core.config import settings

def get_embedding_model():
    return WatsonxEmbeddings(
        model_id="ibm/slate-30m-english-rtrvr-v2",
        url=settings.watsonx_url,
        apikey=settings.watsonx_api_key,
        project_id=settings.watsonx_project_id,
    )

async def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return await model.aembed_query(text)

async def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    return await model.aembed_documents(texts)
