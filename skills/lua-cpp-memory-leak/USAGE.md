# Lua-C++ Memory Leak Analysis Skill - 使用说明

## 快速开始

这个 skill 用于分析 Lua-C++ 交互中的内存泄露问题，特别是当 Lua 对象未能正确调用 `Release` 函数导致 C++ 实例无法释放的场景。

## 🎯 最佳使用方式（强烈推荐）

**直接在 Lua 源代码工程中使用 CodeBuddy：**

1. **用 CodeBuddy 打开 Lua 项目**
   ```
   打开目录：D:\congtoulin_Ma1_code_Microcosm\DFMSource\LuaSource\DFM
   ```

2. **加载 lua-cpp-memory-leak skill**

3. **直接提供引用链，无需指定路径**
   ```
   分析这条内存泄露：
   IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]
   ```

4. **Skill 自动完成**：
   - 在当前工作区搜索相关 Lua 文件
   - 定位代码位置
   - 分析泄露原因
   - 提供修复建议
   - 可直接修改代码

**为什么这是最佳方式？**
- ✅ 无需手动指定路径
- ✅ 可以直接搜索和读取所有项目文件
- ✅ 分析结果可以立即应用到代码修改
- ✅ 完整的上下文理解
- ✅ 最流畅的使用体验

## 框架参考

如果你的项目基于 **YxFramework**，Skill 内置了框架最佳实践参考（`references/framework_patterns.md`），包含：

- ✅ **标准对象生命周期模式**（UI、Timer、Manager 等）
- ✅ **常见 Release 调用位置和时机**
- ✅ **容易遗漏 Release 的 5 大场景**
- ✅ **父子对象释放关系处理**
- ✅ **代码审查 Checklist**
- ✅ **5 种常见反模式及修复方法**

分析时会自动结合框架知识，提供更精准的修复建议。

## 使用场景

当你遇到以下情况时使用这个 skill：

1. 你有一条或多条引用链，显示了 Lua 对象之间的引用关系
2. 引用链中标记了哪些对象已调用 `Release` (`[true]`)，哪些未调用 (`[false]`)
3. 你需要分析为什么某些对象没有调用 `Release`
4. 你需要定位到具体的代码位置并获得修复建议

## 输入格式

### 引用链格式

```
ClassName:MemoryAddress[ReleaseStatus].fieldName.ClassName:MemoryAddress[ReleaseStatus]...__cppinst = BlueprintClassName
```

**关键点**：
- 只有 Lua 对象有 `[true]` 或 `[false]` 标记
- 字段名（如 `_nameComp`）没有标记，只是连接符
- `__cppinst = BlueprintClassName` 是可选的，表示泄露的 C++ 蓝图类

### 示例 1：基本格式

```
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]._crossoverLabel.IVComponentBase:000000029EAF72C0[false]
```

这表示：
- `IVShopItemTemplate` (已释放) 通过 `_nameComp` 字段引用了
- `IVTextQualityComponent` (未释放) 通过 `_crossoverLabel` 字段引用了
- `IVComponentBase` (未释放)

### 示例 2：包含 C++ 实例信息

```
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[true]._crossoverLabel.IVComponentBase:000000029EAF72C0[false].__cppinst = WBP_SlotCompIconCrossoverLabel_C
```

这表示：
- `IVShopItemTemplate` (已释放) → `_nameComp` → `IVTextQualityComponent` (已释放)
- `IVTextQualityComponent` → `_crossoverLabel` → `IVComponentBase` (未释放)
- `IVComponentBase` 持有的 C++ 蓝图实例是 `WBP_SlotCompIconCrossoverLabel_C`
- 这个 UE widget 无法被释放，因为 `IVComponentBase` 没有调用 `Release()`

## 如何使用

### 方式一：在 Lua 工程中使用（推荐 ⭐）

只需提供引用链即可，Skill 自动使用当前工作区：

```
请分析这条内存泄露：
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[true]._crossoverLabel.IVComponentBase:000000029EAF72C0[false].__cppinst = WBP_SlotCompIconCrossoverLabel_C
```

### 方式二：指定源代码路径

如果不在 Lua 工程中，明确指定路径：

```
请分析这条引用链，Lua 源代码在：
E:\MyProject\LuaSource

引用链：
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]
```

### 方式三：使用默认路径

不指定路径时，Skill 使用默认路径：
```
D:\congtoulin_Ma1_code_Microcosm\DFMSource\LuaSource\DFM
```

**路径优先级**：
1. 当前工作区（如果在 Lua 项目中）
2. 用户指定路径
3. 默认路径

