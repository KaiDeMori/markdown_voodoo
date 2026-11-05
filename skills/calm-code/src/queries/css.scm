(rule_set
  (selectors
    (_)+ @other_name) @name @label) @definition.rule

(media_statement
  "@media" @name
  (block) @body) @definition.at_rule

(supports_statement
  "@supports" @name
  (block) @body) @definition.at_rule

(scope_statement
  "@scope" @name
  (block) @body) @definition.at_rule

(keyframes_statement
  ["@keyframes" (at_keyword)] @name
  (keyframes_name) @other_name
  (keyframe_block_list) @body) @definition.at_rule

(at_rule
  (at_keyword) @name
  (block) @body) @definition.at_rule

(at_rule
  (at_keyword) @name
  ";") @definition.at_rule @label

(import_statement
  "@import" @name) @definition.at_rule @label

(charset_statement
  "@charset" @name) @definition.at_rule @label

(namespace_statement
  "@namespace" @name) @definition.at_rule @label
