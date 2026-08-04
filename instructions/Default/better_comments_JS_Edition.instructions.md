---
applyTo: "**"
---

** WRITE ONLY COMMENTS THAT FOLLOW THESE RULES **

# JavaScript
Since javascript is un-typed, we have to rely on good comments!
It is NOT obvious in JavaScript what a function returns and what the parameters shape is, so all parameters and return types have to be clearly commented.

# Documentation Comments

Always use proper XML documentation comments for functions, classes, methods, and modules. Avoid inline comments unless absolutely necessary.

## Use @typedef for complex objects

We generally want @typedef for objects.
In most projects, there will be a central file or multiple files containing all the @typedefs for the project, and we can refer to those typedefs in our documentation comments.

## No redundant comments

In most cases, the function name already explains what the function does and we can focus on the parameters and return values.

GOOD:
```javascript
/**
 * @param {number} angle - Rotation angle in degrees.
 */
function rotate_image(angle) {
}
```

BAD:

```javascript
/**
 * Rotate the image by a given angle.
 * @param {number} angle - Rotation angle in degrees.
 */
function rotate_image(angle) {
}
```

*The first comment is sufficient, the second one is redundant and adds no value, just cluttering the code.*