"""
A script to perform a health check on every LuxOS miner in the network.
"""

import time
import logging
import argparse
import os
import csv
import json
import threading
import asyncio
from datetime import datetime
from typing import Any

from tqdm.asyncio import tqdm as async_tqdm
import asyncpg
import shutil
import yaml
import pandas as pd

from luxos.api import logon_required

from luxos.scripts.luxos import (generate_ip_range,
                   add_session_id_parameter, parameters_to_string,
                   check_res_structure, get_str_field)

LOGGING_CONFIG = {
    'level': logging.INFO,
    'format': "%(asctime)s [%(levelname)s] %(message)s",
    'handlers':
    [logging.StreamHandler(),
     logging.FileHandler("LuxOS-CLI.log")],
}

COLUMN_NAMES = [
    'ip', 'model', 'mac_address', 'os', 'board', 'version', 'elapsed',
    'board_count', 'm_5_hashrate', 'atm_enabled', 'chips_healthy',
    'chips_unhealthy_count', 'board0_5m', 'board1_5m', 'board2_5m',
    'board0_profile', 'board1_profile', 'board2_profile', 'board0_temp',
    'board1_temp', 'board2_temp', 'pool_user', 'diff_accept_0',
    'diff_reject_0', 'diff_stale_0', 'diff_accept_1', 'diff_reject_1',
    'diff_stale_1', 'diff_accept_2', 'diff_reject_2', 'diff_stale_2'
]

BUFFER_SIZE = 100
MAX_RETRIES = 3

INTERMEDIATE_CSV = "report_in_progress.csv"

LUXOS_MINERS = []

log = logging.getLogger(__name__)


def parse_args():
    """Parse arguments from config file."""
    path = "config.yaml"
    with open(path, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError:
            log.exception("Unable to load configs from %s!", path)
            raise

    args = argparse.Namespace()

    args.verbose = config['output']['verbose']
    args.csv_output = config['output']['csv_output']
    args.local_grafana_file = config['output']['local_grafana_file']
    args.report_output_type = config['output']['report_output_type']
    args.ipfile = config['ipfile']
    args.range_start = config['ip_settings']['range_start']
    args.range_end = config['ip_settings']['range_end']
    args.max_threads = config['threads']['max_threads']
    args.timeout = config['luxos']['timeout']
    args.port = config['luxos']['port']
    args.port = config['luxos']['port']
    args.sleep_between_executions = config['sleep_between_executions']
    args.db_host = config['database']['host']
    args.db_port = config['database']['port']
    args.db_database = config['database']['name']
    args.db_user = config['database']['user']
    args.db_password = config['database']['password']
    args.db_table_name = config['database']['table_name']
    args.executeconfigs = config['execution']['executeconfigs']
    args.executeconfig_tempctrlset = config['execution']['tempctrlset'][
        'execute']
    args.executeconfig_tempctrlset_param1 = config['execution']['tempctrlset'][
        'param1']
    args.executeconfig_tempctrlset_param2 = config['execution']['tempctrlset'][
        'param2']
    args.executeconfig_tempctrlset_param3 = config['execution']['tempctrlset'][
        'param3']
    args.executeconfig_atmset = config['execution']['atmset']['execute']
    args.executeconfig_atmset_param1 = config['execution']['atmset']['param1']
    args.executeconfig_atmset_param2 = config['execution']['atmset']['param2']
    args.executeconfig_atmset_param3 = config['execution']['atmset']['param3']
    args.executeconfig_atmset_param4 = config['execution']['atmset']['param4']
    args.executeconfig_fanset = config['execution']['fanset']['execute']
    args.executeconfig_fanset_param1 = config['execution']['fanset']['param1']
    args.executeconfig_fanset_param2 = config['execution']['fanset']['param2']
    args.executeconfig_immersionswitch = config['execution'][
        'immersionswitch']['execute']
    args.executeconfig_immersionswitch_param1 = config['execution'][
        'immersionswitch']['param1']

    return args


def generate_filename(base_name="output"):
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y_%m_%d_%H%M%S")

    if '.' in base_name:
        name, extension = os.path.splitext(base_name)
    else:
        name = base_name
        extension = ".csv"

    return f"health_checks/{name}_{timestamp}{extension}"


def load_ip_list_from_csv(csv_file):
    if not os.path.exists(csv_file):
        logging.info(f"Error: {csv_file} file not found.")
        exit(1)
    df = pd.read_csv(csv_file)
    if 'hostname' not in df.columns:
        logging.info("Error: No 'hostname' column found in CSV.")
        exit(1)
    return df['hostname'].dropna().tolist()


def get_value_with_default(dictionary, key, default=0):
    """
    Retrieve a value from a dictionary for the given key.
    If the key is not present or the value is None, return the default value.
    """
    return dictionary.get(
        key, default) if dictionary.get(key) is not None else default


async def internal_send_cgminer_command(host: str, port: int, command: str,
                                        timeout_sec: int,
                                        verbose: bool) -> dict[str, Any]:
    writer = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(
            host, port),
                                                timeout=timeout_sec)
        writer.write(command.encode())
        await writer.drain()

        response = bytearray()
        while True:
            data = await asyncio.wait_for(reader.read(1), timeout=timeout_sec)
            if not data:
                break
            null_index = data.find(b'\x00')
            if null_index >= 0:
                response += data[:null_index]
                break
            response += data

        r = json.loads(response.decode())
        if verbose:
            logging.info(r)
        return r

    except asyncio.TimeoutError:
        logging.error(f"Timeout on {host}.")
        return {}
    except Exception as e:
        logging.error(f"Error during socket operation: {e}")
        return {}
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()


