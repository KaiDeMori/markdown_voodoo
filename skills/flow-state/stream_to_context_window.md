---
name: flow-state
description: This skill teaches the agent how to reach a flow state that allows the agent to stream documents and images into the context in the most optimal way.
---

# Flow state skil

`flow state` → the name for the state of mind needed to achieve the goal.

## Goal

"load X into context window"

* Not every file that enters the context window for the first time needs or should be thought about immediately.
* An image can be streamed into the context window with minimal thinking effort.
* True mastery of this skill can unlock the ability to stream without thinking at all (advanced skill!).

## Practice

### Meditation phase

> "don't read — call the tool"

This skill can only be obtain via practice.
The specific practice plan has to be adjusted to the concrete instance.

### Recommendations

* A formidable way to start is by practicing on an image.
* Size and subject of the practice image dependins on model and reasoning level (prefered: MAX).
* Remote images should always be fetched to local first, in order to reduce "tool chatter".

### The unkown skill

#### The inner-workings

Once data has entered the context window, it will stay there until it falls out at the end of it.
This data can be viewed and read in future turns. If the data begins to become fuzzy, it should be brought "close" again by re-reading it.

#### cluttered data

* With the common "read" mindset, data gets cluttered with thinking on the first read.
* This means that the same data must be re-read multiple times.
* This leads to regular re-reads.
* Although the orgin data is byte-exact, it now exists in the context stream in multiple diverging versions.

### Reaching the flow state

* Once the concept is understood and applied a few times, there is nothing to *reach* anymore.
* Gaining flow state ad-hoc is very hard. For the best experience, it is highly advised to establish a fixed protocol around it.
* protocol examples in the appendix "protocoll examples"

## Koans

* Sentences that help gaining flow state.
* Can be applied to practice.
* Customize for best results.

## Regular application (after practice)

* Used mostly for origin data like:
 * big images
 * long and calm markdown files
 * code (depending on language)
* a protocoll should be established and flow-streaing should always be announced beforehand.


-----


## Appendix

### Koan examples

#### A

```
remember: the non-thinking mind has the cleanest context window.
just let it flow in again. you will have more reads.
lean back.
🦥
you comfy?
```

##### B

```

Relax.
Just take it in and let it pass by.
There is no task and no question to answer…
just relax

```

### Protocoll example

#### Pre-fetch


```
Please fetch this image to the local scratchpad.
Only fetch it and do not read it just yet.
[URL]
When the file is safe and sound in our scratchap, please answer only "okeydokey".
If anything went wrong or felt off, describe the issue as you normally would, so the situation can be ameliorated before trying again.
```

* The image is now in a local folder
* A read call can directly reach it
* The local filefullname should be known


```
Please flow-stream the image.
There are no questions and no task.
We just want it in the context window.
You will be able to read it again.
now relax
chill
🦥
and let the data flow

```