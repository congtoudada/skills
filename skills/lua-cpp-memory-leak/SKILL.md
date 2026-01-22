---
name: lua-cpp-memory-leak
description: Analyze Lua-C++ memory leaks by examining reference chains where Lua objects fail to call Release functions, preventing C++ instances from being properly deallocated. Use this skill when users provide reference chains showing unreleased Lua objects that hold C++ instance references, requiring analysis of Lua code to identify why Release was not called and provide fixing recommendations.
---

# Lua-C++ Memory Leak Analysis

## Overview

This skill analyzes memory leaks in Lua-C++ interop scenarios where Lua objects fail to call Release functions on C++ instances. The analysis traces reference chains to identify which Lua objects are preventing C++ memory deallocation and provides root cause analysis with actionable fix recommendations.

**Important**: This skill is designed to work with **any** Lua class names, field names, and project structures. Examples in this documentation use placeholder names for illustration. Apply the same analysis patterns to whatever names appear in the actual reference chains.

## When to Use This Skill

Use this skill when:
- User provides reference chains showing Lua objects holding C++ instance references
- Reference chains indicate which objects called Release (marked `[true]`) and which did not (marked `[false]`)
- Analysis requires examining Lua source code to understand why Release was not invoked
- Need to provide specific code locations and fix recommendations for memory leak issues

## Reference Chain Format

Reference chains follow this pattern:
```
ClassName:MemoryAddress[ReleaseStatus].fieldName.ClassName:MemoryAddress[ReleaseStatus].fieldName...__cppinst = BlueprintClassName
```

**CRITICAL Understanding**:
- **Only Lua objects** have `[true]` or `[false]` markers indicating Release status
- **Field names** (like `_nameComp`, `_crossoverLabel`) are **NOT marked** - they are just connection indicators
- **`[true]`** means the Lua object called `Release()` on itself
- **`[false]`** means the Lua object did NOT call `Release()` on itself
- **`.__cppinst = BlueprintClassName`** - Optional suffix showing the C++ blueprint class that's leaked (UE4/UE5 widget class)

**Example with C++ Instance**:
```
ParentClass:ADDR1[true]._field.ChildClass:ADDR2[false].__cppinst = WBP_MyWidget_C
```
This indicates:
- `ChildClass` (Lua wrapper) did not call Release
- The underlying C++ blueprint `WBP_MyWidget_C` is leaked
- The blueprint class name helps identify which UE widget/actor is affected

### Example Pattern 1: Parent Released, Child Not Released

```
ParentClass:ADDR1[true]._fieldName.ChildClass:ADDR2[false].__cppinst = WBP_ChildWidget_C
```

**Generic Interpretation**:
- `ParentClass` [Released ✓] - called its own `Release()`
- `_fieldName` - field name connecting parent to child (no marker)
- `ChildClass` [NOT Released ✗] - did NOT call its own `Release()`
- `__cppinst = WBP_ChildWidget_C` - The leaked C++ blueprint class (UE widget)

**Analysis Focus**: 
Parent released itself but likely failed to call `Release()` on its child field. Check parent's cleanup method for missing `self._fieldName:Release()` call.

**Investigation Steps**:
1. Search for `ParentClass.lua` in source directory
2. Locate the cleanup/destructor method (usually `Destroy()` or `OnClose()`)
3. Check if `self._fieldName:Release()` is present
4. If missing, that's likely the leak cause
5. The blueprint class `WBP_ChildWidget_C` confirms this is a UE widget leak

### Example Pattern 2: Parent and Child Released, But Grandchild Not Released

```
GrandParent:ADDR1[true]._field1.Parent:ADDR2[true]._field2.Child:ADDR3[false].__cppinst = WBP_LeakedWidget_C
```

**Generic Interpretation**:
- `GrandParent` [Released ✓]
- `Parent` [Released ✓] - called its own `Release()`
- `Child` [NOT Released ✗]
- `__cppinst = WBP_LeakedWidget_C` - The leaked C++ blueprint class

**Analysis Focus**: 
Although `Parent` called `Release()` on itself, it likely **forgot to call `Release()` on its `_field2` field** (which holds `Child`). 

**Key Point**: An object calling `Release()` on itself doesn't automatically release its children. Must check if the object's Release/Cleanup method properly releases all child fields.