async def send_cgminer_command(host: str, port: int, cmd: str, param: str,
                               timeout_sec: int, verbose: bool) -> dict[str, Any]:
    req = str(f"{{\"command\": \"{cmd}\", \"parameter\": \"{param}\"}}\n")
    if verbose:
        logging.info(
            f"Executing command: {cmd} with params: {param} to host: {host}")

    return await internal_send_cgminer_command(host, port, req, timeout_sec,
                                               verbose)


async def send_cgminer_simple_command(host: str, port: int, cmd: str,
                                      timeout: int, verbose: bool) -> dict[str, Any]:
    req = str(f"{{\"command\": \"{cmd}\"}}\n")
    if verbose:
        logging.info(f"Executing command: {cmd} to host: {host}")
    return await internal_send_cgminer_command(host, port, req, timeout,
                                               verbose)


async def logon(host: str, port: int, timeout: int, verbose: bool) -> str:
    res = await send_cgminer_simple_command(host, port, "logon", timeout,
                                            verbose)
    check_res_structure(res, "SESSION", 1, 1)
    session = res["SESSION"][0]
    s = get_str_field(session, "SessionID")
    if s == "":
        raise ValueError("error: invalid session id")
    return s


async def execute_command(host: str, port: int, timeout_sec: int, cmd: str,
                          parameters: list, verbose: bool):
    try:
        logon_req = logon_required(cmd)
        if logon_req:
            sid = await logon(host, port, timeout_sec, verbose)
            parameters = add_session_id_parameter(sid, parameters)
            if verbose:
                logging.info(
                    f'Command requires a SessionID, logging in for host: {host}'
                )
                logging.info(f'SessionID obtained for {host}: {sid}')
        # TODO fix this typing issue
        elif not logon_required and verbose:  # type: ignore
            logging.info(f"Logon not required for executing {cmd}")
        param_string = parameters_to_string(parameters)
        if verbose:
            logging.info(f"{cmd} on {host} with parameters: {param_string}")
        res = await send_cgminer_command(host, port, cmd, param_string,
                                         timeout_sec, verbose)

        if verbose:
            logging.info(res)
        if logon_req:
            await send_cgminer_command(host, port, "logoff", sid, timeout_sec,
                                       verbose)

        return res
    except Exception as e:
        logging.error(f"Error executing {cmd} on {host}: {e}")


