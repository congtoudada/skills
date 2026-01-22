# YxFramework 对象管理与 Release 模式总结

本文档总结了 YxFramework 中对象管理、Release 调用的典型模式和易错场景，供分析业务代码内存泄露时参考。

---

## 一、Release 调用时机

### 1.1 UI 生命周期中的 Release

**调用链**：
```
UIManager:CloseUI(uiIns)
  → UIReleaseUtil.MuteRelease(self)
     → UIReleaseUtil._ProcessReleaseUnbindLuaRefs(self)
        → self:Release()
```

**关键方法**：
- `OnOpen()` - UI 显示时创建资源
- `OnClose()` - UI 关闭时业务清理
- `Destroy()` - UI 销毁时释放所有子对象

**标准模式**：
```lua
function MyUI:OnOpen()
    -- 创建子UI（推荐使用 BindOwner 方式）
    self._childUI = Facade.UIManager:CreateSubUIBindOwner(self, UIName2ID.ChildUI)
    
    -- 创建定时器
    self._timer = Timer:NewIns(1.0, 0)
    self._timer:Start()
end

function MyUI:Destroy()
    -- 释放定时器（无限循环定时器必须手动释放）
    if self._timer then
        self._timer:Release()
        self._timer = nil
    end
    
    -- 子UI如果用 CreateSubUIBindOwner，框架自动释放
    -- 如果是 CreateSubUI，需要手动释放
end
```

---

### 1.2 定时器的 Release

**自动释放**（有限次数定时器）：
```lua
-- 执行 targetCount 次后自动释放
local timer = Timer:NewIns(1.0, 1)  -- 1秒后执行1次
timer:Start()
-- 不需要手动 Release
```

**手动释放**（无限循环定时器）：
```lua
-- targetCount=0 表示无限循环
local loopTimer = Timer:NewIns(1.0, 0)
loopTimer:Start()

-- 必须在 Destroy 中手动释放
function MyUI:Destroy()
    if loopTimer then
        loopTimer:Release()
        loopTimer = nil
    end
end
```

---

### 1.3 Manager 批量管理模式

```lua
function MyManager:Ctor()
    self._timerList = {}
end

function MyManager:CreateTimer()
    local timer = Timer:NewIns(1.0, 1)
    table.insert(self._timerList, timer)
    return timer
end

function MyManager:Destroy()
    -- 批量释放所有托管对象
    for _, timer in ipairs(self._timerList) do
        if not hasdestroy(timer) then
            timer:Release()
        end
    end
    table.clear(self._timerList)
end
```

---

### 1.4 事件监听器清理

**本地事件**（LuaObject 自动清理）：
```lua
function MyUI:Ctor()
    self._myEvent = LuaEvent:NewIns("MyEvent")
    self._myEvent:AddListener(callback, self)
end
-- LuaObject 基类会自动清理本地事件，通常不需要手动处理
```

**全局事件**（必须手动移除）：
```lua
function MyUI:OnOpen()
    self._eventHandle = GlobalEvent.OnSomething:AddListener(self.OnEvent, self)
end

function MyUI:Destroy()
    if self._eventHandle then
        GlobalEvent.OnSomething:RemoveListener(self._eventHandle)
        self._eventHandle = nil
    end
end
```

---

## 二、容易遗漏 Release 的场景

### 2.1 子UI未在父UI的Destroy中释放

**问题代码**：
```lua
function ParentUI:Ctor()
    self._childUI = Facade.UIManager:CreateSubUI(UIName2ID.ChildUI)
end

function ParentUI:Destroy()
    -- 忘记释放子UI！
end
```

**引用链表现**：
```
ParentUI:0xADDR1[true]._childUI.ChildUI:0xADDR2[false]
```

**修复方法**：
```lua
function ParentUI:Destroy()
    if self._childUI then
        self._childUI:Release()
        self._childUI = nil
    end
end
```

---

### 2.2 递归嵌套的子对象未完全释放

**问题模式**：
```
GrandParent[true]._field1.Parent[true]._field2.Child[false]
```

**关键理解**：⚠️ **对象调用 `Release()` 只释放自己，不会自动释放子对象！**

虽然 `Parent[true]` 表示 Parent 自己调用了 Release，但如果它的 `Destroy` 方法忘记释放 `_field2` 字段，`Child` 就会泄露。

**分析要点**：
1. 找到 `Parent.lua` 文件
2. 检查其 `Destroy` 方法是否有 `self._field2:Release()` 调用
3. 如果没有，这就是泄露原因

---

### 2.3 定时器未及时释放

**问题代码**：
```lua
function MyUI:Ctor()
    self._timer = Timer:NewIns(1.0, 0) -- 无限循环
    self._timer:Start()
end

function MyUI:Destroy()
    -- 忘记停止并释放 timer！
end
```

