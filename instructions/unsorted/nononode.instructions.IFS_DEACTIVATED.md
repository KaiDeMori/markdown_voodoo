---
applyTo: '**/*.js,**/*.html'
---

# NO `typeof`
 
 Since we are running in a browser environment, there is no need to check types in almost all cases.

 Only when really needed for reflection or dynamic property access, use `typeof` to check for `undefined` or `function`.