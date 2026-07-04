"""Cross-app events for application lifecycle changes.

`application_status_changed` fires after every successful transition
(kwargs: application, old_status, new_status). Consumers (notifications)
attach in their AppConfig.ready().
"""

import django.dispatch

application_status_changed = django.dispatch.Signal()
