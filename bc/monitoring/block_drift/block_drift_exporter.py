#!/usr/bin/env python3

import argparse
from random import betavariate

import requests
import logging
import json
from flask import Flask, Response
from typing import Optional


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="## %(asctime)s [%(levelname)s] %(message)s"
)

# --- Default settings per chain ---
CHAIN_CONFIGS = {
    "sol": {
        "local": "http://127.0.0.1:8899",
        "remote": "https://api.mainnet-beta.solana.com",
        "is_hex": False,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "getBlockHeight"},
    },
    "eth": {
        "local": "http://127.0.0.1:8545",
        "remote": "https://ethereum.llamarpc.com",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "bsc": {
        "local": "http://127.0.0.1:8545",
        "remote": "https://bsc-dataseed1.binance.org/",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "base": {
        "local": "http://127.0.0.1:8545",
        "remote": "https://mainnet.base.org",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "story": {
        "local": "http://127.0.0.1:8545",
        "remote": "https://mainnet.storyrpc.io",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "pulse": {
        "local": "http://127.0.0.1:8545",
        "remote": "https://pulsechain-rpc.publicnode.com",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "bera": {
        "local": "http://127.0.0.1:8545",
        "remote": "https://berachain-rpc.publicnode.com",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "sonic": {
        "local": "http://127.0.0.1:18545",
        "remote": "https://rpc.soniclabs.com",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    },
    "avalanchego": {
        "local": "http://127.0.0.1:8545/ext/bc/C/rpc",
        "remote": "https://avalanche.therpc.io",
        "is_hex": True,
        "jsonrpc_body": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
    }
}


def fetch_block_height(url: str, body: dict, is_hex: bool) -> Optional[int]:
    try:
        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=3)
        result = resp.json().get("result")
        if result is None:
            return None
        return int(result, 16) if is_hex else int(result)
    except Exception as e:
        logging.error(f"Failed to fetch block height from {url}: {e}")
        return None


def calculate_metrics(chain: str, local_url: str, remote_url: str, body: dict, is_hex: bool) -> str:
    remote_block = fetch_block_height(remote_url, body, is_hex)
    local_block = fetch_block_height(local_url, body, is_hex)

    if remote_block is None or local_block is None:
        return f"# Error: could not retrieve block height for chain '{chain}'\n"

    drift = remote_block - local_block
    return (
        f"chain_block_height_local{{chain=\"{chain}\"}} {local_block}\n"
        f"chain_block_height_remote{{chain=\"{chain}\"}} {remote_block}\n"
        f"chain_block_height_drift{{chain=\"{chain}\"}} {drift}\n"
    )


@app.route("/metrics")
def metrics():
    output = calculate_metrics(
        args.chain,
        config["local"],
        config["remote"],
        config["jsonrpc_body"],
        config["is_hex"]
    )
    logging.info(f"Exported metrics for {args.chain}:\n" + output.strip())
    return Response(output + "\n", mimetype="text/plain")

def dump_config(chain):
    logging.info("Effective config: " + json.dumps(CHAIN_CONFIGS[chain], separators=(",", ":"), sort_keys=True))

def main():
    parser = argparse.ArgumentParser(description="Generic block drift Prometheus exporter")
    #parser.add_argument("--chain", required=True, choices=CHAIN_CONFIGS.keys(), help="Blockchain to monitor")
    parser.add_argument("chain", choices=CHAIN_CONFIGS.keys(), help="Blockchain to monitor")
    parser.add_argument("--serve", action="store_true", help="Start HTTP server")
    parser.add_argument("--port", type=int, default=9100, help="HTTP server port")
    parser.add_argument("--remote", type=str, help="Remote chain address")
    parser.add_argument("--local", type=str, help="Local chain address")

    global args
    args = parser.parse_args()

    global config
    config = CHAIN_CONFIGS[args.chain]
    if args.remote:
        config["remote"] = args.remote
    if args.local:
        config["local"] = args.local

    dump_config(args.chain)

    if args.serve:
        logging.info(f"Starting HTTP server for {args.chain} on :{args.port}")
        app.run(host="0.0.0.0", port=args.port)
    else:
        output = calculate_metrics(
            args.chain,
            config["local"],
            config["remote"],
            config["jsonrpc_body"],
            config["is_hex"]
        )
        logging.info(f"Exported metrics for {args.chain}:\n" + output.strip())


if __name__ == "__main__":
    main()