def parse_devs(json):
    devs_data = {
        'alive_board_count': 0,
        '5m_hr': 0,
        'elapsed': json.get('DEVS', [{}])[0].get('Device Elapsed', 0) / 60,
        'boards': []
    }

    all_boards = json.get('DEVS', [])
    for i in range(3):
        board = all_boards[i] if i < len(all_boards) else {}

        board_data = {
            '5m_hr': get_value_with_default(board, 'MHS 5m', 0) / 1e6,
            'temperature': board.get('Temperature', 0),
            'profile': board.get('Profile', 'Unknown')
        }

        devs_data['boards'].append(board_data)

        if board.get('Status') == 'Alive':
            devs_data['alive_board_count'] += 1
            devs_data['5m_hr'] += board_data['5m_hr']

    return devs_data


def parse_board(fgpabuildhex, fpgabuildidstr):
    if fgpabuildhex.lower().startswith('0xbbb'):
        return "BBB"
    elif fgpabuildhex == '0x000A113D':
        return "AML"
    elif ''.join(e for e in fpgabuildidstr
                 if e.isalnum())[2:-2] == fgpabuildhex[2:]:
        return "Xilinx"

    return "Unknown"


def parse_healthchip(healthchipget):
    try:
        unhealthy_count = 0
        for chip in healthchipget.get("CHIPS", []):
            if chip.get("Healthy") == "N":
                unhealthy_count += 1

        healthy = unhealthy_count == 0

        return {
            'chips_healthy': healthy,
            'chips_unhealthy_count': unhealthy_count
        }

    except Exception as e:
        logging.error(f"Error processing healthchipget data: {e}")
        return {}


def parse_config(json):
    json = json.get('CONFIG', [{}])[0]

    fgpabuildhex = json.get('FPGABuildIdHex', '')
    fpgabuildidstr = json.get('FPGABuildIdStr', '')
    if fgpabuildhex:
        board = parse_board(fgpabuildhex, fpgabuildidstr)

    config_data = {
        'is_atm_enabled': json.get('IsAtmEnabled', False),
        'model': json.get('Model', 'Unknown'),
        'mac_addr': json.get('MACAddr', 'Unknown'),
        'os': json.get('OS', 'Unknown'),
        'board': board
    }
    return config_data


def parse_version(json):
    try:
        luxminer_version = json.get('VERSION',
                                    [{}])[0].get('LUXminer', 'Unknown')
    except Exception:
        luxminer_version = 'Unknown'
    return {'version': luxminer_version}


def parse_stats(json):
    elapsed = json.get('STATS', [{}])[0].get('Elapsed', 0) / 60
    stats_data = {'elapsed': elapsed}
    return stats_data


def parse_pools(json):
    pool_data = {}
    pools = json.get('POOLS', [{}])

    try:
        pool_data['pool_user'] = pools[0].get('User', '')
    except Exception:
        pool_data['pool_user'] = ''

    for pool_id in range(3):
        try:
            pool = pools[pool_id]
            pool_data[f'diff_accept_{pool_id}'] = pool.get(
                'Difficulty Accepted', 'Unknown')
            pool_data[f'diff_reject_{pool_id}'] = pool.get(
                'Difficulty Rejected', 'Unknown')
            pool_data[f'diff_stale_{pool_id}'] = pool.get(
                'Difficulty Stale', 'Unknown')
        except Exception:
            pool_data[f'diff_accept_{pool_id}'] = 'Pool_ID out of range.'
            pool_data[f'diff_reject_{pool_id}'] = 'Pool_ID out of range.'
            pool_data[f'diff_stale_{pool_id}'] = 'Pool_ID out of range.'

    return pool_data


