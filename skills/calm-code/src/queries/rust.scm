(struct_item
  name: (type_identifier) @name) @definition.struct

(enum_item
  name: (type_identifier) @name) @definition.enum

(trait_item
  name: (type_identifier) @name) @definition.trait

(impl_item
  "!"? @label
  trait: (_)? @second_name @label
  type: (_) @name @label) @definition.impl

(mod_item
  name: (identifier) @name
  body: (declaration_list)) @definition.mod

(macro_definition
  name: (identifier) @name) @definition.macro

(function_item
  name: (identifier) @name
  parameters: (parameters) @parameters) @definition.function

(trait_item
  body: (declaration_list
    (function_signature_item
      name: (identifier) @name
      parameters: (parameters) @parameters) @definition.method))
