import glob
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from enum import Enum
from os.path import join, split
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError
from typing import Union
from urllib.error import HTTPError, URLError

assert sys.version_info >= (3, 7)

CFR_VERSION = "0.152"
SPECIAL_SOURCE_VERSION = "1.11.4"
MANIFEST_LOCATION = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
CLIENT = "client"
SERVER = "server"

SRC_DIR = "./src"
TMP_DIR = "./tmp"


def get_minecraft_path():
    if sys.platform.startswith('linux'):
        return Path("~/.minecraft")
    elif sys.platform.startswith('win'):
        return Path("~/AppData/Roaming/.minecraft")
    elif sys.platform.startswith('darwin'):
        return Path("~/Library/Application Support/minecraft")
    else:
        logging.info("Cannot detect of version : %s. Please report to your closest sysadmin" % sys.platform)
        raise SystemExit(1)


mc_path = get_minecraft_path()


def check_java():
    """Check for java and setup the proper directory if needed"""
    results = []
    if sys.platform.startswith('win'):
        if not results:
            import winreg

            for flag in [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                try:
                    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\JavaSoft\Java Development Kit', 0,
                                       winreg.KEY_READ | flag)
                    version, _ = winreg.QueryValueEx(k, 'CurrentVersion')
                    k.Close()
                    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                       r'Software\JavaSoft\Java Development Kit\%s' % version, 0,
                                       winreg.KEY_READ | flag)
                    path, _ = winreg.QueryValueEx(k, 'JavaHome')
                    k.Close()
                    path = join(str(path), 'bin')
                    subprocess.run(['"%s"' % join(path, 'java'), ' -version'], stdout=open(os.devnull, 'w'),
                                   stderr=subprocess.STDOUT, check=True)
                    results.append(path)
                except (CalledProcessError, OSError):
                    pass
        if not results:
            try:
                subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                results.append('')
            except (CalledProcessError, OSError):
                pass
        if not results and 'ProgramW6432' in os.environ:
            results.append(which('java.exe', path=os.environ['ProgramW6432']))
        if not results and 'ProgramFiles' in os.environ:
            results.append(which('java.exe', path=os.environ['ProgramFiles']))
        if not results and 'ProgramFiles(x86)' in os.environ:
            results.append(which('java.exe', path=os.environ['ProgramFiles(x86)']))
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        if not results:
            try:
                subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                results.append('')
            except (CalledProcessError, OSError):
                pass
        if not results:
            results.append(which('java', path='/usr/bin'))
        if not results:
            results.append(which('java', path='/usr/local/bin'))
        if not results:
            results.append(which('java', path='/opt'))
    results = [path for path in results if path is not None]
    if not results:
        logging.info('Java JDK is not installed ! Please install java JDK from https://java.oracle.com or OpenJDK')
        input("Aborting, press anything to exit")
        raise SystemExit(1)