**Investigation Steps**:
1. Search for `Parent.lua` (the last released object before the leak)
2. Examine its Release/Cleanup method (usually `Destroy()`)
3. Check if `self._field2:Release()` is called
4. Also review `Child.lua` for any special lifecycle requirements or context
5. The blueprint `WBP_LeakedWidget_C` indicates the actual UE widget that's stuck in memory

**Remember**: Class names, field names, and memory addresses will vary. Focus on the **pattern** (which objects are `[true]` vs `[false]`) rather than specific names.

## Analysis Workflow

### Step 0: Determine Source Code Location

**Path Resolution Priority** (use the first available):

1. **Current workspace**: If CodeBuddy is opened in a Lua project, use the workspace root
2. **User-specified path**: If user explicitly provides a path in their request
3. **Default path**: `D:\congtoulin_Ma1_code_Microcosm\DFMSource\LuaSource\DFM`

**Best Practice**: Recommend the user open their Lua source code project in CodeBuddy for optimal analysis experience.

**Examples**:
- "Please analyze this reference chain" (in Lua project workspace) → Use workspace root
- "Analyze this chain, Lua code is at: E:\MyProject\Lua" → Use E:\MyProject\Lua
- "Analyze this chain" (not in Lua workspace, no path specified) → Use default path

**Framework Reference**: If the project is based on **YxFramework**, refer to `references/framework_patterns.md` for common Release patterns and anti-patterns. This reference document contains:
- Standard object lifecycle patterns
- Common places where Release is called (UI lifecycle, timers, managers)
- Typical scenarios where Release is forgotten
- Parent-child object release relationships
- Code review checklist and anti-patterns

Use this framework knowledge to:
1. Quickly identify if the leaked object follows standard framework patterns
2. Check common anti-patterns (e.g., child UI not released in parent Destroy, global event listeners not removed)
3. Provide more targeted fix recommendations based on framework conventions

### Step 1: Parse Reference Chain

For each provided reference chain:

1. **Extract components**: 
   - Split by `.` to get each segment
   - Check for `.__cppinst = BlueprintClassName` suffix at the end
   - Remove the `__cppinst` suffix for parsing, but **keep it for reporting**
   
2. **Parse segments**:
   - Lua objects: `ClassName:MemoryAddress[ReleaseStatus]`
   - Field names: Simple identifiers (no brackets, not `__cppinst`)

3. **Parse each Lua object**:
   - Class name (e.g., `IVTextQualityComponent`)
   - Memory address (e.g., `000000029E8D6300`)
   - Release status: `[true]` = released, `[false]` = not released

4. **Extract C++ instance info** (if present):
   - Blueprint class name (e.g., `WBP_SlotCompIconCrossoverLabel_C`)
   - This indicates the leaked UE widget/actor type
   - Use this to provide context about what kind of C++ object is stuck

5. **Identify leak points**: Find all Lua objects marked `[false]`

6. **Determine analysis targets**:
   - **Primary focus**: Objects marked `[false]` - they need to call Release
   - **Secondary focus**: Parent objects marked `[true]` that have `[false]` children
     - Even though parent called Release on itself, check if it released its child fields
   
7. **Build parent-child relationships**:
   - Track which field connects parent to child
   - Example: `Parent[true]._fieldName.Child[false]` means `Parent`'s `_fieldName` field holds `Child`

**Example Analysis**:
```
A:addr1[true]._field1.B:addr2[true]._field2.C:addr3[false].__cppinst = WBP_MyWidget_C
```
- Leak: `C` (not released), wrapping `WBP_MyWidget_C` blueprint
- Check: `B.lua`'s Release/Cleanup - does it call `self._field2:Release()`?
- Also check: `A.lua`'s Release/Cleanup - does it call `self._field1:Release()`?
- Context: Review `C.lua` for special lifecycle requirements
- Impact: The UE widget `WBP_MyWidget_C` is stuck in memory until `C:Release()` is called

### Step 2: Understand Release Patterns

Before analyzing specific leaks, understand how Release is typically called in the codebase:

1. **Locate Object.lua**: The base object definition where Release is declared
   - Search for `Object.lua` in the determined source path
   - Read this file to understand the Release function signature and usage

2. **Identify common Release patterns**:
   - Destructor-style cleanup (in `__gc` metamethod or explicit cleanup functions)
   - Parent-triggered cascading Release (parent releases children)
   - Event-driven Release (triggered by specific events or callbacks)
   - Conditional Release (based on ownership or lifecycle flags)

