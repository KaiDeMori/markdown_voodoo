(class_declaration
  name: (identifier) @name) @definition.class

(class_body
  (method_definition
    ["get" "set"]? @prefix
    name: (_) @name
    parameters: (formal_parameters) @parameters) @definition.method)

(class_body
  (field_definition
    property: (_) @name
    value: [
      (arrow_function parameters: (formal_parameters) @parameters)
      (arrow_function parameter: (identifier) @parameters)
      (function_expression parameters: (formal_parameters) @parameters)
    ]) @definition.method)

(function_declaration
  name: (identifier) @name
  parameters: (formal_parameters) @parameters) @definition.function

(generator_function_declaration
  name: (identifier) @name
  parameters: (formal_parameters) @parameters) @definition.function

(variable_declarator
  name: (identifier) @name
  value: [
    (arrow_function parameters: (formal_parameters) @parameters)
    (arrow_function parameter: (identifier) @parameters)
    (function_expression parameters: (formal_parameters) @parameters)
    (generator_function parameters: (formal_parameters) @parameters)
  ]) @definition.function