### 多条引用链分析

```
请分析这些内存泄露的引用链：

1. IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false].__cppinst = WBP_TextComp_C
2. IVShopItemTemplate:000000029E8DD9C0[true]._icon.IVIcon:000000029E8D6400[false].__cppinst = WBP_IconWidget_C
3. ...
```

## 输出内容

Skill 会提供以下内容：

1. **引用链可视化**：树状图展示引用关系
2. **泄露点定位**：标识哪些对象未释放
3. **C++ 实例信息**：显示泄露的 UE 蓝图类名（如果提供了 `__cppinst`）
4. **代码位置**：
   - 类定义文件和行号
   - 字段赋值位置
   - 父对象的清理方法
   - 缺失 Release 调用的位置
5. **根因分析**：解释为什么没有调用 Release
6. **修复建议**：提供具体的代码修改方案（Before/After）
7. **影响评估**：说明泄露的实际影响（包括 C++ 蓝图资源）

## 工具脚本

### parse_chain.py

用于解析引用链字符串的 Python 工具（已支持 `__cppinst` 格式）：

```bash
python scripts/parse_chain.py "IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false].__cppinst = WBP_TextComp_C"
```

输出 JSON 格式的结构化数据，包含：
- 解析后的节点信息
- C++ 蓝图类名
- 泄露点分析
- 可视化树状图

## 参考文档

### release_patterns.md

包含常见的 Release 调用模式和反模式（导致泄露的模式），可以帮助理解代码中的标准做法。

## 注意事项

### 引用链格式的关键理解 ⚠️

**重要**：只有 Lua 对象才有 `[true]` 或 `[false]` 标记，字段名没有标记！

```
ClassName:Address[ReleaseStatus].fieldName.ClassName:Address[ReleaseStatus].__cppinst = BlueprintClass
    ↑                                ↑                                              ↑
   有标记                          无标记（仅是连接）                            C++蓝图类（可选）
```

**示例**：
```
A:addr1[true]._field.B:addr2[false].__cppinst = WBP_MyWidget_C
```
- `A` 是 Lua 对象，`[true]` 表示它调用了 Release
- `_field` 是字段名，**没有标记**
- `B` 是 Lua 对象，`[false]` 表示它**没有**调用 Release
- `__cppinst = WBP_MyWidget_C` 表示 B 持有的 C++ 蓝图类

**关键点**：
- `A[true]` 表示 A 调用了自己的 Release()
- 但这**不代表** A 释放了它的 `_field` 子对象
- 需要检查 A 的 Cleanup 方法是否有 `self._field:Release()`
- `WBP_MyWidget_C` 这个 UE widget 会一直占用内存，直到 B 调用 Release

### 其他注意事项

1. **Lua 虚拟机泄露不在范围内**：这个 skill 只关注为什么 Lua 代码没有调用 Release，不处理 Lua GC 本身的问题
2. **手动 Release**：假设项目使用手动 Release 机制，不依赖自动 GC
3. **只看 Lua 侧**：分析只关注 Lua 代码，不涉及 C++ 实现
4. **路径灵活性**：
   - 在 Lua 工程中使用最方便（自动使用工作区）
   - 也可以指定任何路径
   - 有默认路径作为后备

## 🎯 最佳实践

**推荐工作流程**：

1. **用 CodeBuddy 打开 Lua 源代码工程**
   - 文件 -> 打开文件夹 -> 选择 Lua 源代码目录

2. **加载 lua-cpp-memory-leak skill**

3. **直接提供引用链**（无需路径）
   ```
   分析这条内存泄露：
   IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false].__cppinst = WBP_TextComp_C
   ```

4. **Skill 自动完成分析**：
   - 在工作区搜索相关文件
   - 定位代码位置
   - 生成分析报告

5. **应用修复建议**
   - 让 CodeBuddy 直接修改代码
   - 或手动应用建议

## 示例会话

### 示例 1：父对象已释放，但忘记释放子对象

**用户：**
```
请分析这条内存泄露：
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false].__cppinst = WBP_TextQualityComp_C
```

**理解**：
- `IVShopItemTemplate` 调用了 Release
- `IVTextQualityComponent` 没有调用 Release
- 泄露的 C++ 蓝图是 `WBP_TextQualityComp_C`

