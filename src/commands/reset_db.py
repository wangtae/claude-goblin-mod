#region Imports
import sys
from pathlib import Path

from rich.console import Console

from src.storage.snapshot_db import (
    DEFAULT_DB_PATH,
    get_database_stats,
)
#endregion


#region Functions


def run(console: Console) -> None:
    """
    Reset (reinitialize) the database by deleting it and all backups.

    This is useful when:
    - You want to start fresh with clean device tracking
    - Database schema has changed and you want to rebuild
    - You're switching between storage modes

    Requires --force flag to prevent accidental deletion.

    Args:
        console: Rich console for output

    Flags:
        --force: Required flag to confirm reset
        --keep-backups: Keep backup files (only delete main DB)
    """
    force = "--force" in sys.argv
    keep_backups = "--keep-backups" in sys.argv

    if not force:
        console.print("[red]WARNING: This will DELETE the database and start fresh![/red]")
        console.print("[yellow]To confirm reset, use: ccu reset-db --force[/yellow]")
        console.print("\n[dim]Options:[/dim]")
        console.print("[dim]  --force           Confirm deletion[/dim]")
        console.print("[dim]  --keep-backups    Keep backup files[/dim]")
        return

    db_path = DEFAULT_DB_PATH
    db_dir = db_path.parent

    if not db_path.exists() and not any(db_dir.glob("*.db.bak")):
        console.print("[yellow]No database or backups found. Nothing to reset.[/yellow]")
        return

    try:
        deleted_files = []

        # Show current database stats before deletion
        if db_path.exists():
            try:
                db_stats = get_database_stats()
                if db_stats["total_records"] > 0:
                    console.print("[cyan]Current database:[/cyan]")
                    console.print(f"  Records: {db_stats['total_records']:,}")
                    console.print(f"  Days: {db_stats['total_days']}")
                    console.print(f"  Range: {db_stats['oldest_date']} to {db_stats['newest_date']}\n")
            except:
                pass  # DB might be corrupted, skip stats

            # Delete main database
            db_path.unlink()
            deleted_files.append(str(db_path))
            console.print(f"[green]✓ Deleted database: {db_path.name}[/green]")

        # Delete backups unless --keep-backups is specified
        if not keep_backups:
            backup_files = list(db_dir.glob("*.db.bak")) + list(db_dir.glob("usage_history_backup_*.db"))
            if backup_files:
                console.print(f"\n[cyan]Found {len(backup_files)} backup file(s)[/cyan]")
                for backup in backup_files:
                    backup.unlink()
                    deleted_files.append(str(backup))
                    console.print(f"[green]✓ Deleted backup: {backup.name}[/green]")
        else:
            backup_files = list(db_dir.glob("*.db.bak")) + list(db_dir.glob("usage_history_backup_*.db"))
            if backup_files:
                console.print(f"\n[yellow]Keeping {len(backup_files)} backup file(s)[/yellow]")

        console.print(f"\n[bold green]✓ Database reset complete![/bold green]")
        console.print("[dim]Next 'ccu usage' run will create a fresh database with current device name.[/dim]")

    except Exception as e:
        console.print(f"[red]Error resetting database: {e}[/red]")


#endregion