def parse_bitmain_stats(data):
    stats = data.get('STATS', [{}])

    while len(stats) < 2:
        stats.append({})
    j0 = stats[0]
    j1 = stats[1]

    stats_data = {
        'model':
        j0.get('Type', 'Unknown'),
        'MACAddress':
        'Unknown',
        'OS':
        'bitmain',
        'Elapsed':
        j1.get('Elapsed', 0) / 60,
        'Board Count':
        j1.get('miner_count', 0),
        '5M Hashrate': (float(j1.get('chain_rate1', 0) or 0) +
                        float(j1.get('chain_rate2', 0) or 0) +
                        float(j1.get('chain_rate3', 0) or 0)) / 1e3,
        'ATM Enabled':
        'Unknown',
        'Board05M':
        float(j1.get('chain_rate1', 0) or 0),
        'Board15M':
        float(j1.get('chain_rate2', 0) or 0),
        'Board25M':
        float(j1.get('chain_rate3', 0) or 0),
        'Board0 Profile':
        j1.get('freq1', 0),
        'Board1 Profile':
        j1.get('freq2', 0),
        'Board2 Profile':
        j1.get('freq3', 0),
        'Board0 Temp':
        j1.get('temp2_1', 0),
        'Board1 Temp':
        j1.get('temp2_2', 0),
        'Board2 Temp':
        j1.get('temp2_3', 0),
    }

    return stats_data


def generate_row(ip, devs, config, pools, version, healthchipget):
    row_data = [
        ip,
        config.get('model', ''),
        config.get('mac_addr', ''),
        config.get('os', ''),
        config.get('board', ''),
        version.get('version', ''),
        devs.get('elapsed', ''),
        devs.get('alive_board_count', ''),
        devs.get('5m_hr', ''),
        config.get('is_atm_enabled', '')
    ]
    healthchipget = [
        healthchipget.get('chips_healthy', ''),
        healthchipget.get('chips_unhealthy_count', '')
    ]
    pool_data = [
        pools.get('pool_user', ''),
        pools.get('diff_accept_0', ''),
        pools.get('diff_reject_0', ''),
        pools.get('diff_stale_0', ''),
        pools.get('diff_accept_1', ''),
        pools.get('diff_reject_1', ''),
        pools.get('diff_stale_1', ''),
        pools.get('diff_accept_2', ''),
        pools.get('diff_reject_2', ''),
        pools.get('diff_stale_2', '')
    ]
    boards = devs.get('boards', [])
    if boards and not isinstance(boards, list):
        boards = [boards]

    board_5m_hrs = [board.get('5m_hr', '') for board in boards]
    board_profiles = [board.get('profile', '') for board in boards]
    board_temps = [board.get('temperature', '') for board in boards]

    return row_data + healthchipget + board_5m_hrs + board_profiles + board_temps + pool_data


def generate_empty_row(ip):
    return [ip] + ['' for _ in COLUMN_NAMES[1:]]


def generate_bitmain_row(ip, stats, pools):
    healthchip = {}
    version = {}

    stats_data = [
        ip,
        stats.get('model', ''),
        stats.get('MACAddress', ''),
        stats.get('OS', ''),
        stats.get('Board', ''),
        version.get('Version', ''),
        stats.get('Elapsed', ''),
        stats.get('Board Count', ''),
        stats.get('5M Hashrate', ''),
        stats.get('ATM Enabled', ''),
        healthchip.get('chips_healthy', ''),
        healthchip.get('chips_unhealthy_count', ''),
        stats.get('Board05M', ''),
        stats.get('Board15M', ''),
        stats.get('Board25M', ''),
        stats.get('Board0 Profile', ''),
        stats.get('Board1 Profile', ''),
        stats.get('Board2 Profile', ''),
        stats.get('Board0 Temp', ''),
        stats.get('Board1 Temp', ''),
        stats.get('Board2 Temp', '')
    ]

    pool_data = [
        pools.get('pool_user', ''),
        pools.get('diff_accept_0', ''),
        pools.get('diff_reject_0', ''),
        pools.get('diff_stale_0', ''),
        pools.get('diff_accept_1', ''),
        pools.get('diff_reject_1', ''),
        pools.get('diff_stale_1', ''),
        pools.get('diff_accept_2', ''),
        pools.get('diff_reject_2', ''),
        pools.get('diff_stale_2', '')
    ]

    return stats_data + pool_data


