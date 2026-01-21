# Common Release Patterns in Lua-C++ Interop

This document catalogs common patterns and anti-patterns for calling Release on C++ instances from Lua code.

## Standard Release Patterns

### 1. Destructor-Style Cleanup

Most common pattern - explicit cleanup method called before object destruction:

```lua
function MyClass:Cleanup()
    if self._child then
        self._child:Release()
        self._child = nil
    end
    if self._another then
        self._another:Release()
        self._another = nil
    end
end
```

**Key characteristics:**
- Explicit method name (Cleanup, Destroy, Dispose, etc.)
- Checks for nil before calling Release
- Sets field to nil after releasing
- Called manually before object is garbage collected

### 2. Cascading Release

Parent automatically releases all children:

```lua
function Parent:Release()
    -- Release all managed children
    for _, child in ipairs(self._children) do
        if child then
            child:Release()
        end
    end
    self._children = {}
    
    -- Call base class Release
    BaseClass.Release(self)
end
```

### 3. Conditional Ownership

Only Release if this object owns the reference:

```lua
function MyClass:Cleanup()
    if self._ownedChild and self._ownsReference then
        self._ownedChild:Release()
    end
    self._ownedChild = nil
end
```

**Key characteristics:**
- Ownership flag (`_ownsReference`, `_isOwner`, etc.)
- Only owner calls Release
- Shared references handled carefully

### 4. Event Listener Cleanup

Release after unregistering from events:

```lua
function MyClass:Cleanup()
    if self._eventSource then
        self._eventSource:RemoveListener(self._handler)
    end
    
    if self._boundObject then
        self._boundObject:Release()
        self._boundObject = nil
    end
end
```

### 5. Weak Reference Pattern

Using weak tables to avoid needing explicit Release:

```lua
-- Not requiring Release (out of scope for this skill)
setmetatable(self._weakChildren, {__mode = "v"})
```

## Common Anti-Patterns (Leak Sources)

### 1. Incomplete Cleanup

```lua
-- BAD: Only releases some children
function MyClass:Cleanup()
    if self._child1 then
        self._child1:Release()
    end
    -- Missing: self._child2, self._child3
end
```

**Fix**: Release all children systematically

### 2. Missing Cleanup Method

```lua
-- BAD: No cleanup method at all
function MyClass:new()
    local obj = {}
    obj._child = SomeObject.new()  -- Never released!
    return obj
end
```

**Fix**: Add Cleanup method and ensure it's called

### 3. Early Return Leak

```lua
-- BAD: Early return skips Release
function MyClass:Cleanup()
    if not self._isValid then
        return  -- Leak!
    end
    
    if self._child then
        self._child:Release()
    end
end
```

**Fix**: Release before early return or use try-finally pattern

### 4. Exception Path Leak

```lua
-- BAD: Error prevents Release
function MyClass:ProcessAndCleanup()
    self:DoSomething()  -- May throw error
    
    -- Never reached if error above
    if self._child then
        self._child:Release()
    end
end
```

**Fix**: Use pcall or ensure cleanup in error handler

### 5. Callback Retention

```lua
-- BAD: Callback holds reference without cleanup path
function MyClass:SetupAsync()
    local callback = function()
        self._child:DoSomething()  -- Child never released
    end
    AsyncService:RegisterCallback(callback)
end
```

**Fix**: Store callback reference and unregister in cleanup

### 6. Conditional Creation, Unconditional Use

```lua
-- BAD: Creation is conditional but usage assumes it exists
function MyClass:new()
    local obj = {}
    if someCondition then
        obj._child = Child.new()
    end
    return obj
end

function MyClass:Cleanup()
    self._child:Release()  -- May be nil!
end
```

**Fix**: Always check for nil before Release

## Debugging Checklist

When analyzing a leak, verify:

- [ ] Does the class have a cleanup/destructor method?
- [ ] Is Release called on all child object fields?
- [ ] Are there conditional ownership scenarios?
- [ ] Are event listeners properly unregistered?
- [ ] Are there early return paths that skip cleanup?
- [ ] Does error handling ensure cleanup still occurs?
- [ ] Is the cleanup method actually being called?
- [ ] Are there array/table fields that need iteration?
- [ ] Are weak references being used appropriately?
- [ ] Is there documentation indicating ownership?

## Release Call Signatures

Common ways Release is called:

```lua
-- Direct call
object:Release()

-- With nil check
if object then
    object:Release()
end

-- With nil assignment
if object then
    object:Release()
    object = nil  -- Prevent double release
end

-- Array cleanup
for _, obj in ipairs(self._objects) do
    obj:Release()
end
self._objects = {}

-- Table cleanup
for key, obj in pairs(self._objectMap) do
    obj:Release()
    self._objectMap[key] = nil
end
```

## Ownership Keywords

Look for these comments/variables that indicate ownership:

- `_ownsReference`
- `_isOwner`
- `_managed`
- `_borrowed` (usually means DON'T release)
- Comments: "takes ownership", "borrowed reference", "weak reference"
