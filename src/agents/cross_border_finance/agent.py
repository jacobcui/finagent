import subprocess
import sys
from pathlib import Path

import typer

cli = typer.Typer()


@cli.command()
def ui():
    """Launch the Exchange Rate Lock Engine UI"""
    script_path = Path(__file__).parent / "lock_engine.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(script_path)]
    # Use check=False so we don't crash if user Ctrl-C's the UI
    subprocess.run(cmd, check=False)


@cli.command()
def compliance():
    """Launch the Compliance Self-Check Tool UI"""
    script_path = Path(__file__).parent / "compliance.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(script_path)]
    subprocess.run(cmd, check=False)


@cli.command()
def tax_report():
    """Launch the ATO Tax Report Generation Tool"""
    script_path = Path(__file__).parent / "tax_report.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(script_path)]
    subprocess.run(cmd, check=False)


@cli.command()
def blockchain_log():
    """Launch the Blockchain Log Evidence Module (Sepolia)"""
    script_path = Path(__file__).parent / "blockchain_log.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(script_path)]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    cli()
