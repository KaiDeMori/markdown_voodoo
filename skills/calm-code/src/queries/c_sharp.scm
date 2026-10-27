(class_declaration
  name: (identifier) @name) @definition.class

(struct_declaration
  name: (identifier) @name) @definition.struct

(interface_declaration
  name: (identifier) @name) @definition.interface

(record_declaration
  name: (identifier) @name) @definition.record

(constructor_declaration
  name: (identifier) @name
  parameters: (parameter_list) @parameters) @definition.constructor

(method_declaration
  name: (identifier) @name
  parameters: (parameter_list) @parameters) @definition.method

(property_declaration
  name: (identifier) @name
  accessors: (accessor_list
    (accessor_declaration body: (_)))) @definition.property

(property_declaration
  name: (identifier) @name
  value: (arrow_expression_clause)) @definition.property
