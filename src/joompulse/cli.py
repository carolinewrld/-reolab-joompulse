from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path

import typer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from joompulse.ai.taxonomy import DIMENSIONS, load_all
from joompulse.db.base import get_sessionmaker
from joompulse.db.models import TaxonomyTerm
from joompulse.logging import configure_logging, get_logger

app = typer.Typer(help="JoomPulse CLI")
taxonomy_app = typer.Typer(help="Taxonomy management")
app.add_typer(taxonomy_app, name="taxonomy")


@app.command("gen-key")
def gen_key() -> None:
    """Generate a 32-byte urlsafe base64 key for ENCRYPTION_KEY."""
    typer.echo(base64.urlsafe_b64encode(os.urandom(32)).decode())


@taxonomy_app.command("sync")
def taxonomy_sync(
    path: Path = typer.Option(Path("taxonomy"), help="Directory with <dimension>.yaml files"),
) -> None:
    """Upsert taxonomy terms from YAML files into the database."""
    configure_logging()
    log = get_logger(__name__)

    terms = load_all(path)
    if not terms:
        typer.echo(f"No terms found in {path}", err=True)
        raise typer.Exit(1)

    async def run() -> int:
        async with get_sessionmaker()() as session:
            for t in terms:
                stmt = insert(TaxonomyTerm).values(
                    dimension=t.dimension,
                    code=t.code,
                    label_ru=t.label_ru,
                    label_en=t.label_en,
                    description=t.description,
                    is_active=True,
                ).on_conflict_do_update(
                    index_elements=["dimension", "code"],
                    set_={
                        "label_ru": t.label_ru,
                        "label_en": t.label_en,
                        "description": t.description,
                        "is_active": True,
                    },
                )
                await session.execute(stmt)
            await session.commit()
            total = (
                await session.execute(select(TaxonomyTerm))
            ).scalars().all()
            return len(list(total))

    count = asyncio.run(run())
    log.info("taxonomy.synced", dimensions=list(DIMENSIONS), total_terms=count)


if __name__ == "__main__":
    app()