3. **Search for Release call sites** in the project:
   ```
   search_content pattern=":Release\(\)" in determined Lua source directory
   ```

### Step 3: Locate Relevant Source Files

For each unreleased object in the reference chain:

1. **Search for class definition**:
   ```
   search_file pattern="<ClassName>.lua" in determined source directory
   ```
   Replace `<ClassName>` with the actual class name from the reference chain.

2. **Search for class references** if direct file not found:
   ```
   search_content pattern="<ClassName>" in determined source directory
   ```

3. **Examine parent-child relationships**: Look for where the connecting field is assigned
   - For field `_fieldName`, search for pattern: `_fieldName\s*=`
   - This helps understand how the child object is created and assigned

**Important**: Work with whatever class names and field names appear in the user's reference chain. Don't assume specific naming conventions.

### Step 4: Analyze Release Failure

For each unreleased object (`[false]`), perform a two-level investigation:

#### Level 1: Direct Analysis - Why Didn't This Object Call Release?

1. **Check if object has Release/Cleanup method**:
   - Does the class define a `Release()`, `Cleanup()`, `Destroy()`, or similar method?
   - Is it ever called in the object's lifecycle?

2. **Look for self-release patterns**:
   ```lua
   function MyClass:Cleanup()
       self:Release()  -- Does it call Release on itself?
   end
   ```

3. **Check lifecycle hooks**:
   - `__gc` metamethod
   - Destructor-style methods
   - Event-driven cleanup

#### Level 2: Parent Analysis - Why Didn't Parent Release This Child?

**CRITICAL**: Even if parent called `Release()` on itself (`[true]`), it must also release its child fields.

1. **Locate the parent object** in the reference chain

2. **Find the connecting field**: Identify which field holds the unreleased child
   - Example: `Parent._fieldName.Child[false]` → Check `Parent`'s handling of `_fieldName`

3. **Examine parent's cleanup method**:
   ```lua
   function Parent:Cleanup()
       -- Look for this pattern
       if self._fieldName then
           self._fieldName:Release()
           self._fieldName = nil
       end
   end
   ```

4. **Common parent-side issues**:
   - **Missing child release**: Parent releases some fields but forgets this one
   - **Conditional release bug**: Child only released under certain conditions
   - **Early return**: Cleanup exits before reaching child release
   - **Wrong field name**: Releases `_oldFieldName` but field was renamed to `_newFieldName`

#### Key Investigation Pattern

For chain `A[true]._field.B[false]`:

```
1. Why didn't B call Release()?
   → Check B.lua for self-release logic
   
2. Why didn't A release B?
   → Check A.lua's Cleanup for:
      if self._field then
          self._field:Release()
      end
```

For chain `A[true]._f1.B[true]._f2.C[false]`:

```
1. Why didn't C call Release()?
   → Check C.lua
   
2. Why didn't B release C?
   → Check B.lua's Cleanup for self._f2:Release()
   
3. (Lower priority) Did A properly release B?
   → Check A.lua's Cleanup for self._f1:Release()
```

#### Context Analysis

For each leaked object, also examine:

1. **Ownership patterns**:
   - Is the child object owned by the parent?
   - Are there weak references or shared ownership scenarios?
   - Look for comments or flags indicating ownership responsibility

2. **Lifecycle mismatches**:
   - Does the child outlive the parent intentionally?
   - Are there event listeners or callbacks that keep the child alive?
   - Are there early-return paths in cleanup that skip Release?

3. **Special cases**:
   - Callback retention: Object held by callback without cleanup path
   - Circular references: Mutual references preventing cleanup
   - Pooling/caching: Object intentionally kept alive for reuse
   - Are there event listeners or callbacks that keep the child alive?
   - Are there early-return paths in cleanup that skip Release?

### Step 5: Root Cause Analysis

Categorize the leak cause based on the investigation:

#### Parent-Side Issues (Most Common)

1. **Missing child release in parent cleanup**: 
   - Parent has Cleanup method
   - Parent calls Release on itself
   - But parent forgot to call Release on this specific child field
   
2. **Incomplete cleanup method**:
   - Parent releases some children but not all
   - Recently added field not included in cleanup

3. **Conditional release bug**:
   - Child Release is conditional
   - Condition not met at cleanup time

4. **Early return in cleanup**:
   - Cleanup exits before reaching child Release
   - Guard clause or error handling interrupts cleanup

