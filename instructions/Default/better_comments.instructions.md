---
applyTo: "**"
---

** DO NOT WRITE COMMENTS UNLESS THEY FOLLOW THESE RULES **

# Instructions for Better Comments

- Keep the comments timeless and general.
- Use comments to explain the "why" and "how" of the code, **not** the "what".
- We prefer longer names over comments.

# Documentation Comments

Always use proper XML documentation comments for functions, classes, methods, and modules. Avoid inline comments unless absolutely necessary.

## No actual values in the comments, except they are necessary for understanding the code.

GOOD:
// This variable defines the rotation angle in radians.

BAD: 
// Math.PI / 2 (90 degrees) is used to rotate the image by 90 degrees clockwise (in radians).

## No specific dates or version numbers in comments.

GOOD:
// This function processes the image data.

BAD:
// This function processes the image data as of version 1.2.3.

## No specific names in comments, except they are necessary for understanding the code.

GOOD:
// This function processes the image data.

BAD:
// This function processes the image data for the Imaginer project.

## No redundant comments

GOOD:

```csharp
void rotate_image(Image image, float angle) {
   […]
}
```
*(no comment needed, the function name is self-explanatory)*

BAD:

```csharp
// This function rotates an image by a specified angle.
void rotate_image(Image image, float angle) {
   […]
}
```

# No history keeping!
Do **NOT** reference previous attempts, old ideas or other "historic references" in code comments.

## No useless XML comments

GOOD:

```
private static string build_incoming_message_label(Received_message received_message)…
```
*(no XML comment needed, the method name is self-explanatory)*

BAD:

```
   /// <summary>
   /// Builds the log label for an incoming message.
   /// </summary>
   private static string build_incoming_message_label(Received_message received_message)…
```
*useless XML comment that just restates the method name, cluttering the code, without adding any additional information*

