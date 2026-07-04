"""Cross-app events emitted by the matching pipeline.

`match_job_completed` fires after a job reaches DONE (kwargs: job).
Consumers (e.g. watchlist alerting) attach in their AppConfig.ready().
"""

import django.dispatch

match_job_completed = django.dispatch.Signal()