#### Child-Side Issues

5. **No self-release mechanism**:
   - Class has no Release/Cleanup method
   - Object never calls Release on itself
   - Relies entirely on parent to release it

6. **Lifecycle method not called**:
   - Class has Release method
   - But it's never invoked in object's lifecycle

#### Structural Issues

7. **Ownership confusion**: 
   - Unclear who is responsible for calling Release
   - Shared ownership without clear responsibility

8. **Callback retention**: 
   - Object held by callback/event listener
   - Callback not unregistered before cleanup

9. **Circular reference**: 
   - Mutual references prevent proper cleanup
   - Neither object releases the other

10. **Error path leak**: 
    - Exception or error skips Release
    - No error handling ensures cleanup

**Analysis Priority**:
- For `Parent[true].field.Child[false]`: Check parent cleanup first (most likely cause)
- For `Parent[false].field.Child[false]`: Both need fixing, start with parent
- For complex chains: Work from leaked object upward to first released ancestor

### Step 6: Generate Analysis Report

Provide a structured report including:

1. **Reference Chain Summary**: Visual representation of the leak path
2. **Leak Point Identification**: Which object(s) failed to call Release
3. **Code Locations**: Specific files and line numbers for:
   - Class definition
   - Field assignment
   - Parent cleanup method
   - Missing Release call location
4. **Root Cause**: Detailed explanation of why Release was not called
5. **Fix Recommendation**: Specific code changes with before/after examples
6. **Risk Assessment**: Potential side effects of the fix

## Example Analysis

**Note**: The examples below use specific class names for illustration. In actual usage, apply the same analysis patterns to whatever class names and field names appear in the user's reference chain. Focus on the **structure and logic** of the analysis, not the specific names.

### Example 1: Parent Released But Forgot Child

#### Input Reference Chain
```
ParentClass:ADDR1[true]._childField.ChildClass:ADDR2[false]
```

**Understanding**: `ParentClass` called Release on itself, but `ChildClass` did NOT call Release.

#### Expected Analysis Output

```markdown
## Memory Leak Analysis Report

### Reference Chain Summary
ParentClass [Released ✓]
  └─ _childField → ChildClass [NOT RELEASED ⚠️]

### Leak Point
- **Object**: ChildClass at 0xADDR2
- **Field**: _childField in ParentClass
- **Status**: Parent called Release on itself, but did NOT release this child field

### Analysis Focus
Since parent (`ParentClass`) called Release, we need to check if it properly released its `_childField` field.

### Code Locations

**Parent Cleanup**: `ParentClass.lua:XX-YY`
```lua
function ParentClass:Cleanup()
    if self._otherField then
        self._otherField:Release()
    end
    -- Missing: self._childField:Release()
end
```

**Field Assignment**: `ParentClass.lua:ZZ`
```lua
self._childField = ChildClass.new(...)
```

### Root Cause
The `ParentClass:Cleanup()` method releases `_otherField` but **forgot to release `_childField`**. This is a common oversight where not all child fields are included in cleanup.

### Fix Recommendation

**File**: `ParentClass.lua`
**Location**: Cleanup method

**Before**:
```lua
function ParentClass:Cleanup()
    if self._otherField then
        self._otherField:Release()
    end
end
```

**After**:
```lua
function ParentClass:Cleanup()
    if self._otherField then
        self._otherField:Release()
    end
    if self._childField then
        self._childField:Release()
        self._childField = nil
    end
end
```

### Risk Assessment
- **Low risk**: Standard cleanup pattern addition
- **Verify**: Ensure Cleanup is called in all destruction paths
```

### Example 2: Parent and Child Released, But Child Forgot Grandchild

#### Input Reference Chain
```
GrandParent:ADDR1[true]._field1.Parent:ADDR2[true]._field2.Child:ADDR3[false]
```

**Understanding**:
- `GrandParent` called Release ✓
- `Parent` also called Release ✓
- But `Child` did NOT call Release ✗

#### Expected Analysis Output

```markdown
## Memory Leak Analysis Report

### Reference Chain Summary
GrandParent [Released ✓]
  └─ _field1 → Parent [Released ✓]
      └─ _field2 → Child [NOT RELEASED ⚠️]

### Leak Point
- **Object**: Child at 0xADDR3
- **Field**: _field2 in Parent
- **Status**: `Parent` called Release on itself but did NOT release this child

### Analysis Focus
`Parent` called `Release()` to release itself, but we need to check if its Release/Cleanup method properly releases the `_field2` field.

### Code Locations

**Parent Cleanup**: `Parent.lua:XX-YY`
```lua
function Parent:Cleanup()
    if self._mainField then
        self._mainField:Release()
    end
    -- Missing: self._field2:Release()