**修复方法**：
```lua
function MyUI:Destroy()
    if self._timer then
        self._timer:Release()  -- 内部会先停止再销毁
        self._timer = nil
    end
end
```

---

### 2.4 全局事件监听未移除

**问题场景**：
```lua
function MyUI:Ctor()
    GlobalEvent.OnSomething:AddListener(self.OnEvent, self)
end

function MyUI:Destroy()
    -- 忘记移除监听！导致 GlobalEvent 持有 self 的引用
end
```

**引用链表现**：
```
GlobalEvent:0xADDR1[false]._listeners.MyUI:0xADDR2[false]
```

**修复方法**：
```lua
function MyUI:OnOpen()
    self._eventHandle = GlobalEvent.OnSomething:AddListener(self.OnEvent, self)
end

function MyUI:Destroy()
    if self._eventHandle then
        GlobalEvent.OnSomething:RemoveListener(self._eventHandle)
        self._eventHandle = nil
    end
end
```

---

### 2.5 协程未正确取消

**问题代码**：
```lua
function MyUI:Ctor()
    self._coTaskMgr = CoTaskManager:NewIns()
    self._coTaskMgr:StartCoroutine(self.LongRunningTask, self)
end

function MyUI:Destroy()
    -- 忘记停止协程管理器！
end
```

**修复方法**：
```lua
function MyUI:Destroy()
    if self._coTaskMgr then
        self._coTaskMgr:Release()  -- 会调用 StopAllCoroutines
        self._coTaskMgr = nil
    end
end
```

---

## 三、常见反模式（导致泄露）

### 3.1 部分子对象遗漏

```lua
-- ❌ 错误
function MyUI:Destroy()
    if self._mainChild then
        self._mainChild:Release()
    end
    -- 忘记释放 self._sideChild !!!
end
```

**检测方法**：
1. 搜索类中所有 `self._xxx = CreateXXX()` 赋值
2. 检查 Destroy 方法是否都有对应的 Release 调用

---

### 3.2 条件释放bug

```lua
-- ❌ 错误
function MyUI:Destroy()
    if self._isActive then  -- ⚠️ 如果不 active，childUI 就泄露了
        if self._childUI then
            self._childUI:Release()
        end
    end
end
```

**正确做法**：Release 应该是无条件的
```lua
function MyUI:Destroy()
    -- 业务逻辑可以有条件
    if self._isActive then
        self:DoSomething()
    end
    
    -- 资源释放必须无条件
    if self._childUI then
        self._childUI:Release()
        self._childUI = nil
    end
end
```

---

### 3.3 提前return导致清理中断

```lua
-- ❌ 错误
function MyUI:Destroy()
    if not self._initialized then
        return  -- ⚠️ 提前返回，后面的 Release 不执行
    end
    
    if self._childUI then
        self._childUI:Release()
    end
    if self._timer then
        self._timer:Release()
    end
end
```

**正确做法**：
```lua
function MyUI:Destroy()
    -- 将释放逻辑放在条件之外
    if self._childUI then
        self._childUI:Release()
        self._childUI = nil
    end
    if self._timer then
        self._timer:Release()
        self._timer = nil
    end
    
    -- 条件逻辑可以放后面
    if not self._initialized then
        return
    end
    -- 其他清理...
end
```

---

### 3.4 字段名变更未同步到Destroy

```lua
function MyUI:Ctor()
    -- 代码演进中字段名改了
    self._newChildUI = CreateSubUI(...)
end

function MyUI:Destroy()
    -- 还在释放旧字段名 ❌
    if self._oldChildUI then
        self._oldChildUI:Release()
    end
    -- 新字段泄露！
end
```

**预防方法**：
1. 重命名字段时搜索所有引用
2. 添加注释标注字段的生命周期责任

---

### 3.5 循环引用未break

```lua
-- ❌ Parent 和 Child 互相引用
function Parent:Ctor()
    self._child = Child:NewIns(self)
end

function Child:Ctor(parent)
    self._parent = parent  -- 循环引用
end
```

**正确做法**：使用弱引用
```lua
function Child:Ctor(parent)
    self._parent = makeweak(parent)  -- ✅ 弱引用，不影响 parent 的生命周期
end
```

---

## 四、父子对象释放关系

### 4.1 子UI的两种管理模式

**手动管理模式**（需要手动释放）：
```lua
function MyUI:Ctor()
    self._subUI = Facade.UIManager:CreateSubUI(UIName2ID.SubUI)
end

function MyUI:Destroy()
    if self._subUI then
        self._subUI:Release()  -- ⚠️ 必须手动释放
        self._subUI = nil
    end
end
```

