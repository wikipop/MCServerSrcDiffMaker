import argparse
import subprocess
import os
import logging
from pathlib import Path

from decompiler import download_n_decompile, get_latest_version, Decompiler


def download_n_decompile_wrapper(version: str,
                                 use_fernflower: bool,
                                 force: bool = False,
                                 ) -> str:
    if not use_fernflower:
        return download_n_decompile(version, force=force)
    elif use_fernflower:
        return download_n_decompile(version, force=force, decompiler_type=Decompiler.F)


def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

    parser = argparse.ArgumentParser(description="Decompile and Compare two Minecraft versions")
    parser.add_argument("version", type=str, help="Minecraft Version 1", nargs=1)
    parser.add_argument("compare", type=str, help="Minecraft Version 2 (Default Latest Snapshot)", nargs='?',
                        default="snap")
    parser.add_argument("--ide-location", "-l", dest="ide_location", type=str,
                        help="Provide JetBrains IDE location or PATH name", nargs='?', default="idea64.exe")
    parser.add_argument("--re-download", "-rd", dest="re_download", action="store_true", default=False,
                        help="Force re-download")
    parser.add_argument("--no-compare", "-nc", dest="no_compare", action="store_true", default=False,
                        help="Skip comparing the decompiled versions")
    parser.add_argument("--fern-flower", "-ff", dest="fern_flower", action="store_true", default=False,
                        help="Use FernFlower Decompiler instead of CFR")

    args = parser.parse_args()

    if not Path(args.ide_location).exists():
        logging.error("IntelliJ IDE not found. Please provide the correct path")
        return

    snap_version, latest_version = get_latest_version()

    match args.version[0]:
        case "snap":
            args.version[0] = snap_version
        case "latest":
            args.version[0] = latest_version

    match args.compare:
        case "snap":
            args.compare = snap_version
        case "latest":
            args.compare = latest_version

    if args.version[0] == args.compare:
        logging.error("Versions are same. Exiting...")
        logging.info(f"Version 1: {args.version[0]}")
        logging.info(f"Version 2: {args.compare}")
        return

    if Path(f"./src/{args.version[0]}").exists() and not args.re_download:
        logging.info(f"Version {args.version[0]} already decompiled. Skipping...")
        logging.info(f"Use --re-download to force re-download")
        version1_path = str(Path(f"./src/{args.version[0]}").absolute())
    else:
        version1_path = download_n_decompile_wrapper(args.version[0], args.fern_flower, force=True)

    if Path(f"./src/{args.compare}").exists() and not args.re_download:
        logging.info(f"Version {args.compare} already decompiled. Skipping...")
        logging.info(f"Use --re-download to force re-download")
        version2_path = str(Path(f"./src/{args.compare}").absolute())
    else:
        version2_path = download_n_decompile_wrapper(args.compare, args.fern_flower, force=True)

    logging.info(f"Comparing {args.version[0]} with {args.compare}")
    logging.info(f"Version 1 Path: {version1_path}")
    logging.info(f"Version 2 Path: {version2_path}")

    if not args.no_compare:
        subprocess.run([args.ide_location, "diff", version1_path, version2_path])
    else:
        logging.info("Skipping comparison with --no-compare flag")


if __name__ == '__main__':
    main()