end
```

**Field Assignment**: `Parent.lua:ZZ`
```lua
self._field2 = Child.new(...)
```

### Root Cause
The `Parent:Cleanup()` method releases `_mainField` but **forgot to release `_field2`**. The child field was likely added later and not included in the existing cleanup logic.

### Fix Recommendation

**File**: `Parent.lua`
**Location**: Cleanup method

**Before**:
```lua
function Parent:Cleanup()
    if self._mainField then
        self._mainField:Release()
    end
end
```

**After**:
```lua
function Parent:Cleanup()
    if self._mainField then
        self._mainField:Release()
    end
    if self._field2 then
        self._field2:Release()
        self._field2 = nil
    end
end
```

### Additional Context

Also examine `Child.lua` to understand:
- Does it have special lifecycle requirements?
- Should it call Release on itself?
- Are there any lifecycle hooks we're missing?

### Risk Assessment  
- **Low risk**: Standard cleanup pattern
- **Cascading effect**: This fix will allow `Child` to be properly released
```

**Remember**: Replace `ParentClass`, `ChildClass`, `_childField`, etc. with the actual names from the user's reference chain.

## Multi-Chain Analysis

When multiple reference chains are provided:

1. **Group by common ancestors**: Identify if multiple leaks stem from same root cause
2. **Prioritize by impact**: Focus on leaks higher in the hierarchy first
3. **Identify patterns**: Look for systematic issues (e.g., entire component hierarchy lacks cleanup)
4. **Consolidate fixes**: Provide unified fix strategy when appropriate

## Best Practices

1. **Be thorough**: Read relevant source files completely, don't assume
2. **Consider context**: Look at surrounding code and comments for intent
3. **Verify assumptions**: Check if Release pattern is actually the expected cleanup mechanism
4. **Provide examples**: Include concrete code snippets in recommendations
5. **Think systematically**: Consider if this is an isolated issue or pattern problem
6. **Recommend workspace usage**: If user is not in Lua project, suggest opening the project for better analysis
7. **Work with actual names**: Use the exact class names, field names, and structures from the user's reference chain—don't assume or generalize naming conventions
8. **Focus on patterns**: While class names vary, the analysis logic (checking parent cleanup for child field release) remains consistent

## Resources

### references/release_patterns.md
Common Release patterns and anti-patterns found in Lua-C++ interop scenarios. Reference when unsure about standard cleanup approaches.

### scripts/parse_chain.py
Python utility to parse reference chain strings into structured data for analysis.

## Source Code Access Methods

There are three ways to provide Lua source code access to this skill:

### Method 1: Open Lua Project in CodeBuddy (Recommended ⭐)

**Best approach**: Open the Lua source code project directly in CodeBuddy before using this skill.

**Steps**:
1. Open CodeBuddy in the Lua project directory (e.g., `D:\...\DFMSource\LuaSource\DFM`)
2. Load the lua-cpp-memory-leak skill
3. Provide only the reference chain - no path needed

**Advantages**:
- Skill automatically uses workspace root as search path
- Direct file access and code modification
- Seamless integration with other CodeBuddy features
- No need to specify paths repeatedly

### Method 2: Specify Path Explicitly

If not in the Lua workspace, user can provide the path in their request:

```
Please analyze this reference chain, Lua source code is at:
E:\MyProject\LuaSource

Reference chain: ...
```

The skill will use the specified path for all file searches.

### Method 3: Use Default Path

If no workspace and no explicit path provided, the skill falls back to:
```
D:\congtoulin_Ma1_code_Microcosm\DFMSource\LuaSource\DFM
```

**Note**: This is least flexible and only works if the default path matches the actual location.

## Important Notes

- **Lua VM leaks are out of scope**: This skill focuses only on why Lua code doesn't call Release, not on Lua GC issues
- **Manual Release assumption**: The codebase requires manual Release calls; automatic GC-based cleanup is not expected
- **C++ side is irrelevant**: Analysis focuses solely on Lua code behavior
- **Path flexibility**: Skill adapts to workspace, user-specified, or default paths automatically