async def create_connection_pool(db_config):
    return await asyncpg.create_pool(**db_config)


async def insert_to_db(pool, rows_to_insert, table_name):
    async with pool.acquire() as conn:
        async with conn.transaction():
            for row in rows_to_insert:
                converted_row = [str(item) for item in row]

                await conn.execute(
                    f'''
                    INSERT INTO {table_name}(
                        ip, model, mac_address, os, board, version, elapsed, board_count, 
                        m_5_hashrate, atm_enabled, chips_healthy, chips_unhealthy_count, board0_5m, board1_5m, board2_5m, 
                        board0_profile, board1_profile, board2_profile, board0_temp, 
                        board1_temp, board2_temp, pool_user, diff_accept_0, diff_reject_0, 
                        diff_stale_0, diff_accept_1, diff_reject_1, diff_stale_1, 
                        diff_accept_2, diff_reject_2, diff_stale_2
                    ) VALUES(
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 
                        $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31
                    )
                    ''', *converted_row)


async def append_to_buffer_and_check(buffer, row, lock, pool, table_name):
    rows_to_insert = []
    async with lock:
        buffer.append(row)
        if len(buffer) >= BUFFER_SIZE:
            rows_to_insert = list(buffer)
            buffer.clear()

    if rows_to_insert:
        await insert_to_db(pool, rows_to_insert, table_name)


