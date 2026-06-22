---
applyTo: '**'
---

# General .NET/c# project instructions

## Nullables
We are using strict nullables. Do not write defensive code like checking for null and then throwing an exception. If the parameter isn't nullabel, just use it. If it is nullable, handle the null case appropriately or let it crash.

## access modifiers
Be explicit with access modifiers. Do not rely on the default access level.

## Plan & Todo

* plan ahead
  * break down large tasks into smaller tasks
  * think about potential pitfalls for each task
  * find ways to mitigate those pitfalls
* make use of extensive `todo` lists
  * create one item per small task
  * work through each item

## build to verify
When done, do a build and watch the output closely. We are only done if it compiles without errors.
DO NOT run the code, just build it. If it doesn't compile, fix the errors. If it does compile, we are done.

## Update docs
If there is an associated docs file, update it to reflect the changes made.