**自动管理模式**（推荐，框架自动释放）：
```lua
function MyUI:Ctor()
    self._subUI = Facade.UIManager:CreateSubUIBindOwner(self, UIName2ID.SubUI)
end

function MyUI:Destroy()
    -- ✅ 框架自动释放，不需要手动 Release
    -- Facade.UIManager:ClearAllSubUI(self, false) 会自动调用
end
```

---

### 4.2 对象池中的父子关系

**关键点**：
- 对象进池时调用 `Deactivate`，不调用 `Destroy`
- `Deactivate` 应该清理状态，但不释放子对象（因为对象还会复用）
- 只有真正销毁时才调用 `Destroy` 释放子对象

**正确模式**：
```lua
function PooledObject:OnActivate()
    -- 从池中取出，重新初始化
    self._childUI = CreateSubUI(...)
end

function PooledObject:OnDeactivate()
    -- 放回池中，重置状态但不释放子对象
    self._data = nil
    -- 不调用 self._childUI:Release() !!!
end

function PooledObject:Destroy()
    -- 真正销毁时才释放子对象
    if self._childUI then
        self._childUI:Release()
        self._childUI = nil
    end
end
```

---

## 五、Release 调用 Checklist

创建对象时，确保在 Destroy 中正确处理：

- [ ] **定时器（无限循环）**：`timer:Release()`
- [ ] **子UI（手动创建）**：`childUI:Release()`
- [ ] **子UI（BindOwner）**：框架自动处理
- [ ] **本地事件**：LuaObject 自动清理
- [ ] **全局事件监听**：必须手动 `RemoveListener`
- [ ] **协程管理器**：`coTaskMgr:Release()`
- [ ] **Manager托管对象**：批量释放
- [ ] **对象池对象**：在 Destroy 中释放，在 Deactivate 中重置状态

---

## 六、代码审查要点

审查 Destroy 方法时检查：

1. **所有 `self._xxx = CreateXXX()` 赋值是否都有对应的 Release**
2. **是否有条件释放导致某些路径不调用 Release**
3. **是否有提前 return 跳过了 Release 逻辑**
4. **字段重命名后 Destroy 是否同步更新**
5. **是否存在循环引用需要使用弱引用**

---

## 七、易错场景速查表

| 场景 | 引用链表现 | 检查要点 | 典型修复 |
|------|-----------|---------|---------|
| 子UI未释放 | `Parent[true]._child.Child[false]` | Parent:Destroy 是否有 `self._child:Release()` | 添加 Release 调用 |
| 递归嵌套泄露 | `A[true]._f1.B[true]._f2.C[false]` | B:Destroy 是否释放 `_f2` | 在 B:Destroy 中添加 `self._f2:Release()` |
| 定时器未停止 | `UI[true]._timer.Timer[false]` | Destroy 是否释放 timer | 添加 `self._timer:Release()` |
| 全局事件残留 | `GlobalEvent._listeners.UI[false]` | 是否调用 RemoveListener | 在 Destroy 中移除监听 |
| 协程未取消 | `UI[true]._coTaskMgr.CoTaskManager[false]` | 是否释放协程管理器 | 添加 `self._coTaskMgr:Release()` |

---

## 八、推荐模板

```lua
---@class StandardUI : LuaUIBaseView
StandardUI = ui("StandardUI")

function StandardUI:Ctor()
    -- 初始化字段为 nil，方便检查
    self._childUI = nil
    self._timer = nil
    self._eventHandle = nil
end

function StandardUI:OnOpen()
    -- 创建资源，使用 BindOwner 方式（推荐）
    self._childUI = Facade.UIManager:CreateSubUIBindOwner(self, UIName2ID.ChildUI)
    
    -- 创建定时器
    self._timer = Timer:NewIns(1.0, 0)
    self._timer:AddListener(self.OnTick, self)
    self._timer:Start()
    
    -- 添加全局事件监听
    self._eventHandle = GlobalEvent.OnSomething:AddListener(self.OnEvent, self)
end

function StandardUI:OnClose()
    -- 业务清理逻辑
end

function StandardUI:Destroy()
    -- 1. 释放定时器（无限循环定时器必须手动释放）
    if self._timer then
        self._timer:Release()
        self._timer = nil
    end
    
    -- 2. 移除全局事件监听（必须手动移除）
    if self._eventHandle then
        GlobalEvent.OnSomething:RemoveListener(self._eventHandle)
        self._eventHandle = nil
    end
    
    -- 3. 子UI如果用 CreateSubUIBindOwner，框架自动释放
    --    如果是 CreateSubUI，需要手动释放：
    -- if self._childUI then
    --     self._childUI:Release()
    --     self._childUI = nil
    -- end
    
    -- 4. 本地事件 LuaObject 会自动清理，通常不需要手动处理
end
```

---

**总结时间**：2026-01-21  
**基于版本**：YxFramework Latest
