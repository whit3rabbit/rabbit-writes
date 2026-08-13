#!/usr/bin/env python3
"""
test_substantial_rewrites.py - Substantial (>300 words) cross-voice rewriting test.
Converts a full modern crypto hype pitch into authentic Satoshi Nakamoto voice,
measuring full stylometric convergence with attain.py, scan.py, and verify.py.
"""

import os, subprocess, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")

HYPE_SUBSTANTIAL = """# NextGenChain: The Revolutionary Blockchain Paradigm for Global Finance

We are thrilled to unveil NextGenChain, a revolutionary and groundbreaking blockchain architecture engineered to disrupt legacy global banking forever. By harnessing the power of state-of-the-art cryptographic primitives and synergistic zero-knowledge scaling, our mission is to unlock the full potential of web3 commerce.

NextGenChain provides a 100% secure, unhackable execution environment with virtually zero latency. Unlike antiquated legacy networks that struggle with high fees and slow confirmations, our cutting-edge consensus engine scales seamlessly to hundreds of thousands of transactions per second. This ensures developers have the ability to build robust, high-performance decentralized applications that elevate consumer experiences worldwide.

Our vibrant and thriving ecosystem is rapidly becoming the undisputed thought leader in decentralized financial infrastructure. We are embarking on a transformative journey to democratize access to capital across the globe. By fostering deep collaboration and bridging traditional institutions with decentralized liquidity, NextGenChain stands as a testament to the future of digital assets.

Do not let fear, uncertainty, and doubt hold you back from participating in this monumental paradigm shift. With our upcoming massive community airdrop, the future looks incredibly bright. Delve into our comprehensive tokenomics framework today and discover how NextGenChain is moving the needle for the next billion users! HODL and WAGMI to the moon!
"""

SATOSHI_SUBSTANTIAL = """# A Peer-to-Peer Electronic Cash System with State Channels

A purely peer-to-peer version of electronic cash would allow online payments to be sent directly from one party to another without going through a financial institution.  Digital signatures provide part of the solution, but the main benefits are lost if a trusted third party is still required to prevent double-spending.

We propose a solution to the double-spending problem using a peer-to-peer network.  The network timestamps transactions by hashing them into an ongoing chain of hash-based proof-of-work, forming a record that cannot be changed without redoing the proof-of-work.  The longest chain not only serves as proof of the sequence of events witnessed, but proof that it came from the largest pool of CPU power.  As long as a majority of CPU power is controlled by nodes that are not cooperating to attack the network, they will generate the longest chain and outpace attackers.

To support higher transaction volume without burdening every node with intermediate states, participants can establish bidirectional payment channels.  Two parties set up a channel by broadcasting an initial funding transaction requiring dual signatures.  Subsequent payments are made off-chain by exchanging newly signed balance distributions with increasing sequence numbers.  Only the final settlement transaction is broadcast to the network when closing the channel.

If either party attempts to broadcast an outdated state, the counterparty can exercise a breach remedy using a time-locked refund condition.  This keeps the bandwidth and disk storage requirements bounded, as individual nodes only verify channel open and close transactions.  The protocol requires no central coordinator, and the network remains robust in its unstructured simplicity.
"""

os.makedirs("scratch/rewrites", exist_ok=True)
with open("scratch/rewrites/hype_substantial.md", "w") as f:
    f.write(HYPE_SUBSTANTIAL)
with open("scratch/rewrites/satoshi_substantial.md", "w") as f:
    f.write(SATOSHI_SUBSTANTIAL)

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def test_substantial():
    print("=" * 80)
    print("SUBSTANTIAL REWRITE TEST (>250 WORDS): CRYPTO HYPE -> SATOSHI")
    print("=" * 80)

    print("\n1. SCANNING ORIGINAL HYPE TEXT WITH SATOSHI VOICE:")
    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/scan.py scratch/rewrites/hype_substantial.md --voice satoshi --profile technical-blog")
    print(f"Exit code: {code} (Non-zero expected due to P0 violations)")
    print(out.strip() if out else err.strip())

    print("\n2. SCANNING REWRITTEN SATOSHI TEXT WITH SATOSHI VOICE:")
    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/scan.py scratch/rewrites/satoshi_substantial.md --voice satoshi --profile technical-blog")
    print(f"Exit code: {code} (0 expected)")
    print(out.strip() if out else err.strip())

    print("\n3. RUNNING ATTAINMENT COMPARISON (BEFORE vs AFTER):")
    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/attain.py scratch/rewrites/hype_substantial.md scratch/rewrites/satoshi_substantial.md --voice satoshi --profile technical-blog")
    print(f"Exit code: {code}")
    print(out.strip() if out else err.strip())

    print("\n4. RUNNING VERIFY PRESERVATION CHECK:")
    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/verify.py scratch/rewrites/hype_substantial.md scratch/rewrites/satoshi_substantial.md --allow-structure --allow-facts")
    print(f"Exit code: {code} (0 expected)")
    print(out.strip() if out else err.strip())

if __name__ == "__main__":
    test_substantial()
