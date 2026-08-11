# Quarterly infrastructure review

The migration is done and the legacy cluster is off. That unblocks the platform work for next quarter.

Three things are still open, and one of them is worth doing first.

## What happened

Three phases, spread across the quarter. Sequencing came from other teams' availability, not from anything technical on our side.

Phase two hit connection pooling under load, which we did not catch in staging because the staging pool is a tenth of the size and never reaches the contention point. We rolled back and went again the following week. The rollback was clean. No customer traffic was affected.

Latency at p99 improved about 40%. That is the headline, and it is the number to check against next quarter's dashboard rather than take on faith here.

## Cost

The run rate falls by about $18,000 a month, but not yet.

Two effects pull against each other. Running both clusters in parallel cost money during the transition. The smaller footprint saves money from here on.

The reserved instance commitments on the old cluster do not expire until the end of next quarter. Until they roll off, the savings will not show up in the reported numbers.

## What is still open

- The backup restore path has not been exercised end to end on the new cluster.
- The failover runbook still references the old hostnames.
- Two of the four on-call engineers have not been trained on the new topology.

The training is the one to do first. It is the cheapest to close and the most expensive to skip.

## Plan

1. On-call training, first two weeks.
2. Restore drill straight after, while the training is fresh.
3. Runbook update folded into either.

The platform work can start on the agreed date. The security review of the new topology is scheduled and the reviewer confirmed in writing. Nothing else in the plan waits on anyone outside the team.

Thanks,
-whit3rabbit
