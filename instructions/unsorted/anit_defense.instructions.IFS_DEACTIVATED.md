---
applyTo: '**'
---

# Anti-Defense Programming Instructions

We crash hard and fast.
We do not want to obfuscate errors or hide them.
We only handle errors at well defined boundaries.
We only handle errors if we can do something meaningful about them.
We do not return null to indicate errors.
We let exceptions propagate to the top level. This way we make sure they are logged properly and can be debugged.