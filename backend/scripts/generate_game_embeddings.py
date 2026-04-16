import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path to allow importing from app
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.game_catalog import Game, GameSemanticDoc, GameFeature
from app.services.embedding_service import embed_texts

async def generate_embeddings(batch_size: int = 20):
    db = SessionLocal()
    
    # 1. Ensure GameSemanticDoc exists for games that have a description
    # We'll build a combined semantic text from title, description, and tags
    stmt = (
        select(Game, GameFeature)
        .join(GameFeature, Game.id == GameFeature.game_id)
        .outerjoin(GameSemanticDoc, Game.id == GameSemanticDoc.game_id)
        .where(GameSemanticDoc.id == None)
        .where(Game.short_description != None)
    )
    
    games_needing_docs = db.execute(stmt).all()
    print(f"Found {len(games_needing_docs)} games needing SemanticDoc entries.")
    
    for game, feature in games_needing_docs:
        tags = ", ".join(feature.tags_json or [])
        semantic_text = f"Title: {game.title}\nDescription: {game.short_description}\nTags: {tags}"
        
        doc = GameSemanticDoc(
            game_id=game.id,
            semantic_text=semantic_text,
            version="v1"
        )
        db.add(doc)
    
    if games_needing_docs:
        db.commit()
        print("Created missing SemanticDoc entries.")

    # 2. Generate embeddings for docs that don't have them
    while True:
        stmt = (
            select(GameSemanticDoc)
            .where(GameSemanticDoc.embedding == None)
            .limit(batch_size)
        )
        
        docs = db.scalars(stmt).all()
        if not docs:
            break
            
        print(f"Generating embeddings for batch of {len(docs)} docs...")
        
        texts = [doc.semantic_text for doc in docs]
        try:
            embeddings = await embed_texts(texts)
            
            for doc, emb in zip(docs, embeddings):
                doc.embedding = emb
            
            db.commit()
            print(f"Successfully processed {len(docs)} embeddings.")
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            db.rollback()
            break

    db.close()
    print("Finished generating embeddings.")

if __name__ == "__main__":
    asyncio.run(generate_embeddings())
