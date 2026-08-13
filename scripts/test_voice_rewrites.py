#!/usr/bin/env python3
"""
test_voice_rewrites.py - Tests bidirectional voice conversion and validation:
1. Inbound: Converting modern crypto hype into Satoshi's voice.
2. Outbound: Converting Satoshi's prose into whit3rabbit's voice.
Checks with verify.py, attain.py, and scan.py.
"""

import os, subprocess, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "rabbit-writes", "scripts")

# 1. Inbound Case: Modern Crypto Hype -> Satoshi Nakamoto
HYPE_BEFORE = """# The Next Generation Blockchain Scaling Solution

We are excited to announce our revolutionary new blockchain architecture.  By harnessing the power of cutting-edge zero-knowledge state channels, our project is poised to disrupt legacy financial systems forever.

This groundbreaking technology delivers 100% secure, unhackable transactions with zero latency.  We have unlocked unprecedented throughput so developers can seamlessly build decentralized applications.  Our thriving ecosystem is spearheading the future of web3 finance.

Don't let FUD hold you back from this transformative journey.  Join our community today for our massive upcoming airdrop!
"""

SATOSHI_REWRITE = """# A State-Channel Scaling Architecture

We propose an off-chain transaction design using dual-signed state channels to reduce network traffic on the base chain.  Transactions are exchanged directly between participants and only broadcast to the network when opening or closing a channel.

The security relies on time-locked refund transactions; as long as either party broadcasts the latest signed state before the timeout expires, funds cannot be stolen by an uncooperative peer.  This reduces disk storage and bandwidth requirements for nodes that do not need to process every intermediate exchange.

The implementation details and prototype code are available for testing.
"""

# 2. Outbound Case: Satoshi's Whitepaper / Forum -> whit3rabbit Voice
SATOSHI_BEFORE = """# Reclaiming Disk Space

Once the latest transaction in a coin is buried under enough blocks, the spent transactions before it can be discarded to save disk space.  To facilitate this without breaking the block's hash, transactions are hashed in a Merkle Tree, with only the root included in the block's hash.  Old blocks can then be compacted by stubbing off branches of the tree.  The interior hashes do not need to be stored.

A block header with no transactions would be about 80 bytes.  If we suppose blocks are generated every 10 minutes, 80 bytes * 6 * 24 * 365 = 4.2MB per year.  With computer systems typically selling with 2GB of RAM as of 2008, and Moore's Law predicting current growth of 1.2GB per year, storage will not be a problem even if the block headers must be kept in memory.
"""

WHIT3RABBIT_REWRITE = """# Reclaiming Disk Space

Bottom line: old transactions can be safely pruned from disk without breaking block verification.

Here is how the pruning mechanism works:
- Transactions are hashed into a Merkle tree.
- Only the root hash is stored in the block header.
- Spent transaction branches are stubbed out once they are buried under enough blocks.
- Interior hashes are discarded, leaving the header intact.

Storage growth is negligible:
- Header size: ~80 bytes.
- Annual rate: 80 bytes * 6 blocks/hour * 24 hours * 365 days = 4.2 MB per year.
- Hardware baseline: Standard computers sell with 2 GB RAM (2008 baseline), growing by ~1.2 GB per year under Moore's Law.

Keeping all block headers in memory will not be a bottleneck for years.
"""

os.makedirs("scratch/rewrites", exist_ok=True)

with open("scratch/rewrites/hype_before.md", "w") as f:
    f.write(HYPE_BEFORE)
with open("scratch/rewrites/satoshi_rewrite.md", "w") as f:
    f.write(SATOSHI_REWRITE)

with open("scratch/rewrites/satoshi_before.md", "w") as f:
    f.write(SATOSHI_BEFORE)
with open("scratch/rewrites/whit3rabbit_rewrite.md", "w") as f:
    f.write(WHIT3RABBIT_REWRITE)

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def test_rewrites():
    print("=" * 80)
    print("TESTING CROSS-VOICE REWRITING AND ATTAINMENT")
    print("=" * 80)

    # Test 1: Inbound to Satoshi
    print("\n--- TEST 1: INBOUND (Crypto Hype -> Satoshi) ---")
    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/verify.py scratch/rewrites/hype_before.md scratch/rewrites/satoshi_rewrite.md --allow-structure --allow-facts")
    print(f"verify.py exit: {code} (0 = clean)")
    if out: print(out.strip())

    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/scan.py scratch/rewrites/satoshi_rewrite.md --voice satoshi --profile technical-blog")
    print(f"\nscan.py --voice satoshi exit: {code} (0 = clean)")
    if out: print(out.strip())

    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/attain.py scratch/rewrites/hype_before.md scratch/rewrites/satoshi_rewrite.md --voice satoshi")
    print(f"\nattain.py exit: {code}")
    if out: print(out.strip())

    # Test 2: Outbound to whit3rabbit
    print("\n--- TEST 2: OUTBOUND (Satoshi -> whit3rabbit) ---")
    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/verify.py scratch/rewrites/satoshi_before.md scratch/rewrites/whit3rabbit_rewrite.md --allow-structure --allow-facts")
    print(f"verify.py exit: {code} (0 = clean)")
    if out: print(out.strip())

    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/scan.py scratch/rewrites/whit3rabbit_rewrite.md --voice whit3rabbit --profile technical-blog")
    print(f"\nscan.py --voice whit3rabbit exit: {code} (0 = clean)")
    if out: print(out.strip())

    code, out, err = run_cmd(f"python3 {SCRIPTS_DIR}/attain.py scratch/rewrites/satoshi_before.md scratch/rewrites/whit3rabbit_rewrite.md --voice whit3rabbit")
    print(f"\nattain.py exit: {code}")
    if out: print(out.strip())

if __name__ == "__main__":
    test_rewrites()