def get_global_manifest(quiet):
    if Path(f"./versions/version_manifest.json").exists() and Path(f"./versions/version_manifest.json").is_file():
        if not quiet:
            logging.info(
                "Manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    download_file(MANIFEST_LOCATION, f"./versions/version_manifest.json", quiet)


def download_file(url, filename, quiet):
    try:
        if not quiet:
            logging.info(f'Downloading {filename}.')
        f = urllib.request.urlopen(url)
        with open(filename, 'wb+') as local_file:
            local_file.write(f.read())
    except HTTPError as e:
        if not quiet:
            logging.info('HTTP Error')
            logging.info(e)
        raise SystemExit(1)
    except URLError as e:
        if not quiet:
            logging.info('URL Error')
            logging.info(e)
        raise SystemExit(1)


def get_latest_version():
    download_file(MANIFEST_LOCATION, f"manifest.json", True)
    path_to_json = Path(f'manifest.json')
    snapshot = None
    version = None
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["latest"]
            if versions and versions.get("release") and versions.get("release"):
                version = versions.get("release")
                snapshot = versions.get("snapshot")
    path_to_json.unlink()
    return snapshot, version


def get_version_manifest(target_version, quiet):
    if Path(f"./versions/{target_version}/version.json").exists() and Path(
            f"./versions/{target_version}/version.json").is_file():
        if not quiet:
            logging.info(
                "Version manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path('./versions/version_manifest.json')
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["versions"]
            for version in versions:
                if version.get("id") and version.get("id") == target_version and version.get("url"):
                    download_file(version.get("url"), f"./versions/{target_version}/version.json", quiet)
                    break
    else:
        if not quiet:
            logging.error('ERROR: Missing manifest file: version.json')
            input("Aborting, press anything to exit")
        raise SystemExit(1)


def sha256(fname: Union[Union[str, bytes], int]):
    import hashlib
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_version_jar(target_version, side, quiet):
    path_to_json = Path(f"./versions/{target_version}/version.json")
    if Path(f"./versions/{target_version}/{side}.jar").exists() and Path(
            f"./versions/{target_version}/{side}.jar").is_file():
        if not quiet:
            logging.info(f"versions/{target_version}/{side}.jar already existing, not downloading again")
        return
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jsn = json.load(f)
            if jsn.get("downloads") and jsn.get("downloads").get(side) and jsn.get("downloads").get(side).get("url"):
                jar_path = f"./versions/{target_version}/{side}.jar"
                download_file(jsn.get("downloads").get(side).get("url"), jar_path, quiet)
                # In case the server is newer than 21w39a you need to actually extract it first from the archive
                if side == SERVER:
                    if Path(jar_path).exists():
                        with zipfile.ZipFile(jar_path, mode="r") as z:
                            content = None
                            try:
                                content = z.read("META-INF/versions.list")
                            except Exception as _:
                                # we don't have a versions.list in it
                                pass
                            if content is not None:
                                element = content.split(b"\t")
                                if len(element) != 3:
                                    logging.info(
                                        f"Jar should be extracted but version list is not in the correct format, expected 3 fields, got {len(element)} for {content}")
                                    raise SystemExit(1)
                                version_hash = element[0].decode()
                                version = element[1].decode()
                                path = element[2].decode()
                                if version != target_version and not quiet:
                                    logging.info(
                                        f"Warning, version is not identical to the one targeted got {version} exepected {target_version}")
                                new_jar_path = f"./versions/{target_version}"
                                try:
                                    new_jar_path = z.extract(f"META-INF/versions/{path}", new_jar_path)
                                except Exception as e:
                                    logging.error(f"Could not extract to {new_jar_path} with error {e}")
                                    raise SystemExit(1)
                                if Path(new_jar_path).exists():
                                    file_hash = sha256(new_jar_path)
                                    if file_hash != version_hash:
                                        logging.info(
                                            f"Extracted file hash and expected hash did not match up, got {file_hash} expected {version_hash}")
                                        raise SystemExit(1)
                                    try:
                                        shutil.move(new_jar_path, jar_path)
                                        shutil.rmtree(f"./versions/{target_version}/META-INF")
                                    except Exception as e:
                                        logging.info("Exception while removing the temp file", e)
                                        raise SystemExit(1)
                                else:
                                    logging.info(
                                        f"New {side} jar could not be extracted from archive at {new_jar_path}, failure")
                                    raise SystemExit(1)
                    else:
                        logging.info(f"Jar was maybe downloaded but not located, this is a failure, check path at {jar_path}")
                        raise SystemExit(1)
            else:
                if not quiet:
                    logging.info("Could not download jar, missing fields")
                    input("Aborting, press anything to exit")
                raise SystemExit(1)
    else:
        if not quiet:
            logging.error('ERROR: Missing manifest file: version.json')
            input("Aborting, press anything to exit")
        raise SystemExit(1)
    if not quiet:
        logging.info("Done !")


def get_mappings(version, side, quiet):
    if Path(f'./mappings/{version}/{side}.txt').exists() and Path(f'./mappings/{version}/{side}.txt').is_file():
        if not quiet:
            logging.info(
                "Mappings already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path(f'./versions/{version}/version.json')
    if path_to_json.exists() and path_to_json.is_file():
        if not quiet:
            logging.info(f'Found {version}.json')
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jfile = json.load(f)
            url = jfile['downloads']
            if side == CLIENT:  # client:
                if url['client_mappings']:
                    url = url['client_mappings']['url']
                else:
                    if not quiet:
                        logging.error(f'Error: Missing client mappings for {version}')
            elif side == SERVER:  # server
                if url['server_mappings']:
                    url = url['server_mappings']['url']
                else:
                    if not quiet:
                        logging.error(f'Error: Missing server mappings for {version}')
            else:
                if not quiet:
                    logging.error('ERROR, type not recognized')
                raise SystemExit(1)
            if not quiet:
                logging.info(f'Downloading the mappings for {version}..')
            download_file(url, f'./mappings/{version}/{"client" if side == CLIENT else "server"}.txt', quiet)
    else:
        if not quiet:
            logging.error('ERROR: Missing manifest file: version.json')
            input("Aborting, press anything to exit")
        raise SystemExit(1)


def remap(version, side, quiet):
    if not quiet:
        logging.info('=== Remapping jar using SpecialSource ====')
    t = time.time()
    path = Path(f'./versions/{version}/{side}.jar')
    # that part will not be assured by arguments
    if not path.exists() or not path.is_file():
        path_temp = (mc_path / f'versions/{version}/{version}.jar').expanduser()
        if path_temp.exists() and path_temp.is_file():
            r = input("Error, defaulting to client.jar from your local Minecraft folder, continue? (y/n)") or "y"
            if r != "y":
                raise SystemExit(1)
            path = path_temp
    mapp = Path(f'./mappings/{version}/{side}.tsrg')
    specialsource = Path(f'./lib/SpecialSource-{SPECIAL_SOURCE_VERSION}.jar')
    if path.exists() and mapp.exists() and specialsource.exists() and path.is_file() and mapp.is_file() and specialsource.is_file():
        path = path.resolve()
        mapp = mapp.resolve()
        specialsource = specialsource.resolve()
        subprocess.run(['java',
                        '-jar', specialsource.__str__(),
                        '--in-jar', path.__str__(),
                        '--out-jar', f'{SRC_DIR}/{version}-{side}-temp.jar',
                        '--srg-in', mapp.__str__(),
                        "--kill-lvt"  # kill snowmen
                        ], check=True, capture_output=quiet)
        if not quiet:
            logging.info(f'- New -> {version}-{side}-temp.jar')
            t = time.time() - t
            logging.info('Done in %.1fs' % t)
    else:
        if not quiet:
            logging.error(
                f'ERROR: Missing files: ./lib/SpecialSource-{SPECIAL_SOURCE_VERSION}.jar or mappings/{version}/{side}.tsrg or versions/{version}/{side}.jar')
            input("Aborting, press anything to exit")
        raise SystemExit(1)


def decompile_fern_flower(decompiled_version, version, side, quiet, force):
    if not quiet:
        logging.info('=== Decompiling using FernFlower (silent) ===')
    t = time.time()
    path = Path(f'{SRC_DIR}/{version}-{side}-temp.jar')
    fernflower = Path('./lib/fernflower.jar')
    if path.exists() and fernflower.exists():
        path = path.resolve()
        fernflower = fernflower.resolve()
        subprocess.run(['java',
                        '-Xmx4G',
                        '-Xms1G',
                        '-jar', fernflower.__str__(),
                        '-hes=0',  # hide empty super invocation deactivated (might clutter but allow following)
                        '-hdc=0',  # hide empty default constructor deactivated (allow to track)
                        '-dgs=1',  # decompile generic signatures activated (make sure we can follow types)
                        '-lit=1',  # output numeric literals
                        '-asc=1',  # encode non-ASCII characters in string and character
                        '-log=WARN',
                        path.__str__(), f'{SRC_DIR}/{decompiled_version}/{side}'
                        ], check=True, capture_output=quiet)
        if not quiet:
            logging.info(f'- Removing -> {version}-{side}-temp.jar')
        os.remove(f'{SRC_DIR}/{version}-{side}-temp.jar')
        if not quiet:
            logging.info("Decompressing remapped jar to directory")
        with zipfile.ZipFile(f'{SRC_DIR}/{decompiled_version}/{side}/{version}-{side}-temp.jar') as z:
            z.extractall(path=f'{SRC_DIR}/{decompiled_version}/{side}')
        t = time.time() - t
        if not quiet:
            logging.info(f'Done in %.1fs (file was decompressed in {decompiled_version}/{side})' % t)
            logging.info('Remove Extra Jar file? (y/n): ')
            response = input() or "y"
            if response == 'y':
                logging.info(f'- Removing -> {decompiled_version}/{side}/{version}-{side}-temp.jar')
                os.remove(f'{SRC_DIR}/{decompiled_version}/{side}/{version}-{side}-temp.jar')
        if force:
            os.remove(f'{SRC_DIR}/{decompiled_version}/{side}/{version}-{side}-temp.jar')

    else:
        if not quiet:
            logging.error(f'ERROR: Missing files: ./lib/fernflower.jar or {SRC_DIR}/{version}-{side}-temp.jar')
            input("Aborting, press anything to exit")
        raise SystemExit(1)


def decompile_cfr(decompiled_version, version, side, quiet):
    if not quiet:
        logging.info('=== Decompiling using CFR (silent) ===')
    t = time.time()
    path = Path(f'{SRC_DIR}/{version}-{side}-temp.jar')
    cfr = Path(f'./lib/cfr-{CFR_VERSION}.jar')
    if path.exists() and cfr.exists():
        path = path.resolve()
        cfr = cfr.resolve()
        subprocess.run(['java',
                        '-Xmx4G',
                        '-Xms1G',
                        '-jar', cfr.__str__(),
                        path.__str__(),
                        '--outputdir', f'{SRC_DIR}/{decompiled_version}/{side}',
                        '--caseinsensitivefs', 'true',
                        "--silent", "true"
                        ], check=True, capture_output=quiet)
        if not quiet:
            logging.info(f'- Removing -> {version}-{side}-temp.jar')
            logging.info(f'- Removing -> summary.txt')
        os.remove(f'{SRC_DIR}/{version}-{side}-temp.jar')
        os.remove(f'{SRC_DIR}/{decompiled_version}/{side}/summary.txt')
        if not quiet:
            t = time.time() - t
            logging.info('Done in %.1fs' % t)
    else:
        if not quiet:
            logging.error(f'ERROR: Missing files: ./lib/cfr-{CFR_VERSION}.jar or {SRC_DIR}/{version}-{side}-temp.jar')
            input("Aborting, press anything to exit")
        raise SystemExit(1)


def remove_brackets(line, counter):
    while '[]' in line:  # get rid of the array brackets while counting them
        counter += 1
        line = line[:-2]
    return line, counter


def remap_file_path(path):
    remap_primitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J", "byte": "B", "short": "S",
                        "char": "C", "void": "V"}
    return "L" + "/".join(path.split(".")) + ";" if path not in remap_primitives else remap_primitives[path]


def convert_mappings(version, side, quiet):
    with open(f'./mappings/{version}/{side}.txt', 'r') as inputFile:
        file_name = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if not line.startswith('    '):
                obf_name = obf_name.split(":")[0]
                file_name[remap_file_path(deobf_name)] = obf_name  # save it to compare to put the Lb

    with open(f'./mappings/{version}/{side}.txt', 'r') as inputFile, open(f'./mappings/{version}/{side}.tsrg',
                                                                        'w+') as outputFile:
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if line.startswith('    '):
                obf_name = obf_name.rstrip()  # remove leftover right spaces
                deobf_name = deobf_name.lstrip()  # remove leftover left spaces
                method_type, method_name = deobf_name.split(" ")  # split the `<methodType> <methodName>`
                method_type = method_type.split(":")[
                    -1]  # get rid of the line numbers at the beginning for functions eg: `14:32:void`-> `void`
                if "(" in method_name and ")" in method_name:  # detect a function function
                    variables = method_name.split('(')[-1].split(')')[0]  # get rid of the function name and parenthesis
                    function_name = method_name.split('(')[0]  # get the function name only
                    array_length_type = 0

                    method_type, array_length_type = remove_brackets(method_type, array_length_type)
                    method_type = remap_file_path(
                        method_type)  # remap the dots to / and add the L ; or remap to a primitives character
                    method_type = "L" + file_name[
                        method_type] + ";" if method_type in file_name else method_type  # get the obfuscated name of the class
                    if "." in method_type:  # if the class is already packaged then change the name that the obfuscated gave
                        method_type = "/".join(method_type.split("."))
                    for i in range(array_length_type):  # restore the array brackets upfront
                        if method_type[-1] == ";":
                            method_type = "[" + method_type[:-1] + ";"
                        else:
                            method_type = "[" + method_type

                    if variables != "":  # if there is variables
                        array_length_variables = [0] * len(variables)
                        variables = list(variables.split(","))  # split the variables
                        for i in range(len(variables)):  # remove the array brackets for each variable
                            variables[i], array_length_variables[i] = remove_brackets(variables[i],
                                                                                      array_length_variables[i])
                        variables = [remap_file_path(variable) for variable in
                                     variables]  # remap the dots to / and add the L ; or remap to a primitives character
                        variables = ["L" + file_name[variable] + ";" if variable in file_name else variable for variable
                                     in variables]  # get the obfuscated name of the class
                        variables = ["/".join(variable.split(".")) if "." in variable else variable for variable in
                                     variables]  # if the class is already packaged then change the obfuscated name
                        for i in range(len(variables)):  # restore the array brackets upfront for each variable
                            for j in range(array_length_variables[i]):
                                if variables[i][-1] == ";":
                                    variables[i] = "[" + variables[i][:-1] + ";"
                                else:
                                    variables[i] = "[" + variables[i]
                        variables = "".join(variables)

                    outputFile.write(f'\t{obf_name} ({variables}){method_type} {function_name}\n')
                else:
                    outputFile.write(f'\t{obf_name} {method_name}\n')

            else:
                obf_name = obf_name.split(":")[0]
                outputFile.write(remap_file_path(obf_name)[1:-1] + " " + remap_file_path(deobf_name)[1:-1] + "\n")
    if not quiet:
        logging.info("Done !")


def make_paths(version, side, removal_bool, force, forceno):
    path = Path(f'./mappings/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)
    path = Path(f'./versions/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        path = Path(f'./versions/{version}/version.json')
        if path.is_file() and removal_bool:
            path.unlink()
    if Path("./versions").exists():
        path = Path(f'./versions/version_manifest.json')
        if path.is_file() and removal_bool:
            path.unlink()

    path = Path(f'./versions/{version}/{side}.jar')
    if path.exists() and path.is_file() and removal_bool:
        if force:
            path = Path(f'./versions/{version}')
            shutil.rmtree(path)
            path.mkdir(parents=True)
        else:
            aw = input(f"versions/{version}/{side}.jar already exists, wipe it (w) or ignore (i) ? ") or "i"
            path = Path(f'./versions/{version}')
            if aw == "w":
                shutil.rmtree(path)
                path.mkdir(parents=True)

    path = Path(f'{SRC_DIR}/{version}/{side}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if force:
            shutil.rmtree(Path(f"{SRC_DIR}/{version}/{side}"))
        elif forceno:
            version = version + side + "_" + str(random.getrandbits(128))
        else:
            aw = input(
                f"{SRC_DIR}/{version}/{side} already exists, wipe it (w), create a new folder (n) or kill the process (k) ? ")
            if aw == "w":
                shutil.rmtree(Path(f"{SRC_DIR}/{version}/{side}"))
            elif aw == "n":
                version = version + side + "_" + str(random.getrandbits(128))
            else:
                raise SystemExit(1)
        path = Path(f'{SRC_DIR}/{version}/{side}')
        path.mkdir(parents=True)

    path = Path(f'{TMP_DIR}/{version}/{side}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)
    return version


def delete_dependencies(version, side):
    path = f'{TMP_DIR}/{version}/{side}'

    with zipfile.ZipFile(f'{SRC_DIR}/{version}-{side}-temp.jar') as z:
        z.extractall(path=path)

    for _dir in [join(path, "com"), path]:
        for f in os.listdir(_dir):
            if os.path.isdir(join(_dir, f)) and split(f)[-1] not in ['net', 'assets', 'data', 'mojang', 'com',
                                                                     'META-INF']:
                shutil.rmtree(join(_dir, f))

    with zipfile.ZipFile(f'{SRC_DIR}/{version}-{side}-temp.jar', 'w') as z:
        for f in glob.iglob(f'{path}/**', recursive=True):
            z.write(f, arcname=f[len(path) + 1:])


class Decompiler(str, Enum):
    CFR = "cfr"
    F = "f"


class Side(str, Enum):
    CLIENT = "client"
    SERVER = "server"


def download_n_decompile(minecraft_version: str,
                         quiet: bool = False,
                         clean: bool = True,
                         decompiler_type: Decompiler = "cfr",
                         side: Side = "server",
                         force: bool = False,
                         force_by_new_output: bool = True,
                         non_use_auto_mode: bool = False,
                         download_mapping: bool = True,
                         remap_mapping: bool = True,
                         download_jar: bool = True,
                         remap_jar: bool = True,
                         delete_dep: bool = True,
                         decompile: bool = True) -> str:
    """
    :param minecraft_version:
        The version you want to decompile (valid version starting from 19w36a (snapshot) and 1.14.4 (releases))
        Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest})
    :param quiet: 
        Doesnt display the messages
    :param clean: 
        Clean old runs
    :param decompiler_type:
        Choose between fernflower and cfr.
    :param side:
        The side you want to decompile (either client or server)
    :param force:
        Force resolving conflict by replacing old files.
    :param force_by_new_output:
        Force resolving conflict by creating new directories.
    :param non_use_auto_mode:
        Choose between auto and manual mode.
    :param download_mapping:
        Download the mappings (only if auto off)
    :param remap_mapping:
        Remap the mappings to tsrg (only if auto off)
    :param download_jar:
        Download the jar (only if auto off)
    :param remap_jar: 
        Remap the jar (only if auto off)
    :param delete_dep: 
        Delete the dependencies (only if auto off)
    :param decompile: 
        Decompile (only if auto off)

    :return:
        The path to the decompiled files
    """
    check_java()
    snapshot, latest = get_latest_version()

    if snapshot is None or latest is None:
        logging.error("Error getting latest versions, please refresh cache")
        sys.exit(1)

    if not quiet:
        logging.info("Decompiling using official mojang mappings (Default option are in uppercase, you can just enter)")

    # This ain't my code
    removal_bool = clean
    version = minecraft_version

    if version is None:
        logging.error(
            "Error you should provide a version with --mcversion <version>, use latest or snap if you dont know which one")
        raise SystemExit(1)

    if version in ["snap", "s", "snapshot"]:
        version = snapshot

    if version in ["latest", "l"]:
        version = latest

    side = side.lower() if side.lower() in ["client", "server", "c", "s"] else CLIENT
    side = CLIENT if side in ["client", "c"] else SERVER
    decompiled_version = make_paths(version, side, removal_bool, force, force_by_new_output)
    get_global_manifest(quiet)
    get_version_manifest(version, quiet)

    r = not non_use_auto_mode
    if r:
        get_mappings(version, side, quiet)
        convert_mappings(version, side, quiet)
        get_version_jar(version, side, quiet)
        remap(version, side, quiet)
        if decompiler_type.lower() == "cfr":
            decompile_cfr(decompiled_version, version, side, quiet)
        else:
            decompile_fern_flower(decompiled_version, version, side, quiet, force)
        if not quiet:
            logging.info("===FINISHED DECOMPILING===")
            logging.info(f"output is in {SRC_DIR}/{decompiled_version}")
            return str(Path(f"{SRC_DIR}/{decompiled_version}").absolute())
        sys.exit(0)

    r = download_mapping
    if r:
        get_mappings(version, side, quiet)

    r = remap_mapping
    if r:
        convert_mappings(version, side, quiet)

    r = download_jar
    if r:
        get_version_jar(version, side, quiet)

    r = remap_jar
    if r:
        remap(version, side, quiet)

    r = delete_dep
    if r:
        delete_dependencies(version, side)

    r = decompile
    if r:
        if decompiler_type.lower() == "cfr":
            decompile_cfr(decompiled_version, version, side, quiet)
        else:
            decompile_fern_flower(decompiled_version, version, side, quiet, force)

    if not quiet:
        logging.info("===FINISHED DECOMPILING===")
        logging.info(f"output is in {SRC_DIR}/{decompiled_version}")
        return str(Path(f"{SRC_DIR}/{decompiled_version}").absolute())