**AI 助手：**
```
## 内存泄露分析报告

### 引用链可视化
IVShopItemTemplate [已释放 ✓]
  └─ _nameComp → IVTextQualityComponent [未释放 ⚠️]
      └─ __cppinst → WBP_TextQualityComp_C (C++ Blueprint)

### 泄露点
- 对象：IVTextQualityComponent at 0x000000029E8D6300
- 字段：IVShopItemTemplate 的 _nameComp
- 状态：父对象已释放，但未释放此子对象
- C++ 实例：WBP_TextQualityComp_C（UE widget 被泄露）

### 分析重点
由于父对象 `IVShopItemTemplate` 调用了 Release，需要检查它是否正确释放了 `_nameComp` 字段。

[检查代码...]

### 根因
`IVShopItemTemplate:Cleanup()` 释放了 `_icon` 但忘记释放 `_nameComp`。

### 修复建议
在 `IVShopItemTemplate.lua` 的 Cleanup 方法中添加：
```lua
if self._nameComp then
    self._nameComp:Release()
    self._nameComp = nil
end
```

### 影响评估
- Lua 对象 `IVTextQualityComponent` 无法被 GC
- C++ 蓝图 `WBP_TextQualityComp_C` 实例占用内存
- 可能包含 UE Widget 相关的纹理、材质等资源
```

### 示例 2：父对象和子对象都已释放，但子对象忘记释放孙对象

**用户：**
```
分析这条引用链：
IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[true]._crossoverLabel.IVComponentBase:000000029EAF72C0[false].__cppinst = WBP_SlotCompIconCrossoverLabel_C
```

**理解**：
- `IVShopItemTemplate` 调用了 Release ✓
- `IVTextQualityComponent` 也调用了 Release ✓
- 但 `IVComponentBase` 没有调用 Release ✗
- 泄露的 C++ 蓝图是 `WBP_SlotCompIconCrossoverLabel_C`

**AI 助手：**
```
## 内存泄露分析报告

### 引用链可视化
IVShopItemTemplate [已释放 ✓]
  └─ _nameComp → IVTextQualityComponent [已释放 ✓]
      └─ _crossoverLabel → IVComponentBase [未释放 ⚠️]
          └─ __cppinst → WBP_SlotCompIconCrossoverLabel_C (C++ Blueprint)

### 泄露点
- 对象：IVComponentBase at 0x000000029EAF72C0
- 字段：IVTextQualityComponent 的 _crossoverLabel
- 状态：父对象虽然调用了自身的 Release，但未释放此子字段
- C++ 实例：WBP_SlotCompIconCrossoverLabel_C（UE widget 被泄露）

### 关键理解
虽然 `IVTextQualityComponent` 调用了 `Release()` 释放自己，但这**不意味着**它自动释放了子对象。需要检查它的 Cleanup 方法是否有释放 `_crossoverLabel`。

[检查代码...]

### 根因
`IVTextQualityComponent:Cleanup()` 释放了 `_mainLabel` 但忘记释放 `_crossoverLabel`。

### 修复建议
在 `IVTextQualityComponent.lua` 的 Cleanup 方法中添加：
```lua
if self._crossoverLabel then
    self._crossoverLabel:Release()
    self._crossoverLabel = nil
end
```

### 影响评估
- Lua 对象 `IVComponentBase` 无法被 GC
- C++ 蓝图 `WBP_SlotCompIconCrossoverLabel_C` 实例占用内存
- 这是一个 UE Slate widget，可能包含图标、材质等资源
```

## 技巧

1. **批量分析**：一次提供多条引用链可以发现系统性问题
2. **关注模式**：如果多个泄露有相似结构，可能是同一个根本问题
3. **优先级**：先修复引用链上层的泄露，可能会自动解决下层的泄露
4. **验证修复**：修改代码后，使用相同的引用链重新测试

## 常见问题

**Q: 如何获取引用链？**  
A: 通常由内存分析工具或调试器生成。

**Q: 可以分析 C++ 侧的问题吗？**  
A: 不可以，这个 skill 只关注 Lua 侧为什么没调用 Release。

**Q: 如果找不到相关的 Lua 文件怎么办？**  
A: 
- 确保在正确的 Lua 工程中打开 CodeBuddy
- 或者明确指定正确的源代码路径
- 检查类名拼写是否正确

**Q: 修复建议会直接修改代码吗？**  
A: 不会自动修改，只提供建议。你可以选择：
- 让 CodeBuddy 帮你应用修改（需确认）
- 手动复制建议的代码

**Q: 必须在 Lua 工程中使用吗？**  
A: 不是必须，但强烈推荐：
- ✅ 在工程中：体验最佳，无需指定路径
- ⚠️ 不在工程中：需要手动指定路径，可能有访问限制

**Q: 可以同时分析多个项目的引用链吗？**  
A: 如果引用链来自不同项目，建议分别在各自工程中分析。
