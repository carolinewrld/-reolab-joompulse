from __future__ import annotations

import asyncio
import base64
import os
import uuid
from pathlib import Path

import typer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from joompulse.ai.taxonomy import DIMENSIONS, load_all
from joompulse.db.base import get_sessionmaker
from joompulse.db.models import AdAccount, TaxonomyTerm
from joompulse.logging import configure_logging, get_logger
from joompulse.meta.fetcher import sync_account
from joompulse.security.crypto import encrypt, mask

app = typer.Typer(help="JoomPulse CLI")
taxonomy_app = typer.Typer(help="Taxonomy management")
meta_app = typer.Typer(help="Meta Ads management")
app.add_typer(taxonomy_app, name="taxonomy")
app.add_typer(meta_app, name="meta")


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
                stmt = (
                    insert(TaxonomyTerm)
                    .values(
                        dimension=t.dimension,
                        code=t.code,
                        label_ru=t.label_ru,
                        label_en=t.label_en,
                        description=t.description,
                        is_active=True,
                    )
                    .on_conflict_do_update(
                        index_elements=["dimension", "code"],
                        set_={
                            "label_ru": t.label_ru,
                            "label_en": t.label_en,
                            "description": t.description,
                            "is_active": True,
                        },
                    )
                )
                await session.execute(stmt)
            await session.commit()
            total = (await session.execute(select(TaxonomyTerm))).scalars().all()
            return len(list(total))

    count = asyncio.run(run())
    log.info("taxonomy.synced", dimensions=list(DIMENSIONS), total_terms=count)


@meta_app.command("add-account")
def meta_add_account(
    meta_account_id: str = typer.Argument(..., help="e.g. act_1234567890"),
    access_token: str = typer.Option(
        ..., prompt=True, hide_input=True, help="Long-lived Meta access token"
    ),
    name: str | None = typer.Option(None, help="Human-readable label"),
) -> None:
    """Register a Meta ad account (stores the token encrypted)."""
    configure_logging()
    log = get_logger(__name__)

    async def run() -> None:
        async with get_sessionmaker()() as session:
            row = await session.scalar(
                select(AdAccount).where(AdAccount.meta_account_id == meta_account_id)
            )
            encrypted = encrypt(access_token)
            if row is None:
                session.add(
                    AdAccount(
                        id=uuid.uuid4(),
                        meta_account_id=meta_account_id,
                        name=name,
                        encrypted_access_token=encrypted,
                        status="active",
                    )
                )
                action = "created"
            else:
                row.encrypted_access_token = encrypted
                if name:
                    row.name = name
                row.status = "active"
                action = "updated"
            await session.commit()
        log.info(
            "meta.account.saved",
            meta_account_id=meta_account_id,
            token=mask(access_token),
            action=action,
        )

    asyncio.run(run())


@meta_app.command("sync")
def meta_sync(
    meta_account_id: str = typer.Argument(...),
) -> None:
    """Synchronous one-off sync (useful for local debugging, bypasses Celery)."""
    configure_logging()
    log = get_logger(__name__)

    async def run() -> None:
        async with get_sessionmaker()() as session:
            account = await session.scalar(
                select(AdAccount).where(AdAccount.meta_account_id == meta_account_id)
            )
            if account is None:
                typer.echo(f"Unknown account: {meta_account_id}", err=True)
                raise typer.Exit(1)
            stats = await sync_account(session, account)
            log.info(
                "meta.sync.done",
                account=meta_account_id,
                ads=stats.ads_seen,
                snapshots=stats.snapshots_written,
                new_creatives=len(stats.new_creatives),
                perf_triggers=len(stats.performance_triggers),
            )

    asyncio.run(run())


if __name__ == "__main__":
    app()