async def handle_csv_row(row, lock, buffer, extra_arg=None, table_name=None):
    async with lock:
        buffer.append(row)

        if len(buffer) >= BUFFER_SIZE:
            with open(INTERMEDIATE_CSV, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(buffer)
            del buffer[:]


async def handle_db_row(row, lock, buffer, pool, table_name):
    await append_to_buffer_and_check(buffer, row, lock, pool, table_name)


async def execute_with_retries(ip, port, timeout, command_name, verbose):
    for retry in range(1, MAX_RETRIES + 1):
        result = await execute_command(ip, port, timeout * retry, command_name,
                                       '', verbose)
        if result and isinstance(result, dict):
            return result
        logging.warning(
            f"Attempt {retry} failed for {ip}, command {command_name}. Retrying..."
        )
    return None


async def handle_devs_and_config(ip, res_devs, args, lock, buffer,
                                 handle_row_func, extra_arg):
    devs = parse_devs(res_devs)
    res_config = await execute_with_retries(ip, args.port, args.timeout,
                                            'config', args.verbose)
    if not res_config:
        logging.warning(
            f"Failed to get config for {ip} after {MAX_RETRIES} attempts. Skipping."
        )
        return
    config = parse_config(res_config)

    res_pools = await execute_with_retries(ip, args.port, args.timeout,
                                           'pools', args.verbose)

    if not res_pools:
        logging.warning(
            f"Failed to get pools for {ip} after {MAX_RETRIES} attempts. Skipping."
        )
        return

    res_version = await execute_with_retries(ip, args.port, args.timeout,
                                             'version', args.verbose)

    if not res_version:
        logging.warning(
            f"Failed to get version for {ip} after {MAX_RETRIES} attempts. Skipping."
        )
        return

    res_healthchipget = await execute_with_retries(ip, args.port, args.timeout,
                                                   'healthchipget',
                                                   args.verbose)

    if not res_healthchipget:
        logging.warning(
            f"Failed to get healthchipget for {ip} after {MAX_RETRIES} attempts. Skipping."
        )
        return

    healthchipget = parse_healthchip(res_healthchipget)
    version = parse_version(res_version)
    pools = parse_pools(res_pools)
    new_row = generate_row(ip, devs, config, pools, version, healthchipget)
    await handle_row_func(new_row, lock, buffer, extra_arg, args.db_table_name)


async def handle_status_and_stats(ip, args, lock, buffer, handle_row_func,
                                  extra_arg):
    res_bitmain = await execute_with_retries(ip, args.port, args.timeout,
                                             'stats', args.verbose)
    if not res_bitmain:
        logging.warning(
            f"Failed to get stats for {ip} after {MAX_RETRIES} attempts. Skipping."
        )
        return

    res_pools = await execute_with_retries(ip, args.port, args.timeout,
                                           'pools', args.verbose)
    if not res_pools:
        logging.warning(
            f"Failed to get pools for {ip} after {MAX_RETRIES} attempts. Skipping."
        )
        return

    pools = parse_pools(res_pools)

    stats = parse_bitmain_stats(res_bitmain)
    new_row = generate_bitmain_row(ip, stats, pools)
    await handle_row_func(new_row, lock, buffer, extra_arg, args.db_table_name)


async def handle_unknown_response(ip, args, res_devs, lock, buffer,
                                  handle_row_func, extra_arg):
    logging.error(f'Unknown API response from {ip}: {res_devs}')
    new_row = generate_empty_row(ip)
    await handle_row_func(new_row, lock, buffer, extra_arg, args.db_table_name)


async def healthcheck(ip,
                      handle_row_func,
                      buffer,
                      lock,
                      args,
                      sem,
                      extra_arg=None):
    async with sem:
        res_devs = await execute_with_retries(ip, args.port, args.timeout,
                                              'devs', args.verbose)
        if not res_devs:
            logging.warning(
                f"Failed to get a response for {ip} after {MAX_RETRIES} attempts. Skipping."
            )
            new_row = generate_empty_row(ip)
            await handle_row_func(new_row, lock, buffer, extra_arg,
                                  args.db_table_name)
            return

        keys = list(res_devs.keys())

        if keys == ['DEVS', 'STATUS', 'id']:
            await handle_devs_and_config(ip, res_devs, args, lock, buffer,
                                         handle_row_func, extra_arg)

            if args.executeconfigs == 'True':
                async with lock:
                    LUXOS_MINERS.append(ip)
        elif keys == ['STATUS', 'DEVS', 'id']:
            await handle_status_and_stats(ip, args, lock, buffer,
                                          handle_row_func, extra_arg)

        else:
            await handle_unknown_response(ip, args, res_devs, lock, buffer,
                                          handle_row_func, extra_arg)


async def execute_configs(ip, args):
    if args.executeconfig_atmset == 'True':
        try:
            await execute_command(ip, args.port, args.timeout, 'atmset', [
                args.executeconfig_atmset_param1,
                args.executeconfig_atmset_param2,
                args.executeconfig_atmset_param3,
                args.executeconfig_atmset_param4
            ], args.verbose)
            logging.info(f"Executed atmset config on {ip}")
        except Exception as e:
            logging.error(f"Failed to execute atmset config on {ip}: {e}")

    if args.executeconfig_fanset == 'True':
        try:
            await execute_command(ip, args.port, args.timeout, 'fanset', [
                str(args.executeconfig_fanset_param1),
                str(args.executeconfig_fanset_param2)
            ], args.verbose)
            logging.info(f"Executed fanset config on {ip}")
        except Exception as e:
            logging.error(f"Failed to execute fanset config on {ip}: {e}")

    if args.executeconfig_tempctrlset == 'True':
        try:
            await execute_command(ip, args.port, args.timeout, 'tempctrlset', [
                str(args.executeconfig_tempctrlset_param1),
                str(args.executeconfig_tempctrlset_param2),
                str(args.executeconfig_tempctrlset_param3)
            ], args.verbose)
            logging.info(f"Executed tempctrlset config on {ip}")
        except Exception as e:
            logging.error(f"Failed to execute tempctrlset config on {ip}: {e}")

    if args.executeconfig_immersionswitch == 'True':
        try:
            await execute_command(
                ip, args.port, args.timeout, 'immersionswitch',
                [str(args.executeconfig_immersionswitch_param1)], args.verbose)
            logging.info(f"Executed immersionswitch config on {ip}")
        except Exception as e:
            logging.error(
                f"Failed to execute immersionswitch config on {ip}: {e}")


async def main_loop(ip_list, args, lock, sem, buffer, db_config):
    health_checks_folder = os.path.join(os.getcwd(), "health_checks")
    if not os.path.exists(health_checks_folder):
        os.makedirs(health_checks_folder)

    while True:
        LUXOS_MINERS.clear()
        buffer.clear()
        logging.info("Starting HealthCheck...")
        start_time = time.time()

        start_time_healthcheck = time.time()
        if args.report_output_type == 'csv':
            try:
                with open(INTERMEDIATE_CSV, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(COLUMN_NAMES)
                tasks = [
                    healthcheck(ip, handle_csv_row, buffer, lock, args, sem)
                    for ip in ip_list
                ]
                for task in async_tqdm.as_completed(tasks,
                                                    desc="Processing IPs",
                                                    total=len(tasks)):
                    await task
                if buffer:
                    with open(INTERMEDIATE_CSV, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(buffer)
                final_output_name = generate_filename(args.csv_output)
                shutil.copy(INTERMEDIATE_CSV, args.local_grafana_file)
                os.rename(INTERMEDIATE_CSV, final_output_name)

            finally:
                if os.path.exists(INTERMEDIATE_CSV):
                    os.remove(INTERMEDIATE_CSV)
        else:
            pool = await create_connection_pool(db_config)
            try:
                tasks = [
                    healthcheck(ip, handle_db_row, buffer, lock, args, sem,
                                pool) for ip in ip_list
                ]
                for task in async_tqdm.as_completed(tasks,
                                                    desc="Processing IPs",
                                                    total=len(tasks)):
                    await task
                if buffer:
                    await insert_to_db(pool, buffer, args.db_table_name)
            finally:
                await pool.close()

        end_time_healthcheck = time.time()
        execution_time_healthcheck = end_time_healthcheck - start_time_healthcheck
        logging.info("Finished performing HealthCheck on all hosts.")
        logging.info(
            f"Execution time for Health Check: {execution_time_healthcheck:.2f} seconds."
        )

        if args.executeconfigs == 'True':
            logging.info("Starting config settings...")
            start_time_config = time.time()
            tasks = [execute_configs(ip, args) for ip in LUXOS_MINERS]
            for task in async_tqdm.as_completed(tasks,
                                                desc="Executing configs",
                                                total=len(tasks)):
                await task
            end_time_config = time.time()
            execution_time_config = end_time_config - start_time_config
            logging.info(
                f"Execution time for configs: {execution_time_config:.2f} seconds."
            )

        end_time = time.time()
        execution_time = end_time - start_time

        logging.info(f"Total execution time: {execution_time:.2f} seconds.")

        await asyncio.sleep(args.sleep_between_executions)


def print_message_on_timer():
    while True:
        print(" ########## PRESS ENTER TO STOP ##########")
        time.sleep(20)


def stop_on_input(loop):
    message_thread = threading.Thread(target=print_message_on_timer,
                                      daemon=True)
    message_thread.start()
    input()
    print("Cancelling...")
    for task in asyncio.all_tasks(loop):
        task.cancel()
    message_thread.join()


async def run():
    try:
        args = parse_args()
        logging.basicConfig(**LOGGING_CONFIG)

        db_config = {
            'user': args.db_user,
            'password': args.db_password,
            'database': args.db_database,
            'host': args.db_host,
            'port': args.db_port
        }

        lock = asyncio.Lock()
        sem = asyncio.Semaphore(args.max_threads)
        buffer = []

        if args.range_start and args.range_end:
            ip_list = generate_ip_range(args.range_start, args.range_end)
        elif args.ipfile:
            ip_list = load_ip_list_from_csv(args.ipfile)
        else:
            logging.info("No IP address or IP list found.")
            exit(1)

        loop = asyncio.get_event_loop()
        threading.Thread(target=stop_on_input, args=(loop, ),
                         daemon=True).start()

        await main_loop(ip_list, args, lock, sem, buffer, db_config)
    except asyncio.CancelledError:
        logging.info("Interrupted by user. Exiting...")
        return


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()