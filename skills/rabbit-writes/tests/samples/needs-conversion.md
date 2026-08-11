# Quarterly infrastructure review

## Background and context

The infrastructure team spent the past quarter working through a backlog of items that had accumulated over the previous two quarters. There were a number of competing priorities that made sequencing difficult at several points in the period. The team was nonetheless able to work through most of what had been planned at the start of the quarter. Furthermore, several unplanned items arrived mid-quarter and required attention that consumed capacity allocated elsewhere. Those items were mostly small but they were not free in terms of the calendar. The net effect of all of this activity is that the migration is now complete. The legacy cluster was decommissioned on 3/14/2026, which unblocks the platform work scheduled for the coming quarter.

## Findings from the migration work

The migration itself proceeded in three separate phases spread across the quarter. Each phase had its own set of dependencies on teams outside the infrastructure group entirely. The sequencing of those phases was determined largely by the availability of those teams rather than by any technical constraint on our side. Furthermore, the second phase encountered an unexpected issue with connection pooling under sustained load. That issue required a rollback and a second attempt the following week. The rollback itself went cleanly and no customer traffic was affected at any point during the maintenance window. Latency at the ninety-ninth percentile improved by roughly forty percent once the migration completed, which is the headline result of the entire quarter.

## Cost implications and analysis

The cost picture is more complicated than the latency picture and requires unpacking before any conclusion becomes clear. There are one-time costs associated with running two clusters in parallel throughout the transition period. There are also ongoing savings from the substantially smaller footprint of the replacement cluster. These two effects point in opposite directions over different time horizons, which makes a single number misleading. Furthermore, the reserved instance commitments in place for the legacy cluster do not expire until the end of the following quarter. That means the savings do not begin to appear in the reported numbers until then. Taken together, the monthly run rate falls by about eighteen thousand dollars once those commitments roll off.

## Risks that remain open

Several risks remain open at the close of the quarter and should be tracked into the next one. None of them is severe enough on its own to warrant delaying the platform work already scheduled. Each of them could nonetheless consume meaningful capacity if it materializes at an inconvenient moment. The backup restore path has not yet been exercised end to end on the new cluster. The runbook for the failover procedure still references the old hostnames throughout its steps. Two of the four on-call engineers have not yet been trained on the new topology. That last one is the item worth acting on first, and it is cheap to close.

## Recommendations for the coming quarter

The recommendation is to schedule the on-call training in the first two weeks of the quarter. The restore drill should follow immediately afterward while the training is still fresh. The runbook update is small enough to fold into either of those two pieces of work. Beyond that, the platform work can proceed on the schedule that was agreed at the planning session. There is no technical reason to delay it any further at this point. The team has capacity to absorb the training and the drill without moving that date. The one dependency worth naming is the security review of the new topology. That review is scheduled and the reviewer has confirmed the date in writing. Nothing else in the plan depends on work owned outside the team.

## Reporting and follow-up

The reporting cadence for the coming quarter has not yet been settled with the platform group. The current weekly update is longer than anyone reads and shorter than anyone needs for planning purposes. Furthermore, the metrics that appear in it were chosen for the migration and no longer describe the work that is actually underway. The proposal is to replace it with a fortnightly summary that leads with the two numbers the platform group asks about every time. Those two numbers are the ninety-ninth percentile latency and the monthly run rate against the committed budget. Everything else can move to a dashboard that anyone can open when they want the detail.

Best regards,
The infrastructure team
