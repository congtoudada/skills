---
name: lua-cpp-memory-leak
description: Analyze Lua-C++ memory leaks by examining reference chains where Lua objects fail to call Release functions, preventing C++ instances from being properly deallocated. Use this skill when users provide reference chains showing unreleased Lua objects that hold C++ instance references, requiring analysis of Lua code to identify why Release was not called and provide fixing recommendations.
---

# Lua-C++ Memory Leak Analysis

## Overview

This skill analyzes memory leaks in Lua-C++ interop scenarios where Lua objects fail to call Release functions on C++ instances. The analysis traces reference chains to identify which Lua objects are preventing C++ memory deallocation and provides root cause analysis with actionable fix recommendations.

## When to Use This Skill

Use this skill when:
- User provides reference chains showing Lua objects holding C++ instance references
- Reference chains indicate which objects called Release (marked `[true]`) and which did not (marked `[false]`)
- Analysis requires examining Lua source code to understand why Release was not invoked
- Need to provide specific code locations and fix recommendations for memory leak issues

## Reference Chain Format

Reference chains follow this pattern:
```
ClassName:MemoryAddress[ReleaseStatus].field.ClassName:MemoryAddress[ReleaseStatus]...
```

### Example
```
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]._crossoverLabel.IVComponentBase:000000029EAF72C0[false]
```

This indicates:
- **Root object**: `IVShopItemTemplate` at address `000000029E8DD9C0` - **Released** (`[true]`)
- **Child object**: `IVTextQualityComponent` at address `000000029E8D6300` via field `_nameComp` - **Not Released** (`[false]`)
- **Leaf object**: `IVComponentBase` at address `000000029EAF72C0` via field `_crossoverLabel` - **Not Released** (`[false]`)

The C++ instance is held by `IVComponentBase:000000029EAF72C0`, which has not called Release. Since its parent called Release, the analysis must determine why this child object did not.

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

### Step 1: Parse Reference Chain

For each provided reference chain:

1. **Extract components**: Split by `.` to get each node in the chain
2. **Parse each node**: Extract class name, memory address, release status, and connecting field
3. **Identify leak points**: Find all nodes marked `[false]` that have unreleased C++ references
4. **Determine analysis targets**: Focus on the first unreleased node with a released parent

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

2. **Search for class references** if direct file not found:
   ```
   search_content pattern="<ClassName>" in determined source directory
   ```

3. **Examine parent-child relationships**: Look for where the connecting field is assigned
   - Example: For `_nameComp` field, search for `_nameComp\s*=` assignments

### Step 4: Analyze Release Failure

For each unreleased object, investigate:

1. **Check destructor/cleanup methods**:
   - Does the class have a cleanup function or `__gc` metamethod?
   - Is Release called in these methods?

2. **Examine parent cleanup**:
   - When the parent calls Release, does it trigger Release on child fields?
   - Look for patterns like:
     ```lua
     function MyClass:Cleanup()
         if self._childField then
             self._childField:Release()
         end
     end
     ```

3. **Identify ownership patterns**:
   - Is the child object owned by the parent?
   - Are there weak references or shared ownership scenarios?
   - Look for comments or flags indicating ownership responsibility

4. **Check lifecycle mismatches**:
   - Does the child outlive the parent intentionally?
   - Are there event listeners or callbacks that keep the child alive?
   - Are there early-return paths in cleanup that skip Release?

### Step 5: Root Cause Analysis

Categorize the leak cause:

1. **Missing Release in cleanup**: Parent cleanup exists but doesn't Release this child
2. **No cleanup method**: Class has no destructor/cleanup implementation
3. **Conditional Release bug**: Release is conditional and condition not met
4. **Ownership confusion**: Unclear who is responsible for calling Release
5. **Callback retention**: Object held by callback/event listener without cleanup
6. **Error path leak**: Exception or early return skips Release
7. **Circular reference**: Mutual references prevent proper cleanup

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

### Input Reference Chain
```
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]._crossoverLabel.IVComponentBase:000000029EAF72C0[false]
```

### Expected Analysis Output

```markdown
## Memory Leak Analysis Report

### Reference Chain Summary
IVShopItemTemplate [Released]
  └─ _nameComp → IVTextQualityComponent [NOT RELEASED] ⚠️
      └─ _crossoverLabel → IVComponentBase [NOT RELEASED] ⚠️

### Leak Point
- **Object**: IVTextQualityComponent at 0x000000029E8D6300
- **Field**: _nameComp in IVShopItemTemplate
- **Status**: Not released despite parent calling Release

### Code Locations

**Class Definition**: `IVTextQualityComponent.lua:1`
**Field Assignment**: `IVShopItemTemplate.lua:45`
```lua
self._nameComp = IVTextQualityComponent.new(...)
```

**Parent Cleanup**: `IVShopItemTemplate.lua:78-85`
```lua
function IVShopItemTemplate:Cleanup()
    if self._icon then
        self._icon:Release()
    end
    -- Missing: self._nameComp cleanup
end
```

### Root Cause
The `IVShopItemTemplate:Cleanup()` method releases `_icon` but does not release `_nameComp`. This appears to be an oversight where not all child components are being cleaned up.

### Fix Recommendation

**File**: `IVShopItemTemplate.lua`
**Location**: Line 78-85

**Before**:
```lua
function IVShopItemTemplate:Cleanup()
    if self._icon then
        self._icon:Release()
    end
end
```

**After**:
```lua
function IVShopItemTemplate:Cleanup()
    if self._icon then
        self._icon:Release()
    end
    if self._nameComp then
        self._nameComp:Release()
        self._nameComp = nil
    end
end
```

### Cascading Fix Required
Since `_nameComp` itself has an unreleased child `_crossoverLabel`, ensure `IVTextQualityComponent` also has proper cleanup:

**File**: `IVTextQualityComponent.lua`

Add or update cleanup method:
```lua
function IVTextQualityComponent:Cleanup()
    if self._crossoverLabel then
        self._crossoverLabel:Release()
        self._crossoverLabel = nil
    end
end
```

### Risk Assessment
- **Low risk**: Standard cleanup pattern addition
- **Verify**: Ensure cleanup is called in all destruction paths
- **Test**: Verify parent-child lifecycle matches expected behavior
```

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
